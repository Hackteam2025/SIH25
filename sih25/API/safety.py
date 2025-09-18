#!/usr/bin/env python3
"""
Query Safety and Validation Module
Implements comprehensive input validation, sanitization, and query limits
to prevent performance issues and security vulnerabilities
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from math import radians, degrees

from pydantic import ValidationError
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class QuerySafetyValidator:
    """
    Comprehensive query safety and validation system

    Features:
    - Input sanitization and validation
    - Query size and complexity limits
    - Performance protection
    - Security validation
    """

    # Query limits to prevent performance issues
    MAX_RESULTS_PER_QUERY = 1000
    MAX_TIME_RANGE_DAYS = 365 * 2  # 2 years maximum
    MAX_GEOGRAPHIC_AREA_DEGREES = 180  # Maximum bounding box size
    MAX_SEARCH_RADIUS_KM = 2000  # Maximum search radius
    MIN_SEARCH_RADIUS_KM = 0.1   # Minimum search radius

    # Performance thresholds
    MAX_QUERY_EXECUTION_TIME_SECONDS = 30
    MAX_CONCURRENT_QUERIES_PER_IP = 5

    # Parameter validation patterns
    VALID_PARAMETER_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]{1,20}$')
    VALID_PROFILE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_\-\.]{1,50}$')
    VALID_WMO_ID_PATTERN = re.compile(r'^[0-9]{5,10}$')

    # SQL injection prevention patterns
    SQL_INJECTION_PATTERNS = [
        re.compile(r"('|(\\')|(;)|(\|)|(\*)|(%)|(\-\-)|(\+)|(=))", re.IGNORECASE),
        re.compile(r"(union|select|insert|update|delete|drop|create|alter|exec|execute)", re.IGNORECASE),
        re.compile(r"(script|javascript|vbscript|onload|onerror)", re.IGNORECASE)
    ]

    def __init__(self):
        self.logger = logger

    def validate_geographic_bounds(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float
    ) -> Tuple[bool, List[str]]:
        """
        Validate geographic bounding box

        Args:
            min_lat, max_lat, min_lon, max_lon: Bounding box coordinates

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Basic coordinate validation
        if not (-90 <= min_lat <= 90):
            errors.append(f"Invalid min_lat: {min_lat}. Must be between -90 and 90")

        if not (-90 <= max_lat <= 90):
            errors.append(f"Invalid max_lat: {max_lat}. Must be between -90 and 90")

        if not (-180 <= min_lon <= 180):
            errors.append(f"Invalid min_lon: {min_lon}. Must be between -180 and 180")

        if not (-180 <= max_lon <= 180):
            errors.append(f"Invalid max_lon: {max_lon}. Must be between -180 and 180")

        # Logical validation
        if min_lat >= max_lat:
            errors.append(f"min_lat ({min_lat}) must be less than max_lat ({max_lat})")

        if min_lon >= max_lon:
            errors.append(f"min_lon ({min_lon}) must be less than max_lon ({max_lon})")

        # Area size validation
        lat_span = max_lat - min_lat
        lon_span = max_lon - min_lon

        if lat_span > self.MAX_GEOGRAPHIC_AREA_DEGREES:
            errors.append(f"Latitude span ({lat_span}°) exceeds maximum ({self.MAX_GEOGRAPHIC_AREA_DEGREES}°)")

        if lon_span > self.MAX_GEOGRAPHIC_AREA_DEGREES:
            errors.append(f"Longitude span ({lon_span}°) exceeds maximum ({self.MAX_GEOGRAPHIC_AREA_DEGREES}°)")

        # Ocean coverage validation (ARGO floats are ocean-only)
        if min_lat > 80 or max_lat > 80:
            errors.append("Search area extends too far north (>80°N) - limited ARGO coverage in Arctic")

        if min_lat < -80 or max_lat < -80:
            errors.append("Search area extends too far south (<-80°S) - limited ARGO coverage in Antarctica")

        return len(errors) == 0, errors

    def validate_time_range(
        self,
        time_start: datetime,
        time_end: datetime
    ) -> Tuple[bool, List[str]]:
        """
        Validate time range for queries

        Args:
            time_start: Start of time range
            time_end: End of time range

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        now = datetime.utcnow()

        # Basic time validation
        if time_start >= time_end:
            errors.append(f"time_start ({time_start}) must be before time_end ({time_end})")

        # Range size validation
        time_span = time_end - time_start
        if time_span.days > self.MAX_TIME_RANGE_DAYS:
            errors.append(
                f"Time range ({time_span.days} days) exceeds maximum "
                f"({self.MAX_TIME_RANGE_DAYS} days)"
            )

        # Future date validation
        if time_start > now + timedelta(days=1):
            errors.append("time_start cannot be more than 1 day in the future")

        if time_end > now + timedelta(days=1):
            errors.append("time_end cannot be more than 1 day in the future")

        # Historical limits (ARGO program started ~1999)
        argo_start = datetime(1999, 1, 1)
        if time_start < argo_start:
            errors.append(f"time_start ({time_start}) predates ARGO program start ({argo_start})")

        return len(errors) == 0, errors

    def validate_search_radius(self, radius_km: float) -> Tuple[bool, List[str]]:
        """
        Validate search radius for proximity queries

        Args:
            radius_km: Search radius in kilometers

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if radius_km < self.MIN_SEARCH_RADIUS_KM:
            errors.append(f"Search radius ({radius_km} km) below minimum ({self.MIN_SEARCH_RADIUS_KM} km)")

        if radius_km > self.MAX_SEARCH_RADIUS_KM:
            errors.append(f"Search radius ({radius_km} km) exceeds maximum ({self.MAX_SEARCH_RADIUS_KM} km)")

        return len(errors) == 0, errors

    def validate_result_limits(self, max_results: int) -> Tuple[bool, List[str]]:
        """
        Validate result count limits

        Args:
            max_results: Maximum number of results requested

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if max_results <= 0:
            errors.append("max_results must be greater than 0")

        if max_results > self.MAX_RESULTS_PER_QUERY:
            errors.append(
                f"max_results ({max_results}) exceeds maximum "
                f"({self.MAX_RESULTS_PER_QUERY})"
            )

        return len(errors) == 0, errors

    def sanitize_string_input(self, input_str: str, max_length: int = 100) -> str:
        """
        Sanitize string input to prevent injection attacks

        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            HTTPException: If input contains malicious patterns
        """
        if not isinstance(input_str, str):
            raise HTTPException(status_code=400, detail="Input must be a string")

        # Length validation
        if len(input_str) > max_length:
            raise HTTPException(
                status_code=400,
                detail=f"Input length ({len(input_str)}) exceeds maximum ({max_length})"
            )

        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if pattern.search(input_str):
                self.logger.warning(f"Potential SQL injection attempt: {input_str}")
                raise HTTPException(
                    status_code=400,
                    detail="Input contains potentially malicious content"
                )

        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';\\]', '', input_str)

        # Trim whitespace
        sanitized = sanitized.strip()

        return sanitized

    def validate_parameter_name(self, parameter: str) -> Tuple[bool, List[str]]:
        """
        Validate oceanographic parameter name

        Args:
            parameter: Parameter name (e.g., 'TEMP', 'PSAL')

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Sanitize input
        try:
            sanitized_param = self.sanitize_string_input(parameter, 30)
        except HTTPException as e:
            errors.append(f"Parameter name validation failed: {e.detail}")
            return False, errors

        # Pattern validation
        if not self.VALID_PARAMETER_PATTERN.match(sanitized_param):
            errors.append(
                f"Invalid parameter name '{sanitized_param}'. "
                "Must start with uppercase letter, contain only A-Z, 0-9, underscore"
            )

        # Known parameter validation
        known_parameters = {
            'TEMP', 'PSAL', 'PRES', 'DOXY', 'CHLA', 'BBP700', 'PH_IN_SITU_TOTAL',
            'NITRATE', 'BISULFIDE', 'TURBIDITY', 'UP_RADIANCE412', 'DOWN_IRRADIANCE412',
            'DOWN_IRRADIANCE443', 'DOWN_IRRADIANCE490', 'DOWN_IRRADIANCE555'
        }

        if sanitized_param not in known_parameters:
            # Don't reject, but warn about unknown parameter
            errors.append(
                f"Warning: '{sanitized_param}' is not a standard ARGO parameter. "
                "Results may be empty."
            )

        return len(errors) == 0, errors

    def validate_profile_id(self, profile_id: str) -> Tuple[bool, List[str]]:
        """
        Validate profile ID format

        Args:
            profile_id: Profile identifier

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Sanitize input
        try:
            sanitized_id = self.sanitize_string_input(profile_id, 50)
        except HTTPException as e:
            errors.append(f"Profile ID validation failed: {e.detail}")
            return False, errors

        # Pattern validation
        if not self.VALID_PROFILE_ID_PATTERN.match(sanitized_id):
            errors.append(
                f"Invalid profile ID '{sanitized_id}'. "
                "Must contain only letters, numbers, hyphens, underscores, and periods"
            )

        return len(errors) == 0, errors

    def validate_wmo_id(self, wmo_id: str) -> Tuple[bool, List[str]]:
        """
        Validate WMO (World Meteorological Organization) ID

        Args:
            wmo_id: WMO identifier

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Sanitize input
        try:
            sanitized_id = self.sanitize_string_input(wmo_id, 15)
        except HTTPException as e:
            errors.append(f"WMO ID validation failed: {e.detail}")
            return False, errors

        # Pattern validation
        if not self.VALID_WMO_ID_PATTERN.match(sanitized_id):
            errors.append(
                f"Invalid WMO ID '{sanitized_id}'. "
                "Must be 5-10 digits"
            )

        return len(errors) == 0, errors

    def estimate_query_complexity(
        self,
        geographic_area: float,
        time_range_days: int,
        max_results: int
    ) -> Dict[str, Any]:
        """
        Estimate query complexity and potential performance impact

        Args:
            geographic_area: Area of bounding box in square degrees
            time_range_days: Time range in days
            max_results: Maximum results requested

        Returns:
            Dictionary with complexity metrics
        """
        # Simple complexity scoring
        area_score = min(geographic_area / 100, 10)  # Normalize to 0-10
        time_score = min(time_range_days / 365, 10)  # Normalize to 0-10
        result_score = min(max_results / 100, 10)    # Normalize to 0-10

        complexity_score = (area_score + time_score + result_score) / 3

        # Estimated execution time (very rough)
        estimated_seconds = complexity_score * 2

        return {
            "complexity_score": round(complexity_score, 2),
            "estimated_execution_seconds": round(estimated_seconds, 1),
            "performance_warning": complexity_score > 7.0,
            "components": {
                "geographic_complexity": round(area_score, 2),
                "temporal_complexity": round(time_score, 2),
                "result_set_complexity": round(result_score, 2)
            }
        }

    def validate_query_safety(
        self,
        query_type: str,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Comprehensive query safety validation

        Args:
            query_type: Type of query ('list_profiles', 'search_floats', etc.)
            parameters: Query parameters

        Returns:
            Tuple of (is_valid, errors, metadata)
        """
        errors = []
        metadata = {}

        try:
            if query_type == "list_profiles":
                # Validate geographic bounds
                valid_geo, geo_errors = self.validate_geographic_bounds(
                    parameters['min_lat'], parameters['max_lat'],
                    parameters['min_lon'], parameters['max_lon']
                )
                errors.extend(geo_errors)

                # Validate time range
                valid_time, time_errors = self.validate_time_range(
                    parameters['time_start'], parameters['time_end']
                )
                errors.extend(time_errors)

                # Validate result limits
                valid_results, result_errors = self.validate_result_limits(
                    parameters.get('max_results', 100)
                )
                errors.extend(result_errors)

                # Calculate complexity
                if valid_geo and valid_time:
                    area = (parameters['max_lat'] - parameters['min_lat']) * \
                           (parameters['max_lon'] - parameters['min_lon'])
                    time_range = (parameters['time_end'] - parameters['time_start']).days

                    complexity = self.estimate_query_complexity(
                        area, time_range, parameters.get('max_results', 100)
                    )
                    metadata['query_complexity'] = complexity

            elif query_type == "search_floats_near":
                # Validate coordinates
                lat = parameters.get('lat')
                lon = parameters.get('lon')

                if not (-90 <= lat <= 90):
                    errors.append(f"Invalid latitude: {lat}")

                if not (-180 <= lon <= 180):
                    errors.append(f"Invalid longitude: {lon}")

                # Validate radius
                valid_radius, radius_errors = self.validate_search_radius(
                    parameters.get('radius_km', 0)
                )
                errors.extend(radius_errors)

                # Validate result limits
                valid_results, result_errors = self.validate_result_limits(
                    parameters.get('max_results', 50)
                )
                errors.extend(result_errors)

            elif query_type == "get_profile_details":
                # Validate profile ID
                valid_id, id_errors = self.validate_profile_id(
                    parameters.get('profile_id', '')
                )
                errors.extend(id_errors)

            elif query_type == "get_profile_statistics":
                # Validate profile ID
                valid_id, id_errors = self.validate_profile_id(
                    parameters.get('profile_id', '')
                )
                errors.extend(id_errors)

                # Validate parameter name
                valid_param, param_errors = self.validate_parameter_name(
                    parameters.get('variable', '')
                )
                errors.extend(param_errors)

            # Add general metadata
            metadata.update({
                "validation_timestamp": datetime.utcnow().isoformat(),
                "query_type": query_type,
                "safety_checks_passed": len(errors) == 0
            })

        except Exception as e:
            self.logger.error(f"Query validation error: {e}")
            errors.append(f"Validation system error: {str(e)}")

        return len(errors) == 0, errors, metadata


# Global validator instance
query_safety = QuerySafetyValidator()