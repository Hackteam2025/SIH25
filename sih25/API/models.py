#!/usr/bin/env python3
"""
Pydantic models for MCP tool input/output validation
Ensures data integrity and ARGO protocol compliance
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

from pydantic import BaseModel, Field, validator


class DataMode(str, Enum):
    """ARGO data modes"""
    REAL_TIME = "R"
    ADJUSTED = "A"
    DELAYED = "D"


class QCFlag(int, Enum):
    """ARGO QC flag values"""
    NO_QC = 0
    GOOD = 1
    PROBABLY_GOOD = 2
    PROBABLY_BAD = 3
    BAD = 4
    CHANGED = 5
    NOT_USED = 6
    NOT_USED_2 = 7
    ESTIMATED = 8
    MISSING = 9


# Input Models
class BoundingBox(BaseModel):
    """Geographic bounding box for spatial queries"""
    min_lat: float = Field(..., ge=-90, le=90, description="Minimum latitude")
    max_lat: float = Field(..., ge=-90, le=90, description="Maximum latitude")
    min_lon: float = Field(..., ge=-180, le=180, description="Minimum longitude")
    max_lon: float = Field(..., ge=-180, le=180, description="Maximum longitude")

    @validator('max_lat')
    def validate_lat_bounds(cls, v, values):
        if 'min_lat' in values and v <= values['min_lat']:
            raise ValueError('max_lat must be greater than min_lat')
        return v

    @validator('max_lon')
    def validate_lon_bounds(cls, v, values):
        if 'min_lon' in values and v <= values['min_lon']:
            raise ValueError('max_lon must be greater than min_lon')
        return v


class ProfileQuery(BaseModel):
    """Query parameters for profile listing"""
    region: BoundingBox
    time_start: datetime = Field(..., description="Start of time range")
    time_end: datetime = Field(..., description="End of time range")
    has_bgc: bool = Field(default=False, description="Filter for BGC sensors")
    max_results: int = Field(default=100, le=1000, description="Maximum results")

    @validator('time_end')
    def validate_time_range(cls, v, values):
        if 'time_start' in values and v <= values['time_start']:
            raise ValueError('time_end must be after time_start')
        return v


class FloatSearchQuery(BaseModel):
    """Query parameters for float proximity search"""
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    radius_km: float = Field(..., gt=0, le=1000, description="Search radius in kilometers")
    max_results: int = Field(default=50, le=500, description="Maximum results")


class VariableStatsQuery(BaseModel):
    """Query for variable statistics"""
    profile_id: str = Field(..., description="Profile ID")
    variable: str = Field(..., description="Variable name (e.g., TEMP, PSAL)")


# Output Models
class FloatSummary(BaseModel):
    """Summary information about a float"""
    wmo_id: str
    deployment_date: Optional[datetime]
    last_contact: Optional[datetime]
    status: str
    pi_name: Optional[str]
    institution: Optional[str]
    total_profiles: int


class ProfileSummary(BaseModel):
    """Summary information about a profile"""
    profile_id: str
    float_wmo_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    data_mode: DataMode
    position_qc: QCFlag
    parameters_available: List[str]
    depth_range: Dict[str, float]  # {"min": 0.0, "max": 2000.0}


class ProfileDetail(BaseModel):
    """Detailed profile information"""
    profile_id: str
    float_wmo_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    data_mode: DataMode
    position_qc: QCFlag
    observations_count: int
    parameters: List[str]
    depth_range: Dict[str, float]
    data_provenance: Dict[str, Any]
    quality_summary: Dict[str, int]  # QC flag counts


class VariableStats(BaseModel):
    """Statistical summary of a variable in a profile"""
    profile_id: str
    variable: str
    count: int
    mean: Optional[float]
    std: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    depth_range: Dict[str, float]
    qc_summary: Dict[str, int]  # QC flag counts
    data_mode: DataMode


class ComparisonResult(BaseModel):
    """Results from comparing multiple profiles"""
    profile_ids: List[str]
    parameter: str
    comparison_matrix: Dict[str, Any]
    statistical_summary: Dict[str, float]
    data_quality_notes: List[str]


# Error Response Models
class ValidationError(BaseModel):
    """Validation error response"""
    error: str = "validation_error"
    message: str
    details: Dict[str, Any]


class DataQualityWarning(BaseModel):
    """Data quality warning"""
    warning: str = "data_quality"
    message: str
    affected_data: Dict[str, Any]
    recommendation: str


# Unified response wrapper
class ToolResponse(BaseModel):
    """Unified response wrapper for all MCP tools"""
    success: bool
    data: Optional[Any] = None
    warnings: List[DataQualityWarning] = []
    errors: List[ValidationError] = []
    metadata: Dict[str, Any] = {}
    execution_time_ms: Optional[float] = None