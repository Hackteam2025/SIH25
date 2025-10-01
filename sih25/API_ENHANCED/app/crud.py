from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, desc
from sqlalchemy.engine import Engine
from .models import Profile
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import math

def get_profiles(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    depth_min: Optional[float] = None,
    depth_max: Optional[float] = None,
    temp_min: Optional[float] = None,
    temp_max: Optional[float] = None,
    salinity_min: Optional[float] = None,
    salinity_max: Optional[float] = None,
    lat_min: Optional[float] = None,
    lat_max: Optional[float] = None,
    lon_min: Optional[float] = None,
    lon_max: Optional[float] = None
) -> List[Profile]:
    """Get ARGO float profiles with advanced filtering"""
    query = db.query(Profile)
    
    # Apply filters
    filters = []
    
    if depth_min is not None:
        filters.append(Profile.depth >= depth_min)
    if depth_max is not None:
        filters.append(Profile.depth <= depth_max)
    if temp_min is not None:
        filters.append(Profile.temperature >= temp_min)
    if temp_max is not None:
        filters.append(Profile.temperature <= temp_max)
    if salinity_min is not None:
        filters.append(Profile.salinity >= salinity_min)
    if salinity_max is not None:
        filters.append(Profile.salinity <= salinity_max)
    if lat_min is not None:
        filters.append(Profile.lat >= lat_min)
    if lat_max is not None:
        filters.append(Profile.lat <= lat_max)
    if lon_min is not None:
        filters.append(Profile.lon >= lon_min)
    if lon_max is not None:
        filters.append(Profile.lon <= lon_max)
    
    if filters:
        query = query.filter(and_(*filters))
    
    return query.offset(skip).limit(limit).all()

def get_nearest_profiles(db: Session, latitude: float, longitude: float, radius: float = 100, limit: int = 10) -> List[Profile]:
    """Find nearest ARGO float profiles to given coordinates"""
    profiles = db.query(Profile).all()
    
    # Calculate distances and filter by radius
    nearest = []
    for profile in profiles:
        # Simple distance calculation (not accurate for large distances)
        distance = math.sqrt(
            (profile.lat - latitude) ** 2 + 
            (profile.lon - longitude) ** 2
        ) * 111  # Rough conversion to km
        
        if distance <= radius:
            nearest.append(profile)
    
    # Sort by distance and return limited results
    nearest.sort(key=lambda p: math.sqrt(
        (p.lat - latitude) ** 2 + 
        (p.lon - longitude) ** 2
    ))
    
    return nearest[:limit]

