from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import re
from collections import defaultdict
import math
import statistics
import csv
import io
import json
from datetime import datetime
import unicodedata
import asyncio
from .db import get_db
from .crud import (
    get_profiles,
    get_nearest_profiles,
    create_profile,
    get_profile_by_id,
    update_profile as crud_update_profile,
    delete_profile as crud_delete_profile,
)
from .models import Profile
from .analytics import AnalyticsEngine
from .rag import retrieve, summarize, index_metadata, get_argo_contextual_suggestions
from pydantic import BaseModel, Field
from datetime import date as DateType

class CreateProfileRequest(BaseModel):
    float_id: Optional[str] = None
    latitude: float
    longitude: float
    depth: float
    temperature: float
    salinity: float
    month: int
    year: int
    date: Optional[DateType] = None

class UpdateProfileRequest(BaseModel):
    float_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    depth: Optional[float] = None
    temperature: Optional[float] = None
    salinity: Optional[float] = None
    month: Optional[int] = None
    year: Optional[int] = None
    date: Optional[DateType] = None

class IndexRequest(BaseModel):
    docs: List[Dict[str, Any]]

import os

router = APIRouter()

@router.get("/retrieve")
def retrieve_endpoint(q: str):
    return {"result": retrieve(q)}

@router.get("/summarize")
def summarize_endpoint(text: str):
    ctx = retrieve(text)
    return {"summary": summarize(text, ctx)}

@router.get("/index")
def index_metadata_endpoint():
    return {"status": index_metadata()}

data_router = APIRouter()
admin_router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    latitude: float | None = None
    longitude: float | None = None

class ChatResponse(BaseModel):
    answer: str
    suggestions: List[str] = []
    data_insights: Dict[str, Any] = {}

class IndexRequest(BaseModel):
    docs: List[Dict]

chat_router = APIRouter()

