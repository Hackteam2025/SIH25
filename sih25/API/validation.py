#!/usr/bin/env python3
"""
ARGO Protocol Validation Module
Enforces scientific standards and data quality protocols for ARGO oceanographic data
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from sih25.API.models import DataMode, QCFlag, DataQualityWarning

logger = logging.getLogger(__name__)


class ARGOProtocolValidator:
    """
    Validates and enforces ARGO data quality protocols

    ARGO Quality Control Standards:
    - QC Flag 1 (Good): High quality data
    - QC Flag 2 (Probably good): Acceptable quality data
    - QC Flag 3 (Probably bad): Questionable data
    - QC Flag 4 (Bad): Poor quality data - should not be used

    Data Mode Preference:
    - D (Delayed): Highest quality, fully validated
    - A (Adjusted): Real-time data with adjustments
    - R (Real-time): Immediate data, may have issues
    """

    # ARGO QC flag priorities (higher number = better quality)
    QC_PRIORITY = {
        QCFlag.GOOD: 10,
        QCFlag.PROBABLY_GOOD: 8,
        QCFlag.ESTIMATED: 6,
        QCFlag.CHANGED: 5,
        QCFlag.NO_QC: 3,
        QCFlag.PROBABLY_BAD: 2,
        QCFlag.NOT_USED: 1,
        QCFlag.NOT_USED_2: 1,
        QCFlag.BAD: 0,
        QCFlag.MISSING: 0
    }

    # Data mode priorities (higher number = better quality)
    DATA_MODE_PRIORITY = {
        DataMode.DELAYED: 10,
        DataMode.ADJUSTED: 8,
        DataMode.REAL_TIME: 5
    }

    # Scientific parameter ranges for validation
    PARAMETER_RANGES = {
        'TEMP': {'min': -2.5, 'max': 40.0, 'units': 'degrees Celsius'},
        'PSAL': {'min': 0.0, 'max': 42.0, 'units': 'PSU'},
        'PRES': {'min': 0.0, 'max': 11000.0, 'units': 'decibar'},
        'DOXY': {'min': 0.0, 'max': 500.0, 'units': 'micromol/kg'},
        'NITRATE': {'min': 0.0, 'max': 50.0, 'units': 'micromol/kg'},
        'CHLA': {'min': 0.0, 'max': 50.0, 'units': 'mg/m3'},
        'BBP700': {'min': 0.0, 'max': 0.01, 'units': 'm-1'},
        'PH_IN_SITU_TOTAL': {'min': 7.0, 'max': 8.5, 'units': 'pH units'}
    }

    def __init__(self):
        self.logger = logger

    def validate_qc_flags(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[DataQualityWarning]]:
        """
        Filter and validate data based on QC flags according to ARGO standards

        Args:
            data: List of data records with QC information

        Returns:
            Tuple of (filtered_data, warnings)
        """
        warnings = []
        good_data = []
        bad_data_count = 0
        questionable_data_count = 0

        for record in data:
            qc_flag = record.get('qc_flag')

            if qc_flag is None:
                # No QC flag - include with warning
                warnings.append(DataQualityWarning(
                    message="Data without QC flags detected",
                    affected_data={"record_id": record.get('id', 'unknown')},
                    recommendation="Use caution - QC status unknown"
                ))
                good_data.append(record)
                continue

            qc_flag_enum = QCFlag(qc_flag) if isinstance(qc_flag, int) else qc_flag

            if qc_flag_enum == QCFlag.BAD:
                bad_data_count += 1
                # Skip bad data entirely
                continue

            elif qc_flag_enum == QCFlag.PROBABLY_BAD:
                questionable_data_count += 1
                # Include but warn about questionable data
                warnings.append(DataQualityWarning(
                    message="Questionable quality data included",
                    affected_data={"qc_flag": qc_flag, "record_id": record.get('id', 'unknown')},
                    recommendation="Consider filtering out if high precision required"
                ))

            good_data.append(record)

        # Add summary warnings
        if bad_data_count > 0:
            warnings.append(DataQualityWarning(
                message=f"Filtered out {bad_data_count} records with bad QC flags",
                affected_data={"filtered_count": bad_data_count},
                recommendation="Bad quality data excluded per ARGO standards"
            ))

        if questionable_data_count > 0:
            warnings.append(DataQualityWarning(
                message=f"Dataset includes {questionable_data_count} records with questionable QC",
                affected_data={"questionable_count": questionable_data_count},
                recommendation="Review data quality requirements for your use case"
            ))

        return good_data, warnings

    def validate_data_mode_preference(self, profiles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[DataQualityWarning]]:
        """
        Apply ARGO data mode preference (Delayed > Adjusted > Real-time)

        Args:
            profiles: List of profile records

        Returns:
            Tuple of (sorted_profiles, warnings)
        """
        warnings = []

        # Sort by data mode priority and timestamp
        def sort_key(profile):
            data_mode = profile.get('data_mode', DataMode.REAL_TIME)
            if isinstance(data_mode, str):
                data_mode = DataMode(data_mode)

            # Priority: higher data mode priority, then newer timestamp
            timestamp = profile.get('timestamp', datetime.min)
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            return (
                self.DATA_MODE_PRIORITY.get(data_mode, 0),
                timestamp
            )

        sorted_profiles = sorted(profiles, key=sort_key, reverse=True)

        # Check data mode distribution
        mode_counts = {}
        for profile in profiles:
            data_mode = profile.get('data_mode', DataMode.REAL_TIME)
            if isinstance(data_mode, str):
                data_mode = DataMode(data_mode)
            mode_counts[data_mode.value] = mode_counts.get(data_mode.value, 0) + 1

        # Generate warnings based on data mode distribution
        if mode_counts.get('R', 0) > mode_counts.get('D', 0):
            warnings.append(DataQualityWarning(
                message="Dataset contains more real-time than delayed-mode data",
                affected_data={"mode_distribution": mode_counts},
                recommendation="Delayed-mode data preferred for scientific analysis"
            ))

        if 'D' not in mode_counts:
            warnings.append(DataQualityWarning(
                message="No delayed-mode data available",
                affected_data={"available_modes": list(mode_counts.keys())},
                recommendation="Results may have lower accuracy without delayed-mode processing"
            ))

        return sorted_profiles, warnings

    def validate_parameter_ranges(self, observations: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[DataQualityWarning]]:
        """
        Validate oceanographic parameter values against expected ranges

        Args:
            observations: List of observation records

        Returns:
            Tuple of (validated_observations, warnings)
        """
        warnings = []
        valid_observations = []
        outlier_count = 0

        for obs in observations:
            parameter = obs.get('parameter')
            value = obs.get('value')

            if parameter not in self.PARAMETER_RANGES or value is None:
                valid_observations.append(obs)
                continue

            param_range = self.PARAMETER_RANGES[parameter]

            if not (param_range['min'] <= value <= param_range['max']):
                outlier_count += 1
                warnings.append(DataQualityWarning(
                    message=f"Parameter {parameter} value outside expected range",
                    affected_data={
                        "parameter": parameter,
                        "value": value,
                        "expected_range": f"{param_range['min']}-{param_range['max']} {param_range['units']}",
                        "observation_id": obs.get('id', 'unknown')
                    },
                    recommendation="Verify measurement accuracy or check for instrument errors"
                ))

            valid_observations.append(obs)

        if outlier_count > 0:
            warnings.append(DataQualityWarning(
                message=f"Found {outlier_count} observations with values outside expected ranges",
                affected_data={"outlier_count": outlier_count},
                recommendation="Review outliers for potential data quality issues"
            ))

        return valid_observations, warnings

    def validate_temporal_consistency(self, profiles: List[Dict[str, Any]]) -> List[DataQualityWarning]:
        """
        Check for temporal consistency issues in profile data

        Args:
            profiles: List of profile records

        Returns:
            List of warnings about temporal issues
        """
        warnings = []

        if len(profiles) < 2:
            return warnings

        # Sort by timestamp
        sorted_profiles = sorted(profiles, key=lambda p: p.get('timestamp', datetime.min))

        # Check for suspiciously rapid sampling
        for i in range(1, len(sorted_profiles)):
            current_time = sorted_profiles[i].get('timestamp')
            previous_time = sorted_profiles[i-1].get('timestamp')

            if current_time and previous_time:
                time_diff = current_time - previous_time

                # ARGO floats typically cycle every 10 days
                if time_diff < timedelta(hours=6):
                    warnings.append(DataQualityWarning(
                        message="Unusually rapid profile sampling detected",
                        affected_data={
                            "profile_1": sorted_profiles[i-1].get('profile_id'),
                            "profile_2": sorted_profiles[i].get('profile_id'),
                            "time_diff_hours": time_diff.total_seconds() / 3600
                        },
                        recommendation="Verify profile timestamps for potential data issues"
                    ))

        # Check for data gaps
        total_timespan = sorted_profiles[-1].get('timestamp') - sorted_profiles[0].get('timestamp')
        expected_profiles = total_timespan.days / 10  # Expected ~10-day cycle
        actual_profiles = len(profiles)

        if actual_profiles < expected_profiles * 0.5:  # Less than 50% of expected profiles
            warnings.append(DataQualityWarning(
                message="Significant data gaps detected in time series",
                affected_data={
                    "timespan_days": total_timespan.days,
                    "actual_profiles": actual_profiles,
                    "expected_profiles": int(expected_profiles)
                },
                recommendation="Consider data completeness for temporal analysis"
            ))

        return warnings

    def validate_spatial_consistency(self, profiles: List[Dict[str, Any]]) -> List[DataQualityWarning]:
        """
        Check for spatial consistency issues in profile locations

        Args:
            profiles: List of profile records with lat/lon

        Returns:
            List of warnings about spatial issues
        """
        warnings = []

        if len(profiles) < 2:
            return warnings

        # Check for impossible movements (floats drift, don't teleport)
        for i in range(1, len(profiles)):
            current = profiles[i]
            previous = profiles[i-1]

            curr_lat = current.get('latitude')
            curr_lon = current.get('longitude')
            curr_time = current.get('timestamp')

            prev_lat = previous.get('latitude')
            prev_lon = previous.get('longitude')
            prev_time = previous.get('timestamp')

            if all([curr_lat, curr_lon, curr_time, prev_lat, prev_lon, prev_time]):
                # Calculate distance using haversine formula (simplified)
                from math import radians, cos, sin, asin, sqrt

                def haversine(lon1, lat1, lon2, lat2):
                    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    r = 6371  # Earth radius in km
                    return c * r

                distance_km = haversine(prev_lon, prev_lat, curr_lon, curr_lat)
                time_diff = curr_time - prev_time

                if time_diff.total_seconds() > 0:
                    speed_kmh = distance_km / (time_diff.total_seconds() / 3600)

                    # ARGO floats typically drift at ~0.1-1 km/h
                    if speed_kmh > 5.0:  # Suspiciously fast movement
                        warnings.append(DataQualityWarning(
                            message="Unusually rapid float movement detected",
                            affected_data={
                                "profile_1": previous.get('profile_id'),
                                "profile_2": current.get('profile_id'),
                                "distance_km": round(distance_km, 2),
                                "speed_kmh": round(speed_kmh, 2)
                            },
                            recommendation="Verify position accuracy or check for data processing errors"
                        ))

        return warnings

    def add_data_provenance(self, data: Dict[str, Any], processing_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add ARGO-compliant data provenance information

        Args:
            data: Data record to enhance
            processing_info: Information about processing steps

        Returns:
            Enhanced data with provenance
        """
        provenance = {
            "argo_compliance": True,
            "qc_standards": "ARGO Data Management Team",
            "processing_timestamp": datetime.utcnow().isoformat(),
            "data_source": "SIH25 MCP Tool Server",
            "quality_control": {
                "qc_flag_filtering": "Bad data (QC=4) excluded",
                "data_mode_preference": "Delayed > Adjusted > Real-time",
                "parameter_validation": "ARGO standard ranges applied"
            },
            "processing_steps": processing_info
        }

        # Add to existing provenance or create new
        if 'data_provenance' in data:
            data['data_provenance'].update(provenance)
        else:
            data['data_provenance'] = provenance

        return data


# Global validator instance
argo_validator = ARGOProtocolValidator()