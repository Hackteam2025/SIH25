"""
Enhanced Profile model for ARGO float data
Supports NetCDF ingestion and advanced oceanographic parameters
"""

from sqlalchemy import Column, Integer, Float, String, Date, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, date
from typing import Optional, Dict, Any

Base = declarative_base()

class Profile(Base):
    """Enhanced ARGO Profile model with NetCDF support"""
    __tablename__ = "profiles"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Float identification
    float_id = Column(String(20), nullable=False, index=True)
    platform_number = Column(String(20), index=True)  # WMO platform number
    cycle_number = Column(Integer, default=0)  # Profile cycle number
    level_number = Column(Integer, default=0)  # Depth level within profile
    
    # Geographic coordinates
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    
    # Temporal information
    date = Column(Date, index=True)
    month = Column(Integer, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    julian_date = Column(Float)  # Original ARGO Julian date
    
    # Oceanographic measurements
    depth = Column(Float, nullable=False, index=True)  # Calculated from pressure
    pressure = Column(Float, index=True)  # Original pressure measurement
    temperature = Column(Float, nullable=False, index=True)  # Sea temperature (°C)
    salinity = Column(Float, nullable=False, index=True)  # Practical salinity (PSU)
    
    # Bio-Geo-Chemical parameters (BGC floats)
    oxygen = Column(Float)  # Dissolved oxygen (μmol/kg)
    nitrate = Column(Float)  # Nitrate concentration (μmol/kg)
    ph = Column(Float)  # pH
    chlorophyll = Column(Float)  # Chlorophyll-a (mg/m³)
    backscatter = Column(Float)  # Optical backscatter
    cdom = Column(Float)  # Colored Dissolved Organic Matter
    
    # Quality control flags
    temperature_qc = Column(Integer, default=1)  # ARGO QC flag for temperature
    salinity_qc = Column(Integer, default=1)  # ARGO QC flag for salinity
    pressure_qc = Column(Integer, default=1)  # ARGO QC flag for pressure
    position_qc = Column(Integer, default=1)  # ARGO QC flag for position
    
    # Data processing flags
    is_adjusted = Column(Boolean, default=False)  # Real-time vs delayed mode
    is_interpolated = Column(Boolean, default=False)  # Interpolated data point
    data_mode = Column(String(1), default='R')  # R=real-time, D=delayed-mode, A=adjusted
    
    # Metadata and provenance
    data_source = Column(String(50), default='ARGO')  # Data source identifier
    processing_level = Column(String(10), default='L2')  # Processing level
    institution = Column(String(100))  # Data center/institution
    project_name = Column(String(100))  # Project name
    pi_name = Column(String(200))  # Principal investigator
    
    # Technical metadata
    instrument_type = Column(String(50))  # Float/instrument type
    wmo_inst_type = Column(String(10))  # WMO instrument type
    float_serial_no = Column(String(20))  # Float serial number
    
    # Extended metadata (JSON field for flexibility)
    metadata = Column(JSON)  # Additional metadata as JSON
    
    # Audit fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Profile(id={self.id}, float_id='{self.float_id}', lat={self.latitude}, lon={self.longitude}, depth={self.depth}m)>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return {
            'id': self.id,
            'float_id': self.float_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'depth': self.depth,
            'temperature': self.temperature,
            'salinity': self.salinity,
            'pressure': self.pressure,
            'month': self.month,
            'year': self.year,
            'date': self.date.isoformat() if self.date else None,
            'cycle_number': self.cycle_number,
            'level_number': self.level_number,
            'oxygen': self.oxygen,
            'nitrate': self.nitrate,
            'ph': self.ph,
            'chlorophyll': self.chlorophyll,
            'temperature_qc': self.temperature_qc,
            'salinity_qc': self.salinity_qc,
            'data_mode': self.data_mode,
            'institution': self.institution,
            'project_name': self.project_name,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_argo_profile(cls, argo_profile, level_idx: int = 0):
        """Create Profile instance from ArgoProfile data"""
        return cls(
            float_id=argo_profile.float_id,
            latitude=argo_profile.latitude,
            longitude=argo_profile.longitude,
            depth=argo_profile.depth[level_idx] if level_idx < len(argo_profile.depth) else None,
            temperature=argo_profile.temperature[level_idx] if level_idx < len(argo_profile.temperature) else None,
            salinity=argo_profile.salinity[level_idx] if level_idx < len(argo_profile.salinity) else None,
            pressure=argo_profile.pressure[level_idx] if level_idx < len(argo_profile.pressure) else None,
            month=argo_profile.date.month,
            year=argo_profile.date.year,
            date=argo_profile.date.date(),
            cycle_number=argo_profile.cycle_number,
            level_number=level_idx,
            metadata=argo_profile.metadata
        )

class FloatTrajectory(Base):
    """Float trajectory and deployment information"""
    __tablename__ = "float_trajectories"
    
    id = Column(Integer, primary_key=True, index=True)
    float_id = Column(String(20), nullable=False, index=True)
    
    # Deployment information
    deployment_date = Column(Date)
    deployment_latitude = Column(Float)
    deployment_longitude = Column(Float)
    deployment_platform = Column(String(100))  # Ship/platform name
    
    # Current status
    last_contact_date = Column(Date)
    last_latitude = Column(Float)
    last_longitude = Column(Float)
    status = Column(String(20), default='ACTIVE')  # ACTIVE, INACTIVE, DEAD
    
    # Float specifications
    float_type = Column(String(50))
    manufacturer = Column(String(50))
    model = Column(String(50))
    serial_number = Column(String(20))
    
    # Mission parameters
    cycle_time = Column(Integer, default=10)  # Days between cycles
    parking_depth = Column(Float, default=1000)  # Parking depth (m)
    profile_depth = Column(Float, default=2000)  # Maximum profile depth (m)
    
    # Metadata
    metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<FloatTrajectory(float_id='{self.float_id}', status='{self.status}')>"

class DataSummary(Base):
    """Summary statistics for data discovery and RAG"""
    __tablename__ = "data_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Spatial-temporal bounds
    region_name = Column(String(100), index=True)  # e.g., "North Atlantic", "Indian Ocean"
    min_latitude = Column(Float)
    max_latitude = Column(Float)
    min_longitude = Column(Float)
    max_longitude = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Data statistics
    profile_count = Column(Integer, default=0)
    float_count = Column(Integer, default=0)
    min_depth = Column(Float)
    max_depth = Column(Float)
    avg_temperature = Column(Float)
    min_temperature = Column(Float)
    max_temperature = Column(Float)
    avg_salinity = Column(Float)
    min_salinity = Column(Float)
    max_salinity = Column(Float)
    
    # Text summary for RAG
    summary_text = Column(Text)  # Natural language summary
    keywords = Column(JSON)  # Keywords for search
    
    # Vector embedding (for similarity search)
    embedding = Column(JSON)  # Store embedding as JSON array
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<DataSummary(region='{self.region_name}', profiles={self.profile_count})>"
