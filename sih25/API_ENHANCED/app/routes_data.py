from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import get_db
import xarray as xr
import io
from dotenv import load_dotenv
import os
import pandas as pd
from crud import get_nearest_profiles, query_profiles, create_profile
import statistics
from db import DATABASE_URL

load_dotenv()

engine = create_engine(DATABASE_URL)

router = APIRouter()

@router.get("/nearest")
async def nearest(lat: float, lon: float, limit: int = 10):
    rows = get_nearest_profiles(engine, lat, lon, limit)
    return {"results": rows}

@router.get("/profiles")
async def profiles(min_lat: float | None = None, max_lat: float | None = None,
                   min_lon: float | None = None, max_lon: float | None = None,
                   month: int | None = None, year: int | None = None, limit: int = 500):
    rows = query_profiles(engine, min_lat, max_lat, min_lon, max_lon, month, year, limit)
    return {"results": rows}

@router.get("/explain")
async def explain(
    lat_min: float | None = Query(None),
    lat_max: float | None = Query(None),
    lon_min: float | None = Query(None),
    lon_max: float | None = Query(None),
    depth_min: float | None = Query(None),
    depth_max: float | None = Query(None),
    temp_min: float | None = Query(None),
    temp_max: float | None = Query(None),
    month: int | None = Query(None),
    year: int | None = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
):
    # Map to existing query function signature
    rows = query_profiles(
        engine,
        lat_min, lat_max,
        lon_min, lon_max,
        month, year,
        limit
    )
    # Apply optional numeric filters here if provided
    def within(val, vmin, vmax):
        if vmin is not None and val < vmin: return False
        if vmax is not None and val > vmax: return False
        return True
    filtered = []
    for r in rows:
        if not within(r.get('depth', 0), depth_min, depth_max):
            continue
        if not within(r.get('temperature', 0.0), temp_min, temp_max):
            continue
        filtered.append(r)

    if not filtered:
        return {
            "count": 0,
            "summary": "No profiles matched the current view and filters. Try widening the bounds or relaxing filters.",
            "stats": {}
        }

    temps = [float(r['temperature']) for r in filtered if r.get('temperature') is not None]
    sals = [float(r['salinity']) for r in filtered if r.get('salinity') is not None]
    depths = [float(r['depth']) for r in filtered if r.get('depth') is not None]

    def safe_mean(vals):
        return statistics.fmean(vals) if vals else None

    stats = {
        "count": len(filtered),
        "temperature": {
            "avg": safe_mean(temps),
            "min": min(temps) if temps else None,
            "max": max(temps) if temps else None,
        },
        "salinity": {
            "avg": safe_mean(sals),
            "min": min(sals) if sals else None,
            "max": max(sals) if sals else None,
        },
        "depth": {
            "min": min(depths) if depths else None,
            "max": max(depths) if depths else None,
        },
    }

    summary = (
        f"Found {stats['count']} profiles in the current view. "
        f"Temperature avg {stats['temperature']['avg']:.2f}°C "
        f"(min {stats['temperature']['min']:.2f}, max {stats['temperature']['max']:.2f}). "
        f"Salinity avg {stats['salinity']['avg']:.2f} PSU "
        f"(min {stats['salinity']['min']:.2f}, max {stats['salinity']['max']:.2f}). "
        f"Depth range {stats['depth']['min']}–{stats['depth']['max']} m."
    ) if temps and sals and depths else (
        f"Found {stats['count']} profiles in the current view. Some stats are unavailable due to missing values."
    )

    return {"count": stats['count'], "summary": summary, "stats": stats}

@router.get("/export/netcdf")
async def export_netcdf(min_lat: float | None = None, max_lat: float | None = None,
                        min_lon: float | None = None, max_lon: float | None = None,
                        month: int | None = None, year: int | None = None, limit: int = 1000):
    rows = query_profiles(engine, min_lat, max_lat, min_lon, max_lon, month, year, limit)
    df = pd.DataFrame(rows)
    if xr is None or df.empty:
        # Fallback to CSV if xarray unavailable
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type='text/csv',
            headers={"Content-Disposition": "attachment; filename=export.csv"}
        )
    # Build minimal dataset
    da_temp = xr.DataArray(df['temperature'], dims=['obs'])
    da_sal = xr.DataArray(df['salinity'], dims=['obs'])
    da_lat = xr.DataArray(df['latitude'], dims=['obs'])
    da_lon = xr.DataArray(df['longitude'], dims=['obs'])
    da_depth = xr.DataArray(df['depth'], dims=['obs'])
    ds = xr.Dataset({
        "temperature": da_temp,
        "salinity": da_sal,
        "latitude": da_lat,
        "longitude": da_lon,
        "depth": da_depth,
    })
    buf = io.BytesIO()
    ds.to_netcdf(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type='application/netcdf',
        headers={"Content-Disposition": "attachment; filename=export.nc"}
    )

@router.get("/export/csv")
async def export_csv(page: int = 1, page_size: int = 1000):
    # Fetch paginated data
    data = get_profiles(page, page_size)
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type='text/csv',
        headers={"Content-Disposition": "attachment; filename=export.csv"}
    )

@router.get("/export/ascii")
async def export_ascii(min_lat: float | None = None, max_lat: float | None = None,
                       min_lon: float | None = None, max_lon: float | None = None,
                       month: int | None = None, year: int | None = None, limit: int = 1000):
    rows = query_profiles(engine, min_lat, max_lat, min_lon, max_lon, month, year, limit)
    buf = io.StringIO()
    buf.write("# id lat lon depth temperature salinity\n")
    for r in rows:
        buf.write(f"{r['id']} {r['latitude']} {r['longitude']} {r['depth']} {r['temperature']} {r['salinity']}\n")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type='text/plain',
        headers={"Content-Disposition": "attachment; filename=export.txt"}
    )