def get_nearest_profiles_legacy(engine: Engine, lat: float, lon: float, limit: int = 10) -> List[Dict]:
    """Legacy function for backward compatibility"""
    # Haversine approximation via simple ordering by squared distance
    query = text(
        """
        SELECT id, lat as latitude, lon as longitude, depth, temperature, salinity,
            ((lat-:lat)*(lat-:lat) + (lon-:lon)*(lon-:lon)) AS dist2
        FROM profiles
        ORDER BY dist2 ASC
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(query, {"lat": lat, "lon": lon, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]

def query_profiles(engine: Engine, min_lat=None, max_lat=None, min_lon=None, max_lon=None, month=None, year=None, limit: int = 500) -> List[Dict]:
    """Legacy function for backward compatibility"""
    clauses = []
    params = {"limit": limit}
    if min_lat is not None:
        clauses.append("lat >= :min_lat"); params["min_lat"] = min_lat
    if max_lat is not None:
        clauses.append("lat <= :max_lat"); params["max_lat"] = max_lat
    if min_lon is not None:
        clauses.append("lon >= :min_lon"); params["min_lon"] = min_lon
    if max_lon is not None:
        clauses.append("lon <= :max_lon"); params["max_lon"] = max_lon
    if month is not None:
        clauses.append("month = :month"); params["month"] = month
    if year is not None:
        clauses.append("year = :year"); params["year"] = year
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    q = text(f"SELECT id, lat as latitude, lon as longitude, depth, temperature, salinity, month, year FROM profiles{where} LIMIT :limit")
    with engine.begin() as conn:
        rows = conn.execute(q, params).mappings().all()
    return [dict(r) for r in rows]

def get_profiles_by_region(
    db: Session,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    skip: int = 0,
    limit: int = 100
) -> List[Profile]:
    """Get profiles within a specific geographic region"""
    return db.query(Profile).filter(
        and_(
            Profile.lat >= lat_min,
            Profile.lat <= lat_max,
            Profile.lon >= lon_min,
            Profile.lon <= lon_max
        )
    ).offset(skip).limit(limit).all()

def get_profiles_by_depth_range(
    db: Session,
    depth_min: float,
    depth_max: float,
    skip: int = 0,
    limit: int = 100
) -> List[Profile]:
    """Get profiles within a specific depth range"""
    return db.query(Profile).filter(
        and_(
            Profile.depth >= depth_min,
            Profile.depth <= depth_max
        )
    ).offset(skip).limit(limit).all()

def get_profiles_by_temperature_range(
    db: Session,
    temp_min: float,
    temp_max: float,
    skip: int = 0,
    limit: int = 100
) -> List[Profile]:
    """Get profiles within a specific temperature range"""
    return db.query(Profile).filter(
        and_(
            Profile.temperature >= temp_min,
            Profile.temperature <= temp_max
        )
    ).offset(skip).limit(limit).all()

def get_profiles_by_salinity_range(
    db: Session,
    salinity_min: float,
    salinity_max: float,
    skip: int = 0,
    limit: int = 100
) -> List[Profile]:
    """Get profiles within a specific salinity range"""
    return db.query(Profile).filter(
        and_(
            Profile.salinity >= salinity_min,
            Profile.salinity <= salinity_max
        )
    ).offset(skip).limit(limit).all()

def search_profiles(
    db: Session,
    search_term: str,
    skip: int = 0,
    limit: int = 100
) -> List[Profile]:
    """Search profiles by ID, coordinates, or other fields"""
    search_pattern = f"%{search_term}%"
    
    return db.query(Profile).filter(
        or_(
            Profile.id.like(search_pattern),
            Profile.lat.like(search_pattern),
            Profile.lon.like(search_pattern),
            Profile.depth.like(search_pattern),
            Profile.temperature.like(search_pattern),
            Profile.salinity.like(search_pattern)
        )
    ).offset(skip).limit(limit).all()

def create_profile(
    db: Session,
    float_id: str,
    latitude: float,
    longitude: float,
    depth: float,
    temperature: float,
    salinity: float,
    month: int,
    year: int,
    date: Optional[str] = None
) -> Profile:
    """Create a new ARGO float profile"""
    from datetime import datetime

    # Convert date string to datetime object if provided
    date_obj = None
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            # If date parsing fails, try different format
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S').date()
            except ValueError:
                # If still fails, set to None
                date_obj = None

    db_profile = Profile(
        float_id=float_id,
        lat=latitude,  # Updated to use lat instead of latitude
        lon=longitude,  # Updated to use lon instead of longitude
        depth=depth,
        temperature=temperature,
        salinity=salinity,
        month=month,
        year=year,
        date=date_obj
    )

    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def get_profile_by_id(db: Session, profile_id: int) -> Optional[Profile]:
    return db.query(Profile).filter(Profile.id == profile_id).first()

def update_profile(
    db: Session,
    profile_id: int,
    *,
    float_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    depth: Optional[float] = None,
    temperature: Optional[float] = None,
    salinity: Optional[float] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    date: Optional[str] = None,
) -> Optional[Profile]:
    prof = get_profile_by_id(db, profile_id)
    if not prof:
        return None
    if float_id is not None: prof.float_id = float_id
    if latitude is not None: prof.lat = latitude  # Updated to use lat
    if longitude is not None: prof.lon = longitude  # Updated to use lon
    if depth is not None: prof.depth = depth
    if temperature is not None: prof.temperature = temperature
    if salinity is not None: prof.salinity = salinity
    if month is not None: prof.month = month
    if year is not None: prof.year = year
    if date is not None:
        try:
            prof.date = datetime.strptime(date, '%Y-%m-%d').date()
        except Exception:
            try:
                prof.date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S').date()
            except Exception:
                prof.date = None
    db.commit()
    db.refresh(prof)
    return prof

def delete_profile(db: Session, profile_id: int) -> bool:
    prof = get_profile_by_id(db, profile_id)
    if not prof:
        return False
    db.delete(prof)
    db.commit()
    return True

def get_recent_profiles(db: Session, hours: int = 1) -> List[Profile]:
    """Get profiles from the last specified hours"""
    from datetime import datetime, timedelta

    # Since Profile model doesn't have timestamps, we'll return a sample of recent profiles
    # In a real implementation, you'd filter by created_at or updated_at timestamp
    cutoff_time = datetime.now() - timedelta(hours=hours)

    # For now, just return the first 10 profiles as "recent"
    # This should be replaced with proper timestamp filtering in production
    return db.query(Profile).limit(10).all()