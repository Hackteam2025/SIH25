from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

from .db import get_db
from .models import Profile
from .rag import retrieve, summarize

router = APIRouter()

class NaturalLanguageQuery(BaseModel):
    query: str
    language: Optional[str] = "en"
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    answer: str
    data: Optional[List[Dict[str, Any]]] = None
    visualization_config: Optional[Dict[str, Any]] = None
    query_type: Optional[str] = None
    error: Optional[str] = None

async def rag_query(query: str, db: Session) -> Dict[str, Any]:
    """Process a natural language query using RAG and return structured results"""
    try:
        # Use RAG to get context
        context = retrieve(query, k=3)
        answer = summarize(query, context)

        # Simple query processing - for now return basic response
        # In a full implementation, this would parse the query and fetch actual data
        return {
            "answer": answer,
            "data": [],  # Could be populated with actual DB query results
            "query_type": "general"
        }
    except Exception as e:
        raise Exception(f"RAG query failed: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def natural_language_query(
    request: NaturalLanguageQuery,
    db: Session = Depends(get_db)
):
    try:
        result = await rag_query(request.query, db)

        chart_config = generate_visualization_config(result.get("data", []), request.query)

        return QueryResponse(
            success=True,
            answer=result.get("answer", "I found some ocean data for you."),
            data=result.get("data", []),
            visualization_config=chart_config,
            query_type=result.get("query_type", "general")
        )

    except Exception as e:
        return QueryResponse(
            success=False,
            answer=f"Sorry, I encountered an error: {str(e)}",
            error=str(e)
        )

def generate_visualization_config(data: List[Dict], query: str) -> Dict[str, Any]:
    if not data or len(data) == 0:
        return None

    query_lower = query.lower()

    if "temperature" in query_lower or "temp" in query_lower:
        return {
            "type": "line",
            "title": "Temperature Profile",
            "x_axis": "depth",
            "y_axis": "temperature",
            "x_label": "Depth (m)",
            "y_label": "Temperature (°C)",
            "color": "#FF6B6B"
        }

    elif "salinity" in query_lower or "psal" in query_lower:
        return {
            "type": "line",
            "title": "Salinity Profile",
            "x_axis": "depth",
            "y_axis": "salinity",
            "x_label": "Depth (m)",
            "y_label": "Salinity (PSU)",
            "color": "#4ECDC4"
        }

    elif "map" in query_lower or "location" in query_lower or "float" in query_lower:
        return {
            "type": "map",
            "title": "Float Locations",
            "data_points": [
                {"lat": d.get("latitude"), "lon": d.get("longitude"), "value": d.get("temperature", 0)}
                for d in data if d.get("latitude") and d.get("longitude")
            ]
        }

    else:
        return {
            "type": "scatter",
            "title": "Ocean Data Visualization",
            "x_axis": "depth",
            "y_axis": "value",
            "x_label": "Depth (m)",
            "y_label": "Value",
            "color": "#95E1D3"
        }

@router.post("/voice/query", response_model=QueryResponse)
async def voice_query(
    request: NaturalLanguageQuery,
    db: Session = Depends(get_db)
):
    return await natural_language_query(request, db)