@chat_router.post("/", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    """JARVIS-like AI chat endpoint with natural language to SQL conversion"""
    from .ai_service import floatchat_ai

    def clean_text(s: str) -> str:
        s = unicodedata.normalize('NFKD', s)
        s = s.replace(""", '"').replace(""", '"').replace("'", "'").replace("–", "-")
        s = ''.join(ch for ch in s if ch.isprintable())
        return s

    message = clean_text((req.message or "").strip())
    if not message:
        return ChatResponse(
            answer="Hello! I'm FloatChat, your AI oceanographic assistant. Ask me anything about ocean data!",
            suggestions=["Show temperature near the equator", "Find salinity in the Pacific Ocean", "Analyze deep ocean profiles"]
        )

    try:
        # Use enhanced AI service with dynamic SQL generation
        ai_result = await floatchat_ai.get_ai_response(message, None, db)

        if not ai_result["success"]:
            return ChatResponse(
                answer=ai_result["answer"],
                suggestions=["Try: 'Show ocean temperature data'", "Try: 'What is salinity in tropical regions?'"],
                error=ai_result.get("error")
            )

        # Generate contextual suggestions
        suggestions = get_argo_contextual_suggestions(message)

        # Enhanced data insights with JARVIS mode info
        data_insights = {
            "total_records": ai_result.get("total_records", 0),
            "model_used": ai_result.get("model_used", "unknown"),
            "jarvis_mode": ai_result.get("jarvis_mode", False),
            "sql_generated": bool(ai_result.get("sql_generated")),
            "dynamic_query": ai_result.get("sql_generated", "")[:100] + "..." if ai_result.get("sql_generated") else ""
        }

        # Add dynamic data to insights if available
        if ai_result.get("dynamic_data"):
            sample_data = ai_result["dynamic_data"][:3]  # First 3 records
            data_insights["sample_data"] = sample_data

        return ChatResponse(
            answer=ai_result["answer"],
            suggestions=suggestions,
            data_insights=data_insights
        )

    except Exception as e:
        print(f"Chat endpoint error: {e}")
        return ChatResponse(
            answer="I encountered an issue processing your request. Please ensure the AI service is properly configured with an OpenAI API key.",
            suggestions=["Try: 'Show temperature data'", "Try: 'Tell me about ocean salinity'"],
            error=str(e)
        )

@chat_router.post("/stream")
async def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """Stream a response incrementally as plain text chunks.

    Dev-only by ENV=dev. Splits the summarized text into tokens and streams
    them with small delays to simulate generation.
    """
    # if os.getenv("ENV", "dev") != "dev":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Disabled in non-dev environments")

    def clean_text(s: str) -> str:
        s = unicodedata.normalize('NFKD', s)
        s = s.replace(""", '"').replace(""", '"').replace("'", "'").replace("–", "-")
        s = ''.join(ch for ch in s if ch.isprintable())
        return s

    message_raw = (req.message or "").strip()
    message = clean_text(message_raw)
    print(f"DEBUG: Original: '{message_raw}' -> Cleaned: '{message}'")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    # Precompute the response text (intent summary with citations, else RAG, else fallback)
    def parse_intent(msg: str) -> Dict[str, Any]:
        m = msg.lower()
        intent: Dict[str, Any] = {}
        if "equator" in m:
            intent.update({"lat_min": -10, "lat_max": 10})
        band = re.search(r"lat\s*(-?\d{1,2})\s*(?:to|-)\s*(-?\d{1,2})", m)
        if band:
            a, b = int(band.group(1)), int(band.group(2))
            intent.update({"lat_min": min(a, b), "lat_max": max(a, b)})
        mon = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*(\d{4})?", m)
        month_map = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
        if mon:
            intent["month"] = month_map[mon.group(1)]
            if mon.group(2): intent["year"] = int(mon.group(2))
        yr = re.search(r"\b(20\d{2})\b", m)
        if yr and "year" not in intent: intent["year"] = int(yr.group(1))
        return intent

    def build_intent_summary(intent: Dict[str, Any]) -> Optional[str]:
        params: Dict[str, Any] = dict(skip=0, limit=1000)
        if "lat_min" in intent: params["lat_min"] = intent["lat_min"]
        if "lat_max" in intent: params["lat_max"] = intent["lat_max"]
        rows = get_profiles(db, **params)
        if not rows:
            return None
        if intent.get("year"):
            rows = [p for p in rows if p.year == intent["year"]]
        if intent.get("month"):
            rows = [p for p in rows if p.month == intent["month"]]
        if not rows:
            return None
        temps = [float(p.temperature) for p in rows if p.temperature is not None]
        sals = [float(p.salinity) for p in rows if p.salinity is not None]
        depths = [float(p.depth) for p in rows if p.depth is not None]
        parts = []
        if "lat_min" in intent and "lat_max" in intent:
            parts.append(f"Latitude {intent['lat_min']} to {intent['lat_max']}°")
        if intent.get("year"): parts.append(f"Year {intent['year']}")
        if intent.get("month"): parts.append(f"Month {intent['month']}")
        head = ", ".join(parts) if parts else "Selected region"
        out = [f"{head}: {len(rows)} profiles."]
        if temps: out.append(f"Temperature avg {statistics.fmean(temps):.2f} degC (min {min(temps):.2f}, max {max(temps):.2f}).")
        if sals: out.append(f"Salinity avg {statistics.fmean(sals):.2f} PSU (min {min(sals):.2f}, max {max(sals):.2f}).")
        if depths: out.append(f"Depth range {min(depths):.0f}–{max(depths):.0f} m.")
        ctx = retrieve(message)
        cites = [c.get('text','') for c in ctx[:2]]
        if cites:
            out.append("Sources:\n" + "\n".join([f"- {c}" for c in cites]))
        return " ".join(out)

    # Compute response text with robust error handling
    text = "I couldn't derive a specific insight from the data. Try refining filters or asking about a region/time window."
    try:
        intent = parse_intent(message)
        if intent:
            summary = build_intent_summary(intent)
            if summary:
                text = summary
        # Always try RAG as fallback if no intent summary or no intent detected
        if text == "I couldn't derive a specific insight from the data. Try refining filters or asking about a region/time window.":
            try:
                ctx = retrieve(message)
                rag_summary = summarize(message, ctx)
                if rag_summary and rag_summary.strip() and rag_summary != "No results found.":
                    text = rag_summary
            except Exception:
                pass
    except Exception as e:
        # Log the error for debugging but don't crash
        print(f"Chat stream error: {e}")
        text = f"I encountered an issue processing your request. Please try rephrasing or ask about a specific region/time period."

    async def token_gen():
        try:
            tokens = text.split(" ")
            for tok in tokens:
                yield tok + " "
                await asyncio.sleep(0.03)
        except Exception as e:
            # Fallback if streaming fails
            yield f"Error streaming response: {str(e)}"

    return StreamingResponse(token_gen(), media_type="text/plain")

@data_router.post("/profile")
async def create_profile_endpoint(
    payload: CreateProfileRequest,
    db: Session = Depends(get_db)
):
    """Create a new ARGO float profile"""
    try:
        # Validate input parameters
        if not (-90 <= payload.latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        if not (-180 <= payload.longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        if payload.depth < 0:
            raise HTTPException(status_code=400, detail="Depth must be non-negative")
        if not (1 <= payload.month <= 12):
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        if not (1900 <= payload.year <= 2100):
            raise HTTPException(status_code=400, detail="Year must be between 1900 and 2100")

        # Validate oceanographic parameters
        if not (-5 <= payload.temperature <= 50):
            raise HTTPException(status_code=400, detail="Temperature should be between -5°C and 50°C")
        if not (0 <= payload.salinity <= 50):
            raise HTTPException(status_code=400, detail="Salinity should be between 0 and 50 PSU")

        # Create profile in database
        profile = create_profile(
            db=db,
            float_id=payload.float_id or "dev-float",
            latitude=payload.latitude,
            longitude=payload.longitude,
            depth=payload.depth,
            temperature=payload.temperature,
            salinity=payload.salinity,
            month=payload.month,
            year=payload.year,
            date=payload.date.isoformat() if payload.date else None,
        )

        return {
            "message": "Profile created successfully",
            "id": profile.id,
            "float_id": profile.float_id,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "depth": profile.depth,
            "temperature": profile.temperature,
            "salinity": profile.salinity,
            "month": profile.month,
            "year": profile.year,
            "date": profile.date.isoformat() if profile.date else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")

@data_router.get("/profile/{profile_id}")
async def get_profile_endpoint(profile_id: int, db: Session = Depends(get_db)):
    prof = get_profile_by_id(db, profile_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "id": prof.id,
        "float_id": prof.float_id,
        "latitude": prof.latitude,
        "longitude": prof.longitude,
        "depth": prof.depth,
        "temperature": prof.temperature,
        "salinity": prof.salinity,
        "month": prof.month,
        "year": prof.year,
        "date": prof.date.isoformat() if prof.date else None,
    }

@data_router.put("/profile/{profile_id}")
async def update_profile_endpoint(profile_id: int, payload: UpdateProfileRequest, db: Session = Depends(get_db)):
    updated = crud_update_profile(
        db,
        profile_id,
        float_id=payload.float_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        depth=payload.depth,
        temperature=payload.temperature,
        salinity=payload.salinity,
        month=payload.month,
        year=payload.year,
        date=payload.date.isoformat() if payload.date else None,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "message": "Profile updated",
        "id": updated.id,
        "float_id": updated.float_id,
        "latitude": updated.latitude,
        "longitude": updated.longitude,
        "depth": updated.depth,
        "temperature": updated.temperature,
        "salinity": updated.salinity,
        "month": updated.month,
        "year": updated.year,
        "date": updated.date.isoformat() if updated.date else None,
    }

@data_router.delete("/profile/{profile_id}")
async def delete_profile_endpoint(profile_id: int, db: Session = Depends(get_db)):
    ok = crud_delete_profile(db, profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True, "id": profile_id}

@data_router.post("/profiles/bulk")
async def create_profiles_bulk(reqs: List[CreateProfileRequest], db: Session = Depends(get_db)):
    """Dev-only: Bulk insert Profiles from a JSON array.

    Payload example (array of objects):
    [
      {"float_id":"dev-001","latitude":12.3,"longitude":45.6,"depth":100,"temperature":20.1,
       "salinity":35.0,"month":9,"year":2025,"date":"2025-09-20"}
    ]
    """
    try:
        items = []
        for r in reqs:
            items.append(Profile(
                float_id=r.float_id or "dev-float",
                latitude=r.latitude,
                longitude=r.longitude,
                depth=r.depth,
                temperature=r.temperature,
                salinity=r.salinity,
                month=r.month,
                year=r.year,
                date=r.date,
            ))
        db.add_all(items)
        db.commit()
        # Return minimal summary to keep response small
        return {"inserted": len(items)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed bulk insert: {e}")

@data_router.get("/profiles")
async def get_profiles_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    depth_min: Optional[float] = Query(None, ge=0),
    depth_max: Optional[float] = Query(None, ge=0),
    temp_min: Optional[float] = Query(None),
    temp_max: Optional[float] = Query(None),
    salinity_min: Optional[float] = Query(None),
    salinity_max: Optional[float] = Query(None),
    lat_min: Optional[float] = Query(None, ge=-90),
    lat_max: Optional[float] = Query(None, le=90),
    lon_min: Optional[float] = Query(None, ge=-180),
    lon_max: Optional[float] = Query(None, le=180),
    db: Session = Depends(get_db)
):
    """Get ARGO float profiles with advanced filtering"""
    profiles = get_profiles(
        db, 
        skip=skip, 
        limit=limit,
        depth_min=depth_min,
        depth_max=depth_max,
        temp_min=temp_min,
        temp_max=temp_max,
        salinity_min=salinity_min,
        salinity_max=salinity_max,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max
    )
    return {"results": profiles, "total": len(profiles), "filters_applied": {
        "depth_range": [depth_min, depth_max],
        "temperature_range": [temp_min, temp_max],
        "salinity_range": [salinity_min, salinity_max],
        "latitude_range": [lat_min, lat_max],
        "longitude_range": [lon_min, lon_max]
    }}

@data_router.get("/nearest")
async def get_nearest_profiles_endpoint(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(100, ge=1, le=1000),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Find nearest ARGO float profiles to given coordinates"""
    profiles = get_nearest_profiles(db, latitude, longitude, radius, limit)
    return {"results": profiles, "count": len(profiles), "center": {"latitude": latitude, "longitude": longitude}, "radius_km": radius}

@data_router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """Get comprehensive statistics about the data"""
    analytics = AnalyticsEngine(db)
    return analytics.get_basic_statistics()

@data_router.get("/analytics/depth-distribution")
async def get_depth_distribution(db: Session = Depends(get_db)):
    """Get depth distribution analysis"""
    analytics = AnalyticsEngine(db)
    return {"distribution": analytics.get_depth_distribution()}

@data_router.get("/analytics/geographic-distribution")
async def get_geographic_distribution(
    grid_size: float = Query(5.0, ge=1.0, le=50.0),
    db: Session = Depends(get_db)
):
    """Get geographic distribution in grid cells"""
    analytics = AnalyticsEngine(db)
    return {"distribution": analytics.get_geographic_distribution(grid_size)}

@data_router.get("/analytics/temporal")
async def get_temporal_analysis(db: Session = Depends(get_db)):
    """Get temporal analysis by month and year"""
    analytics = AnalyticsEngine(db)
    return analytics.get_temporal_analysis()

@data_router.get("/analytics/correlation")
async def get_correlation_analysis(db: Session = Depends(get_db)):
    """Get temperature-salinity correlation analysis"""
    analytics = AnalyticsEngine(db)
    return analytics.get_temperature_salinity_correlation()

@data_router.get("/analytics/depth-profiles")
async def get_depth_profile_analysis(
    depth_min: Optional[float] = Query(None, ge=0),
    depth_max: Optional[float] = Query(None, ge=0),
    db: Session = Depends(get_db)
):
    """Get depth profile analysis"""
    analytics = AnalyticsEngine(db)
    depth_range = (depth_min, depth_max) if depth_min and depth_max else None
    return analytics.get_depth_profile_analysis(depth_range)

@data_router.get("/analytics/outliers")
async def get_outlier_analysis(
    threshold: float = Query(2.0, ge=1.0, le=5.0),
    db: Session = Depends(get_db)
):
    """Get outlier analysis"""
    analytics = AnalyticsEngine(db)
    return analytics.get_outlier_analysis(threshold)

@data_router.get("/analytics/advanced/{query_type}")
async def get_advanced_analysis(
    query_type: str,
    db: Session = Depends(get_db),
    **kwargs
):
    """Execute advanced analytical queries"""
    analytics = AnalyticsEngine(db)
    return analytics.get_advanced_queries(query_type, **kwargs)

@data_router.get("/export/csv")
async def export_csv(
    depth_min: Optional[float] = Query(None, ge=0),
    depth_max: Optional[float] = Query(None, ge=0),
    temp_min: Optional[float] = Query(None),
    temp_max: Optional[float] = Query(None),
    salinity_min: Optional[float] = Query(None),
    salinity_max: Optional[float] = Query(None),
    lat_min: Optional[float] = Query(None, ge=-90),
    lat_max: Optional[float] = Query(None, le=90),
    lon_min: Optional[float] = Query(None, ge=-180),
    lon_max: Optional[float] = Query(None, le=180),
    db: Session = Depends(get_db)
):
    """Export data as CSV with filtering"""
    profiles = get_profiles(
        db, 
        skip=0, 
        limit=50000,  # Increased limit for export
        depth_min=depth_min,
        depth_max=depth_max,
        temp_min=temp_min,
        temp_max=temp_max,
        salinity_min=salinity_min,
        salinity_max=salinity_max,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max
    )
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['id', 'latitude', 'longitude', 'depth', 'temperature', 'salinity', 'month', 'year'])
    
    # Write data
    for profile in profiles:
        writer.writerow([
            profile.id,
            profile.latitude,
            profile.longitude,
            profile.depth,
            profile.temperature,
            profile.salinity,
            profile.month,
            profile.year
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=floatchat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@data_router.get("/export/ascii")
async def export_ascii(
    depth_min: Optional[float] = Query(None, ge=0),
    depth_max: Optional[float] = Query(None, ge=0),
    temp_min: Optional[float] = Query(None),
    temp_max: Optional[float] = Query(None),
    salinity_min: Optional[float] = Query(None),
    salinity_max: Optional[float] = Query(None),
    lat_min: Optional[float] = Query(None, ge=-90),
    lat_max: Optional[float] = Query(None, le=90),
    lon_min: Optional[float] = Query(None, ge=-180),
    lon_max: Optional[float] = Query(None, le=180),
    db: Session = Depends(get_db)
):
    """Export data as ASCII format"""
    profiles = get_profiles(
        db, 
        skip=0, 
        limit=50000,
        depth_min=depth_min,
        depth_max=depth_max,
        temp_min=temp_min,
        temp_max=temp_max,
        salinity_min=salinity_min,
        salinity_max=salinity_max,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max
    )
    
    # Generate ASCII format
    ascii_content = f"# FloatChat ARGO Data Export\n"
    ascii_content += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    ascii_content += f"# Total Records: {len(profiles)}\n"
    ascii_content += f"# Format: ID LAT LON DEPTH TEMP SAL MONTH YEAR\n"
    ascii_content += f"#\n"
    
    for profile in profiles:
        ascii_content += f"{profile.id:8d} {profile.latitude:8.3f} {profile.longitude:9.3f} {profile.depth:5.0f} {profile.temperature:6.2f} {profile.salinity:6.3f} {profile.month:2d} {profile.year:4d}\n"
    
    return Response(
        content=ascii_content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=floatchat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"}
    )

@data_router.get("/export/netcdf")
async def export_netcdf(db: Session = Depends(get_db)):
    """Export data as NetCDF (placeholder)"""
    profiles = get_profiles(db, skip=0, limit=10000)
    # This would generate actual NetCDF in production
    return {"message": "NetCDF export endpoint - requires netCDF4 library implementation", "record_count": len(profiles)}

@data_router.get("/export/json")
async def export_json(
    depth_min: Optional[float] = Query(None, ge=0),
    depth_max: Optional[float] = Query(None, ge=0),
    temp_min: Optional[float] = Query(None),
    temp_max: Optional[float] = Query(None),
    salinity_min: Optional[float] = Query(None),
    salinity_max: Optional[float] = Query(None),
    lat_min: Optional[float] = Query(None, ge=-90),
    lat_max: Optional[float] = Query(None, le=90),
    lon_min: Optional[float] = Query(None, ge=-180),
    lon_max: Optional[float] = Query(None, le=180),
    db: Session = Depends(get_db)
):
    """Export data as JSON"""
    profiles = get_profiles(
        db, 
        skip=0, 
        limit=50000,
        depth_min=depth_min,
        depth_max=depth_max,
        temp_min=temp_min,
        temp_max=temp_max,
        salinity_min=salinity_min,
        salinity_max=salinity_max,
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max
    )
    
    export_data = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "total_records": len(profiles),
            "filters": {
                "depth_range": [depth_min, depth_max],
                "temperature_range": [temp_min, temp_max],
                "salinity_range": [salinity_min, salinity_max],
                "latitude_range": [lat_min, lat_max],
                "longitude_range": [lon_min, lon_max]
            }
        },
        "profiles": [
            {
                "id": profile.id,
                "latitude": profile.latitude,
                "longitude": profile.longitude,
                "depth": profile.depth,
                "temperature": profile.temperature,
                "salinity": profile.salinity,
                "month": profile.month,
                "year": profile.year
            }
            for profile in profiles
        ]
    }
    
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=floatchat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )

@admin_router.post("/index")
async def index_metadata_endpoint(req: IndexRequest):
    """Index metadata for RAG"""
    try:
        index_metadata(req.docs)
        return {"indexed": len(req.docs)}
    except Exception as e:
        # Surface the error so dev can see the failure cause
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

@admin_router.post("/reindex")
async def admin_reindex(db: Session = Depends(get_db)):
    """Build metadata docs (5° latitude bands x month/year) and index them.

    Dev utility so the UI can re-index after new data loads.
    """
    # Fetch a large slice of profiles directly from DB
    profiles = get_profiles(db, skip=0, limit=100000)

    def lat_band(lat: float, band: int = 5) -> str:
        lo = math.floor(lat / band) * band
        hi = lo + band
        return f"{int(lo)}_to_{int(hi)}"

    groups: Dict[tuple, list] = defaultdict(list)
    for p in profiles:
        try:
            b = lat_band(float(p.latitude))
            y = int(p.year or 0)
            m = int(p.month or 0)
            groups[(b, y, m)].append(p)
        except Exception:
            continue

    docs = []
    for (band, year, month), rows in groups.items():
        try:
            temps = [float(r.temperature) for r in rows if r.temperature is not None]
            sals = [float(r.salinity) for r in rows if r.salinity is not None]
            depths = [float(r.depth) for r in rows if r.depth is not None]
            parts = [
                f"Latitude band {band.replace('_',' ')}",
                f"Year {year}, Month {month}",
                f"Profiles {len(rows)}",
            ]
            if temps:
                t_avg = statistics.fmean(temps)
                t_med = statistics.median(temps)
                t_sd = statistics.pstdev(temps) if len(temps) > 1 else 0.0
                parts.append(f"Temp avg {t_avg:.2f}°C, med {t_med:.2f}, sd {t_sd:.2f} (min {min(temps):.2f}, max {max(temps):.2f})")
            if sals:
                s_avg = statistics.fmean(sals)
                s_med = statistics.median(sals)
                s_sd = statistics.pstdev(sals) if len(sals) > 1 else 0.0
                parts.append(f"Sal avg {s_avg:.2f} PSU, med {s_med:.2f}, sd {s_sd:.2f} (min {min(sals):.2f}, max {max(sals):.2f})")
            if depths:
                parts.append(f"Depth range {min(depths):.0f}–{max(depths):.0f} m")
            text = ". ".join(parts) + "."
            doc_id = f"band:{band}|y:{year}|m:{month}"
            docs.append({"id": doc_id, "text": text})
        except Exception:
            continue

    if not docs:
        return {"indexed": 0, "message": "No docs built"}
    index_metadata(docs)
    return {"indexed": len(docs)}

@admin_router.get("/health")
async def admin_health(db: Session = Depends(get_db)):
    """Admin health check with database status"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }