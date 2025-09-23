"""
Scientific Context for AGNO Agent

Provides oceanographic domain knowledge, data interpretation capabilities,
and scientific accuracy validation for ARGO data queries.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ScientificContext:
    """
    Provides scientific domain knowledge for oceanographic data interpretation.

    Includes:
    - ARGO protocol understanding
    - Parameter interpretation and units
    - Quality control guidance
    - Spatial and temporal context
    """

    def __init__(self):
        """Initialize scientific context with oceanographic knowledge."""
        self.logger = logger
        self._load_argo_parameters()
        self._load_quality_control_info()
        self._load_spatial_contexts()

    def _load_argo_parameters(self):
        """Load ARGO parameter definitions and metadata."""
        self.argo_parameters = {
            "TEMP": {
                "name": "Temperature",
                "units": "°C",
                "description": "In-situ seawater temperature",
                "typical_range": (-2.0, 35.0),
                "quality_indicators": {
                    "very_cold": -1.8,
                    "very_warm": 32.0,
                    "surface_max": 30.0,
                    "deep_typical": (2.0, 4.0)
                },
                "scientific_significance": "Primary indicator of ocean thermal structure and circulation patterns"
            },
            "PSAL": {
                "name": "Practical Salinity",
                "units": "PSU",
                "description": "Salinity calculated from conductivity measurements",
                "typical_range": (30.0, 37.0),
                "quality_indicators": {
                    "very_fresh": 32.0,
                    "very_salty": 38.0,
                    "surface_typical": (34.0, 36.0),
                    "deep_typical": (34.6, 34.8)
                },
                "scientific_significance": "Key tracer for water masses and ocean circulation"
            },
            "PRES": {
                "name": "Pressure",
                "units": "dbar",
                "description": "Water pressure, approximately equal to depth in meters",
                "typical_range": (0.0, 2000.0),
                "quality_indicators": {
                    "surface_max": 10.0,
                    "deep_ocean": 2000.0,
                    "abyssal": 4000.0
                },
                "scientific_significance": "Determines depth level for all other measurements"
            },
            "DOXY": {
                "name": "Dissolved Oxygen",
                "units": "μmol/kg",
                "description": "Concentration of dissolved oxygen in seawater",
                "typical_range": (0.0, 400.0),
                "quality_indicators": {
                    "hypoxic": 60.0,
                    "well_oxygenated": 200.0,
                    "supersaturated": 300.0
                },
                "scientific_significance": "Critical for marine ecosystem health and ocean ventilation"
            },
            "CHLA": {
                "name": "Chlorophyll-a",
                "units": "mg/m³",
                "description": "Chlorophyll-a concentration, proxy for phytoplankton biomass",
                "typical_range": (0.0, 10.0),
                "quality_indicators": {
                    "oligotrophic": 0.1,
                    "mesotrophic": 1.0,
                    "eutrophic": 5.0
                },
                "scientific_significance": "Primary productivity indicator and base of marine food chain"
            }
        }

    def _load_quality_control_info(self):
        """Load ARGO quality control flag meanings."""
        self.qc_flags = {
            0: {
                "meaning": "No QC performed",
                "reliability": "unknown",
                "recommendation": "Use with caution, quality unknown"
            },
            1: {
                "meaning": "Good data",
                "reliability": "high",
                "recommendation": "Suitable for all scientific applications"
            },
            2: {
                "meaning": "Probably good data",
                "reliability": "good",
                "recommendation": "Acceptable for most applications"
            },
            3: {
                "meaning": "Bad data that are potentially correctable",
                "reliability": "questionable",
                "recommendation": "Use only if corrected, check documentation"
            },
            4: {
                "meaning": "Bad data",
                "reliability": "bad",
                "recommendation": "Do not use for scientific analysis"
            },
            5: {
                "meaning": "Value changed",
                "reliability": "modified",
                "recommendation": "Check change documentation before use"
            },
            8: {
                "meaning": "Estimated value",
                "reliability": "estimated",
                "recommendation": "Use with understanding of estimation method"
            },
            9: {
                "meaning": "Missing value",
                "reliability": "missing",
                "recommendation": "Value not available"
            }
        }

    def _load_spatial_contexts(self):
        """Load spatial context information for ocean regions."""
        self.ocean_regions = {
            "equatorial": {
                "lat_range": (-5, 5),
                "characteristics": "High temperature, low salinity variation, strong currents",
                "significance": "Major heat transport region, El Niño/La Niña effects"
            },
            "tropical": {
                "lat_range": (-23.5, 23.5),
                "characteristics": "Warm surface waters, strong stratification",
                "significance": "High primary productivity, tropical cyclone formation region"
            },
            "subtropical": {
                "lat_range": [(-40, -23.5), (23.5, 40)],
                "characteristics": "Moderate temperatures, high salinity surface waters",
                "significance": "Subtropical gyres, oligotrophic conditions"
            },
            "subpolar": {
                "lat_range": [(-60, -40), (40, 60)],
                "characteristics": "Cold surface waters, deep mixing",
                "significance": "Deep water formation, high nutrient concentrations"
            },
            "polar": {
                "lat_range": [(-90, -60), (60, 90)],
                "characteristics": "Very cold waters, seasonal ice cover",
                "significance": "Deep and bottom water formation, unique ecosystems"
            }
        }

    def interpret_query(self, user_message: str) -> Dict[str, Any]:
        """
        Interpret a user's natural language query for scientific context.

        Args:
            user_message: User's natural language query

        Returns:
            Dictionary with query interpretation and scientific context
        """
        interpretation = {
            "parameters_of_interest": [],
            "spatial_context": {},
            "temporal_context": {},
            "analysis_type": "unknown",
            "scientific_significance": [],
            "quality_requirements": "good",
            "suggested_tools": []
        }

        message_lower = user_message.lower()

        # Extract parameters
        for param_code, param_info in self.argo_parameters.items():
            if any(term in message_lower for term in [
                param_info["name"].lower(),
                param_code.lower(),
                *self._get_parameter_synonyms(param_code)
            ]):
                interpretation["parameters_of_interest"].append({
                    "code": param_code,
                    "name": param_info["name"],
                    "significance": param_info["scientific_significance"]
                })

        # Extract spatial context
        interpretation["spatial_context"] = self._extract_spatial_context(message_lower)

        # Extract temporal context
        interpretation["temporal_context"] = self._extract_temporal_context(message_lower)

        # Determine analysis type
        interpretation["analysis_type"] = self._determine_analysis_type(message_lower)

        # Suggest appropriate tools
        interpretation["suggested_tools"] = self._suggest_tools(interpretation)

        # Add scientific significance
        interpretation["scientific_significance"] = self._determine_scientific_significance(interpretation)

        return interpretation

    def validate_data_scientifically(self, data: Any, parameter: str) -> Dict[str, Any]:
        """
        Validate data against scientific expectations.

        Args:
            data: Data to validate
            parameter: Parameter code (e.g., 'TEMP', 'PSAL')

        Returns:
            Validation results with warnings and recommendations
        """
        validation = {
            "is_scientifically_reasonable": True,
            "warnings": [],
            "recommendations": [],
            "context": {}
        }

        if parameter not in self.argo_parameters:
            validation["warnings"].append({
                "type": "unknown_parameter",
                "message": f"Parameter {parameter} not in standard ARGO parameter list",
                "severity": "medium"
            })
            return validation

        param_info = self.argo_parameters[parameter]

        # Validate against typical ranges
        if hasattr(data, '__iter__') and not isinstance(data, str):
            # For data collections
            values = [getattr(item, parameter.lower(), None) for item in data if hasattr(item, parameter.lower())]
            values = [v for v in values if v is not None]

            if values:
                min_val, max_val = min(values), max(values)
                typical_min, typical_max = param_info["typical_range"]

                if min_val < typical_min or max_val > typical_max:
                    validation["warnings"].append({
                        "type": "value_outside_typical_range",
                        "message": f"{parameter} values ({min_val:.2f} to {max_val:.2f}) outside typical range ({typical_min} to {typical_max})",
                        "severity": "medium"
                    })

        # Add context about parameter
        validation["context"] = {
            "parameter_description": param_info["description"],
            "scientific_significance": param_info["scientific_significance"],
            "typical_range": param_info["typical_range"],
            "units": param_info["units"]
        }

        return validation

    def generate_scientific_explanation(self, data: Any, query_context: Dict[str, Any]) -> str:
        """
        Generate scientific explanation of data in context.

        Args:
            data: Data to explain
            query_context: Context from query interpretation

        Returns:
            Scientific explanation text
        """
        explanation_parts = []

        # Data overview
        if hasattr(data, '__len__'):
            count = len(data) if data else 0
            explanation_parts.append(f"Found {count} records matching your query.")
        else:
            explanation_parts.append("Retrieved detailed information for your query.")

        # Parameter-specific insights
        for param in query_context.get("parameters_of_interest", []):
            param_code = param["code"]
            if param_code in self.argo_parameters:
                param_info = self.argo_parameters[param_code]
                explanation_parts.append(
                    f"{param_info['name']} ({param_info['units']}) is {param_info['scientific_significance'].lower()}."
                )

        # Spatial context
        spatial = query_context.get("spatial_context", {})
        if spatial.get("region"):
            region_info = self.ocean_regions.get(spatial["region"])
            if region_info:
                explanation_parts.append(
                    f"This {spatial['region']} region is characterized by {region_info['characteristics'].lower()}."
                )

        # Quality control context
        explanation_parts.append(
            "All data follows ARGO quality control standards. Only good quality data (QC flags 1-2) is recommended for scientific analysis."
        )

        return " ".join(explanation_parts)

    def _get_parameter_synonyms(self, param_code: str) -> List[str]:
        """Get synonyms for parameter names."""
        synonyms = {
            "TEMP": ["temp", "temperature", "thermal"],
            "PSAL": ["salinity", "salt", "conductivity"],
            "PRES": ["pressure", "depth", "level"],
            "DOXY": ["oxygen", "o2", "dissolved oxygen"],
            "CHLA": ["chlorophyll", "chl", "phytoplankton", "productivity"]
        }
        return synonyms.get(param_code, [])

    def _extract_spatial_context(self, message_lower: str) -> Dict[str, Any]:
        """Extract spatial context from message."""
        spatial_context = {}

        # Check for ocean regions
        for region, info in self.ocean_regions.items():
            if region in message_lower:
                spatial_context["region"] = region
                spatial_context["characteristics"] = info["characteristics"]
                break

        # Check for coordinates
        lat_match = re.search(r'lat[itude]*[:\s]*([+-]?\d+\.?\d*)', message_lower)
        lon_match = re.search(r'lon[gitude]*[:\s]*([+-]?\d+\.?\d*)', message_lower)

        if lat_match and lon_match:
            spatial_context["coordinates"] = {
                "latitude": float(lat_match.group(1)),
                "longitude": float(lon_match.group(1))
            }

        # Check for general directional terms
        directions = ["north", "south", "east", "west", "equator", "pole"]
        for direction in directions:
            if direction in message_lower:
                spatial_context["direction"] = direction
                break

        return spatial_context

    def _extract_temporal_context(self, message_lower: str) -> Dict[str, Any]:
        """Extract temporal context from message."""
        temporal_context = {}

        # Relative time terms
        relative_terms = {
            "recent": "last_month",
            "latest": "last_week",
            "current": "present",
            "today": "today",
            "yesterday": "yesterday"
        }

        for term, meaning in relative_terms.items():
            if term in message_lower:
                temporal_context["relative_time"] = meaning
                break

        # Seasonal terms
        seasons = ["winter", "spring", "summer", "fall", "autumn"]
        for season in seasons:
            if season in message_lower:
                temporal_context["season"] = season
                break

        # Specific months
        months = ["january", "february", "march", "april", "may", "june",
                 "july", "august", "september", "october", "november", "december"]
        for month in months:
            if month in message_lower:
                temporal_context["month"] = month
                break

        return temporal_context

    def _determine_analysis_type(self, message_lower: str) -> str:
        """Determine the type of analysis requested."""
        if any(term in message_lower for term in ["profile", "vertical", "depth"]):
            return "vertical_profile"
        elif any(term in message_lower for term in ["float", "instrument", "trajectory"]):
            return "float_analysis"
        elif any(term in message_lower for term in ["statistics", "stats", "mean", "average"]):
            return "statistical"
        elif any(term in message_lower for term in ["map", "spatial", "region"]):
            return "spatial"
        elif any(term in message_lower for term in ["time", "temporal", "trend"]):
            return "temporal"
        else:
            return "general_query"

    def _suggest_tools(self, interpretation: Dict[str, Any]) -> List[str]:
        """Suggest appropriate tools based on query interpretation."""
        tools = []

        analysis_type = interpretation["analysis_type"]

        if analysis_type == "vertical_profile":
            tools.extend(["list_profiles", "get_profile_details"])
        elif analysis_type == "float_analysis":
            tools.extend(["search_floats_near", "list_profiles"])
        elif analysis_type == "statistical":
            tools.extend(["list_profiles", "get_profile_statistics"])
        else:
            # Default tool progression
            tools.append("list_profiles")

        # Add specific tools based on parameters
        if interpretation["parameters_of_interest"]:
            tools.append("get_profile_statistics")

        # Add geographic tools if spatial context
        if interpretation["spatial_context"]:
            if "coordinates" in interpretation["spatial_context"]:
                tools.append("search_floats_near")

        return list(set(tools))  # Remove duplicates

    def _determine_scientific_significance(self, interpretation: Dict[str, Any]) -> List[str]:
        """Determine scientific significance of the query."""
        significance = []

        # Based on parameters
        for param in interpretation["parameters_of_interest"]:
            param_code = param["code"]
            if param_code in ["TEMP", "PSAL"]:
                significance.append("Ocean circulation and water mass analysis")
            if param_code == "DOXY":
                significance.append("Marine ecosystem health and ocean ventilation")
            if param_code == "CHLA":
                significance.append("Primary productivity and marine food web dynamics")

        # Based on spatial context
        spatial = interpretation["spatial_context"]
        if spatial.get("region") == "equatorial":
            significance.append("Climate variability and El Niño/La Niña dynamics")
        elif spatial.get("region") in ["polar", "subpolar"]:
            significance.append("Deep water formation and global circulation")

        return significance