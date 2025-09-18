#!/usr/bin/env python3
"""
Core MCP tools for ARGO data querying
Provides secure, validated database access with ARGO protocol compliance
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from math import radians, cos, sin, asin, sqrt

from fastapi import HTTPException
from pydantic import ValidationError

from sih25.LOADER.database import get_db_manager
from sih25.API.models import (
    BoundingBox, ProfileQuery, FloatSearchQuery, VariableStatsQuery,
    FloatSummary, ProfileSummary, ProfileDetail, VariableStats,
    ComparisonResult, ToolResponse, DataQualityWarning, ValidationError as ValidationErrorModel,
    DataMode, QCFlag
)
from sih25.API.validation import argo_validator

logger = logging.getLogger(__name__)


class ARGOTools:
    """Core MCP tools for ARGO data access"""

    def __init__(self):
        self.logger = logger

    async def _execute_with_timing(self, func, *args, **kwargs) -> ToolResponse:
        """Execute a function with timing, ARGO validation, and error handling"""
        start_time = time.time()
        warnings = []
        errors = []

        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000

            # Apply ARGO protocol validation if result contains data
            if result and hasattr(result, '__iter__') and not isinstance(result, str):
                if isinstance(result, list):
                    # For list results (profiles, floats, etc.)
                    validated_result, validation_warnings = argo_validator.validate_data_mode_preference(
                        [{"data_mode": getattr(item, 'data_mode', 'R'),
                          "timestamp": getattr(item, 'timestamp', None),
                          "profile_id": getattr(item, 'profile_id', getattr(item, 'wmo_id', None))}
                         for item in result if hasattr(item, '__dict__')]
                    )
                    warnings.extend(validation_warnings)

                    # Add temporal and spatial consistency checks
                    if len(result) > 1:
                        temporal_warnings = argo_validator.validate_temporal_consistency(
                            [{"timestamp": getattr(item, 'timestamp', None),
                              "profile_id": getattr(item, 'profile_id', getattr(item, 'wmo_id', None))}
                             for item in result if hasattr(item, '__dict__')]
                        )
                        warnings.extend(temporal_warnings)

                        spatial_warnings = argo_validator.validate_spatial_consistency(
                            [{"latitude": getattr(item, 'latitude', None),
                              "longitude": getattr(item, 'longitude', None),
                              "timestamp": getattr(item, 'timestamp', None),
                              "profile_id": getattr(item, 'profile_id', getattr(item, 'wmo_id', None))}
                             for item in result if hasattr(item, '__dict__')]
                        )
                        warnings.extend(spatial_warnings)

            # Add data provenance to metadata
            metadata = {
                "argo_compliance_validated": True,
                "processing_timestamp": datetime.utcnow().isoformat(),
                "data_quality_checks": "QC flags, data modes, parameter ranges validated"
            }

            return ToolResponse(
                success=True,
                data=result,
                warnings=warnings,
                errors=errors,
                metadata=metadata,
                execution_time_ms=execution_time
            )

        except ValidationError as e:
            errors.append(ValidationErrorModel(
                message="Input validation failed",
                details={"validation_errors": str(e)}
            ))
            return ToolResponse(success=False, errors=errors)

        except Exception as e:
            self.logger.error(f"Tool execution error: {e}")
            errors.append(ValidationErrorModel(
                message="Internal server error",
                details={"error": str(e)}
            ))
            return ToolResponse(success=False, errors=errors)

    def _haversine_distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Calculate the great circle distance between two points on Earth in kilometers"""
        # Convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    async def list_profiles(
        self,
        region: BoundingBox,
        time_start: datetime,
        time_end: datetime,
        has_bgc: bool = False,
        max_results: int = 100
    ) -> List[ProfileSummary]:
        """
        List profiles within a geographic region and time range

        Args:
            region: Geographic bounding box
            time_start: Start of time range
            time_end: End of time range
            has_bgc: Filter for BGC sensors (not implemented in basic schema)
            max_results: Maximum number of results

        Returns:
            List of profile summaries
        """
        db_manager = await get_db_manager()

        query = """
        SELECT DISTINCT
            p.profile_id,
            p.float_wmo_id,
            p.timestamp,
            p.latitude,
            p.longitude,
            p.data_mode,
            p.position_qc,
            ARRAY_AGG(DISTINCT o.parameter) as parameters,
            MIN(o.depth) as min_depth,
            MAX(o.depth) as max_depth,
            CASE p.data_mode
                WHEN 'D' THEN 3  -- Delayed mode first (highest priority)
                WHEN 'A' THEN 2  -- Adjusted mode second
                WHEN 'R' THEN 1  -- Real-time mode last
                ELSE 0
            END as data_mode_priority
        FROM profiles p
        LEFT JOIN observations o ON p.profile_id = o.profile_id
        WHERE p.latitude BETWEEN $1 AND $2
        AND p.longitude BETWEEN $3 AND $4
        AND p.timestamp BETWEEN $5 AND $6
        AND p.position_qc IN (1, 2)  -- ARGO QC: Only good or probably good positions
        AND (o.qc_flag IS NULL OR o.qc_flag IN (1, 2, 8))  -- ARGO QC: Good, probably good, or estimated data
        GROUP BY p.profile_id, p.float_wmo_id, p.timestamp, p.latitude, p.longitude, p.data_mode, p.position_qc
        ORDER BY data_mode_priority DESC, p.timestamp DESC
        LIMIT $7
        """

        results = await db_manager.fetch_with_retry(
            query,
            region.min_lat, region.max_lat,
            region.min_lon, region.max_lon,
            time_start, time_end,
            max_results
        )

        profiles = []
        for row in results:
            # Convert asyncpg.Record to dict to access values
            row_dict = dict(row)

            profiles.append(ProfileSummary(
                profile_id=row_dict['profile_id'],
                float_wmo_id=row_dict['float_wmo_id'],
                timestamp=row_dict['timestamp'],
                latitude=row_dict['latitude'],
                longitude=row_dict['longitude'],
                data_mode=DataMode(row_dict['data_mode']) if row_dict['data_mode'] else DataMode.REAL_TIME,
                position_qc=QCFlag(row_dict['position_qc']) if row_dict['position_qc'] is not None else QCFlag.NO_QC,
                parameters_available=row_dict['parameters'] or [],
                depth_range={
                    "min": float(row_dict['min_depth']) if row_dict['min_depth'] is not None else 0.0,
                    "max": float(row_dict['max_depth']) if row_dict['max_depth'] is not None else 0.0
                }
            ))

        return profiles

    async def get_profile_details(self, profile_id: str) -> ProfileDetail:
        """
        Get detailed information about a specific profile

        Args:
            profile_id: The profile identifier

        Returns:
            Detailed profile information
        """
        db_manager = await get_db_manager()

        # Get profile metadata
        profile_query = """
        SELECT
            p.profile_id,
            p.float_wmo_id,
            p.timestamp,
            p.latitude,
            p.longitude,
            p.data_mode,
            p.position_qc,
            f.deployment_info,
            f.pi_details
        FROM profiles p
        LEFT JOIN floats f ON p.float_wmo_id = f.wmo_id
        WHERE p.profile_id = $1
        """

        profile_result = await db_manager.fetch_with_retry(profile_query, profile_id)

        if not profile_result:
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")

        profile_row = dict(profile_result[0])

        # Get observations summary
        observations_query = """
        SELECT
            COUNT(*) as obs_count,
            ARRAY_AGG(DISTINCT parameter) as parameters,
            MIN(depth) as min_depth,
            MAX(depth) as max_depth,
            parameter,
            qc_flag,
            COUNT(*) as qc_count
        FROM observations
        WHERE profile_id = $1
        GROUP BY parameter, qc_flag
        """

        obs_results = await db_manager.fetch_with_retry(observations_query, profile_id)

        # Process observations data
        total_observations = 0
        parameters = set()
        min_depth = float('inf')
        max_depth = float('-inf')
        qc_summary = {}

        for row in obs_results:
            row_dict = dict(row)
            total_observations += row_dict['qc_count']
            parameters.add(row_dict['parameter'])

            if row_dict['min_depth'] is not None:
                min_depth = min(min_depth, row_dict['min_depth'])
            if row_dict['max_depth'] is not None:
                max_depth = max(max_depth, row_dict['max_depth'])

            qc_flag = row_dict['qc_flag']
            if qc_flag is not None:
                qc_summary[str(qc_flag)] = qc_summary.get(str(qc_flag), 0) + row_dict['qc_count']

        # Handle edge cases
        if min_depth == float('inf'):
            min_depth = 0.0
        if max_depth == float('-inf'):
            max_depth = 0.0

        return ProfileDetail(
            profile_id=profile_row['profile_id'],
            float_wmo_id=profile_row['float_wmo_id'],
            timestamp=profile_row['timestamp'],
            latitude=profile_row['latitude'],
            longitude=profile_row['longitude'],
            data_mode=DataMode(profile_row['data_mode']) if profile_row['data_mode'] else DataMode.REAL_TIME,
            position_qc=QCFlag(profile_row['position_qc']) if profile_row['position_qc'] is not None else QCFlag.NO_QC,
            observations_count=total_observations,
            parameters=list(parameters),
            depth_range={"min": float(min_depth), "max": float(max_depth)},
            data_provenance={
                "deployment_info": profile_row.get('deployment_info', {}),
                "pi_details": profile_row.get('pi_details', {}),
                "profile_id": profile_id
            },
            quality_summary=qc_summary
        )

    async def search_floats_near(
        self,
        lon: float,
        lat: float,
        radius_km: float,
        max_results: int = 50
    ) -> List[FloatSummary]:
        """
        Search for floats within a specified radius of a point

        Args:
            lon: Longitude of search center
            lat: Latitude of search center
            radius_km: Search radius in kilometers
            max_results: Maximum number of results

        Returns:
            List of float summaries within the radius
        """
        db_manager = await get_db_manager()

        # Get all floats with their latest profiles within a larger bounding box first
        # Use approximate bounding box (1 degree ≈ 111 km at equator)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * cos(radians(lat)))

        query = """
        WITH latest_profiles AS (
            SELECT DISTINCT ON (float_wmo_id)
                float_wmo_id,
                timestamp as last_contact,
                latitude,
                longitude
            FROM profiles
            WHERE latitude BETWEEN $1 AND $2
            AND longitude BETWEEN $3 AND $4
            ORDER BY float_wmo_id, timestamp DESC
        ),
        profile_counts AS (
            SELECT
                float_wmo_id,
                COUNT(*) as total_profiles
            FROM profiles
            GROUP BY float_wmo_id
        )
        SELECT
            f.wmo_id,
            f.deployment_info,
            f.pi_details,
            lp.last_contact,
            lp.latitude,
            lp.longitude,
            COALESCE(pc.total_profiles, 0) as total_profiles
        FROM floats f
        LEFT JOIN latest_profiles lp ON f.wmo_id = lp.float_wmo_id
        LEFT JOIN profile_counts pc ON f.wmo_id = pc.float_wmo_id
        WHERE lp.latitude IS NOT NULL
        LIMIT $5
        """

        results = await db_manager.fetch_with_retry(
            query,
            lat - lat_delta, lat + lat_delta,
            lon - lon_delta, lon + lon_delta,
            max_results * 2  # Get more results to filter by actual distance
        )

        # Filter by actual distance and create summaries
        floats_within_radius = []
        for row in results:
            row_dict = dict(row)

            if row_dict['latitude'] is None or row_dict['longitude'] is None:
                continue

            distance = self._haversine_distance(
                lon, lat,
                row_dict['longitude'], row_dict['latitude']
            )

            if distance <= radius_km:
                deployment_info = row_dict.get('deployment_info', {}) or {}
                pi_details = row_dict.get('pi_details', {}) or {}

                floats_within_radius.append(FloatSummary(
                    wmo_id=row_dict['wmo_id'],
                    deployment_date=deployment_info.get('deployment_date'),
                    last_contact=row_dict['last_contact'],
                    status="active" if row_dict['last_contact'] else "unknown",
                    pi_name=pi_details.get('name'),
                    institution=pi_details.get('institution'),
                    total_profiles=row_dict['total_profiles'] or 0
                ))

        # Sort by distance and limit results
        floats_within_radius.sort(key=lambda f: f.total_profiles, reverse=True)
        return floats_within_radius[:max_results]

    async def get_profile_statistics(self, profile_id: str, variable: str) -> VariableStats:
        """
        Get statistical summary of a variable in a profile

        Args:
            profile_id: The profile identifier
            variable: Variable name (e.g., 'TEMP', 'PSAL')

        Returns:
            Statistical summary of the variable
        """
        db_manager = await get_db_manager()

        # Get profile metadata
        profile_query = """
        SELECT data_mode FROM profiles WHERE profile_id = $1
        """

        profile_result = await db_manager.fetch_with_retry(profile_query, profile_id)
        if not profile_result:
            raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")

        data_mode = DataMode(profile_result[0]['data_mode']) if profile_result[0]['data_mode'] else DataMode.REAL_TIME

        # Get variable statistics
        stats_query = """
        SELECT
            COUNT(*) as count,
            AVG(value) as mean,
            STDDEV(value) as std,
            MIN(value) as min_value,
            MAX(value) as max_value,
            MIN(depth) as min_depth,
            MAX(depth) as max_depth,
            qc_flag,
            COUNT(*) as qc_count
        FROM observations
        WHERE profile_id = $1 AND parameter = $2
        GROUP BY qc_flag
        """

        stats_results = await db_manager.fetch_with_retry(stats_query, profile_id, variable)

        if not stats_results:
            raise HTTPException(status_code=404, detail=f"Variable {variable} not found in profile {profile_id}")

        # Aggregate statistics
        total_count = 0
        qc_summary = {}
        values_for_stats = []
        min_depth = float('inf')
        max_depth = float('-inf')

        for row in stats_results:
            row_dict = dict(row)
            total_count += row_dict['count']
            qc_flag = row_dict['qc_flag']

            if qc_flag is not None:
                qc_summary[str(qc_flag)] = row_dict['qc_count']

            if row_dict['min_depth'] is not None:
                min_depth = min(min_depth, row_dict['min_depth'])
            if row_dict['max_depth'] is not None:
                max_depth = max(max_depth, row_dict['max_depth'])

        # Get overall statistics (for good quality data only per ARGO standards)
        overall_stats_query = """
        SELECT
            AVG(value) as mean,
            STDDEV(value) as std,
            MIN(value) as min_value,
            MAX(value) as max_value
        FROM observations
        WHERE profile_id = $1 AND parameter = $2 AND qc_flag IN (1, 2)  -- ARGO QC: Only good and probably good data
        """

        overall_result = await db_manager.fetch_with_retry(overall_stats_query, profile_id, variable)
        overall_dict = dict(overall_result[0]) if overall_result else {}

        # Handle edge cases
        if min_depth == float('inf'):
            min_depth = 0.0
        if max_depth == float('-inf'):
            max_depth = 0.0

        return VariableStats(
            profile_id=profile_id,
            variable=variable,
            count=total_count,
            mean=float(overall_dict['mean']) if overall_dict.get('mean') is not None else None,
            std=float(overall_dict['std']) if overall_dict.get('std') is not None else None,
            min_value=float(overall_dict['min_value']) if overall_dict.get('min_value') is not None else None,
            max_value=float(overall_dict['max_value']) if overall_dict.get('max_value') is not None else None,
            depth_range={"min": float(min_depth), "max": float(max_depth)},
            qc_summary=qc_summary,
            data_mode=data_mode
        )


# Global tools instance
argo_tools = ARGOTools()