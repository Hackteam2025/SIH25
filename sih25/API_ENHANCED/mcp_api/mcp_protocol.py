#!/usr/bin/env python3
"""
MCP Protocol Enhancement Module
Adds additional MCP-specific functionality and utilities for AI Agent integration
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import HTTPException

from sih25.API.models import ToolResponse

logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """
    Enhanced MCP protocol handling for AI Agent integration

    Provides:
    - Tool metadata generation
    - Response formatting for LLM consumption
    - Conversation context preservation
    - Scientific unit conversion and labeling
    """

    def __init__(self):
        self.logger = logger

    def format_for_llm(self, tool_response: ToolResponse, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format tool response for optimal LLM processing

        Args:
            tool_response: Raw tool response
            context: Optional conversation context

        Returns:
            LLM-optimized response format
        """
        formatted = {
            "success": tool_response.success,
            "tool_execution_time_ms": tool_response.execution_time_ms,
            "scientific_context": {},
            "data_summary": {},
            "llm_interpretation": {}
        }

        if tool_response.success and tool_response.data:
            # Add scientific context and interpretation
            if isinstance(tool_response.data, list):
                formatted["data_summary"] = {
                    "type": "list",
                    "count": len(tool_response.data),
                    "sample_record": tool_response.data[0].__dict__ if hasattr(tool_response.data[0], '__dict__') else str(tool_response.data[0])
                }

                # Generate natural language summary
                formatted["llm_interpretation"]["summary"] = self._generate_data_summary(tool_response.data)

            elif hasattr(tool_response.data, '__dict__'):
                formatted["data_summary"] = {
                    "type": "single_record",
                    "fields": list(tool_response.data.__dict__.keys())
                }

            # Add scientific units and meanings
            formatted["scientific_context"] = self._add_scientific_context(tool_response.data)

        # Include warnings and errors with explanations
        if tool_response.warnings:
            formatted["data_quality_warnings"] = [
                {
                    "message": warning.message,
                    "explanation": self._explain_warning(warning),
                    "recommendation": warning.recommendation
                }
                for warning in tool_response.warnings
            ]

        if tool_response.errors:
            formatted["errors"] = [
                {
                    "type": error.get("error", "unknown"),
                    "message": error.get("message", "Unknown error"),
                    "user_friendly_explanation": self._explain_error(error)
                }
                for error in tool_response.errors
            ]

        # Add metadata
        formatted["metadata"] = tool_response.metadata or {}
        formatted["argo_compliance"] = formatted["metadata"].get("argo_compliance_validated", False)

        return formatted

    def _generate_data_summary(self, data: List[Any]) -> str:
        """Generate natural language summary of data for LLM"""
        if not data:
            return "No data found matching the query criteria."

        data_type = type(data[0]).__name__
        count = len(data)

        if "Profile" in data_type:
            return f"Found {count} ARGO oceanographic profiles. Each profile represents measurements from a single float at a specific time and location."

        elif "Float" in data_type:
            return f"Found {count} ARGO floats. These are autonomous instruments that drift in the ocean collecting temperature, salinity, and other measurements."

        elif "VariableStats" in data_type:
            var_name = getattr(data[0], 'variable', 'unknown')
            return f"Statistical analysis of {var_name} measurements. Includes mean, standard deviation, and quality control information."

        else:
            return f"Found {count} records of type {data_type}."

    def _add_scientific_context(self, data: Any) -> Dict[str, Any]:
        """Add scientific context and unit information"""
        context = {
            "argo_program_info": "ARGO is an international program providing real-time ocean observations",
            "data_standards": "Data follows ARGO quality control standards with QC flags",
            "units_and_meanings": {}
        }

        # Add parameter-specific context
        if hasattr(data, '__iter__') and not isinstance(data, str):
            # For lists of data
            if data and hasattr(data[0], 'parameters_available'):
                params = getattr(data[0], 'parameters_available', [])
                context["units_and_meanings"] = self._get_parameter_meanings(params)

        elif hasattr(data, 'variable'):
            # For variable statistics
            var = getattr(data, 'variable')
            context["units_and_meanings"] = self._get_parameter_meanings([var])

        return context

    def _get_parameter_meanings(self, parameters: List[str]) -> Dict[str, Dict[str, str]]:
        """Get scientific meanings and units for parameters"""
        meanings = {
            'TEMP': {
                'name': 'Temperature',
                'units': '°C (degrees Celsius)',
                'meaning': 'Seawater temperature measured in situ',
                'typical_range': '-2 to 35°C'
            },
            'PSAL': {
                'name': 'Practical Salinity',
                'units': 'PSU (Practical Salinity Units)',
                'meaning': 'Salinity of seawater based on conductivity',
                'typical_range': '30 to 37 PSU'
            },
            'PRES': {
                'name': 'Pressure',
                'units': 'dbar (decibar)',
                'meaning': 'Water pressure, approximately equal to depth in meters',
                'typical_range': '0 to 2000+ dbar'
            },
            'DOXY': {
                'name': 'Dissolved Oxygen',
                'units': 'μmol/kg (micromoles per kilogram)',
                'meaning': 'Concentration of dissolved oxygen in seawater',
                'typical_range': '0 to 400 μmol/kg'
            },
            'CHLA': {
                'name': 'Chlorophyll-a',
                'units': 'mg/m³ (milligrams per cubic meter)',
                'meaning': 'Concentration of chlorophyll-a, indicator of phytoplankton',
                'typical_range': '0 to 10 mg/m³'
            }
        }

        return {param: meanings.get(param, {
            'name': param,
            'units': 'Unknown',
            'meaning': 'Standard ARGO parameter',
            'typical_range': 'Varies'
        }) for param in parameters}

    def _explain_warning(self, warning) -> str:
        """Provide user-friendly explanation of warnings"""
        message = warning.message.lower()

        if "real-time" in message and "delayed" in message:
            return "Real-time data hasn't undergone full quality control. Delayed-mode data is preferred for scientific analysis."

        elif "qc" in message or "quality" in message:
            return "Some data points have quality control flags indicating potential issues. This is normal but worth noting."

        elif "gap" in message:
            return "There are missing time periods in the data. This could affect temporal analysis."

        elif "movement" in message or "speed" in message:
            return "The float appears to have moved unusually fast, which might indicate a data processing error."

        else:
            return "This warning provides information about potential data quality considerations."

    def _explain_error(self, error: Dict[str, Any]) -> str:
        """Provide user-friendly explanation of errors"""
        error_type = error.get("error", "").lower()
        message = error.get("message", "").lower()

        if "validation" in error_type:
            return "The request parameters don't meet safety or format requirements. Please check the input values."

        elif "not found" in message:
            return "The requested data (profile, float, etc.) doesn't exist in the database."

        elif "timeout" in message or "performance" in message:
            return "The query is too complex or large. Try reducing the search area, time range, or result count."

        else:
            return "An unexpected error occurred. Please try again or contact support."

    def generate_tool_descriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate comprehensive tool descriptions for MCP discovery

        Returns:
            Dictionary of tool descriptions optimized for AI agents
        """
        return {
            "list_profiles": {
                "name": "list_profiles",
                "description": "Search for ARGO oceanographic profiles within geographic and temporal bounds",
                "ai_guidance": {
                    "when_to_use": "When user wants to find ocean measurements in a specific area and time period",
                    "example_scenarios": [
                        "Find temperature profiles in the Gulf Stream",
                        "Get recent measurements near a specific location",
                        "Search for data during a particular season"
                    ],
                    "parameter_tips": {
                        "geographic_bounds": "Use reasonable bounding boxes - very large areas may return too much data",
                        "time_range": "ARGO data goes back to ~1999, be aware of data density variations",
                        "max_results": "Start with 100-500 results, increase if needed"
                    }
                },
                "scientific_context": "Returns ProfileSummary objects with QC-filtered, ARGO-compliant data",
                "response_format": "List of profiles with metadata, coordinates, and available parameters"
            },

            "get_profile_details": {
                "name": "get_profile_details",
                "description": "Get comprehensive information about a specific ARGO profile",
                "ai_guidance": {
                    "when_to_use": "When user wants detailed information about a specific profile",
                    "example_scenarios": [
                        "Examine quality control status of a profile",
                        "Get complete parameter list for a measurement",
                        "Understand data provenance and processing"
                    ],
                    "parameter_tips": {
                        "profile_id": "Must be exact profile identifier from list_profiles results"
                    }
                },
                "scientific_context": "Provides complete profile metadata including QC summaries and data provenance",
                "response_format": "Single ProfileDetail object with comprehensive information"
            },

            "search_floats_near": {
                "name": "search_floats_near",
                "description": "Find ARGO floats within a specified radius of coordinates",
                "ai_guidance": {
                    "when_to_use": "When user wants to find floats operating near a specific location",
                    "example_scenarios": [
                        "Find all floats within 100km of a research station",
                        "Locate floats in a hurricane path",
                        "Identify active floats for comparison studies"
                    ],
                    "parameter_tips": {
                        "radius_km": "Use 50-200km for local searches, up to 500km for regional",
                        "coordinates": "Use decimal degrees, ensure they're in ocean areas"
                    }
                },
                "scientific_context": "Returns active floats with deployment info and profile counts",
                "response_format": "List of FloatSummary objects with status and activity information"
            },

            "get_profile_statistics": {
                "name": "get_profile_statistics",
                "description": "Calculate statistical summary of oceanographic variables in a profile",
                "ai_guidance": {
                    "when_to_use": "When user wants numerical analysis of specific measurements",
                    "example_scenarios": [
                        "Get temperature statistics for a specific profile",
                        "Analyze salinity distribution in measurements",
                        "Understand data quality through QC statistics"
                    ],
                    "parameter_tips": {
                        "variable": "Use standard ARGO names: TEMP, PSAL, PRES, DOXY, etc.",
                        "profile_id": "Must be exact identifier from previous queries"
                    }
                },
                "scientific_context": "Provides mean, std dev, range, and QC flag distributions",
                "response_format": "Single VariableStats object with comprehensive statistics"
            }
        }


# Global MCP handler instance
mcp_handler = MCPProtocolHandler()