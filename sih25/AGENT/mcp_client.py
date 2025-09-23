"""
MCP Tool Client for AGNO Agent

Handles communication with the MCP Tool Server from Story 2.
Provides async tool calling with error handling and capability mapping.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
import httpx
from datetime import datetime

from sih25.API.models import ToolResponse

logger = logging.getLogger(__name__)


class MCPToolClient:
    """
    Client for communicating with the MCP Tool Server.

    Provides tool discovery, execution, and error handling for the AI Agent.
    """

    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        """
        Initialize MCP Tool Client.

        Args:
            mcp_server_url: URL of the MCP Tool Server from Story 2
        """
        self.server_url = mcp_server_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.available_tools: Dict[str, Dict[str, Any]] = {}
        self.logger = logger

    async def initialize(self) -> bool:
        """
        Initialize connection and discover available tools.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Test connection
            response = await self.client.get(f"{self.server_url}/health")
            if response.status_code != 200:
                self.logger.error(f"MCP Server health check failed: {response.status_code}")
                return False

            # Discover tools
            await self.discover_tools()
            self.logger.info(f"MCP Client initialized with {len(self.available_tools)} tools")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP client: {e}")
            return False

    async def discover_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover available tools from MCP server.

        Returns:
            Dictionary of tool names and their descriptions
        """
        try:
            # Get tool metadata from MCP protocol enhancement
            response = await self.client.get(f"{self.server_url}/mcp/tools")
            if response.status_code == 200:
                self.available_tools = response.json()
            else:
                # Fallback: infer tools from API endpoints
                self.available_tools = {
                    "list_profiles": {
                        "description": "Search for ARGO oceanographic profiles",
                        "endpoint": "/profiles/list",
                        "method": "POST"
                    },
                    "get_profile_details": {
                        "description": "Get detailed information about a specific profile",
                        "endpoint": "/profiles/{profile_id}",
                        "method": "GET"
                    },
                    "search_floats_near": {
                        "description": "Find ARGO floats near specified coordinates",
                        "endpoint": "/floats/search",
                        "method": "POST"
                    },
                    "get_profile_statistics": {
                        "description": "Calculate statistics for profile variables",
                        "endpoint": "/profiles/{profile_id}/stats/{variable}",
                        "method": "GET"
                    }
                }

            return self.available_tools

        except Exception as e:
            self.logger.error(f"Tool discovery failed: {e}")
            return {}

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResponse:
        """
        Execute a tool call with parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            context: Optional conversation context

        Returns:
            ToolResponse with results or errors
        """
        start_time = datetime.now()

        try:
            if tool_name not in self.available_tools:
                return ToolResponse(
                    success=False,
                    errors=[{"error": "unknown_tool", "message": f"Tool '{tool_name}' not available"}],
                    execution_time_ms=0
                )

            # Execute the appropriate tool
            if tool_name == "list_profiles":
                result = await self._call_list_profiles(parameters)
            elif tool_name == "get_profile_details":
                result = await self._call_get_profile_details(parameters)
            elif tool_name == "search_floats_near":
                result = await self._call_search_floats_near(parameters)
            elif tool_name == "get_profile_statistics":
                result = await self._call_get_profile_statistics(parameters)
            else:
                result = ToolResponse(
                    success=False,
                    errors=[{"error": "not_implemented", "message": f"Tool '{tool_name}' not implemented"}],
                    execution_time_ms=0
                )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Tool call '{tool_name}' failed: {e}")

            return ToolResponse(
                success=False,
                errors=[{"error": "execution_error", "message": str(e)}],
                execution_time_ms=execution_time
            )

    async def _call_list_profiles(self, parameters: Dict[str, Any]) -> ToolResponse:
        """Call the list_profiles endpoint."""
        response = await self.client.post(
            f"{self.server_url}/profiles/list",
            json=parameters
        )

        if response.status_code == 200:
            return ToolResponse.model_validate(response.json())
        else:
            return ToolResponse(
                success=False,
                errors=[{"error": "api_error", "message": f"HTTP {response.status_code}: {response.text}"}],
                execution_time_ms=0
            )

    async def _call_get_profile_details(self, parameters: Dict[str, Any]) -> ToolResponse:
        """Call the get_profile_details endpoint."""
        profile_id = parameters.get("profile_id")
        if not profile_id:
            return ToolResponse(
                success=False,
                errors=[{"error": "missing_parameter", "message": "profile_id is required"}],
                execution_time_ms=0
            )

        response = await self.client.get(f"{self.server_url}/profiles/{profile_id}")

        if response.status_code == 200:
            return ToolResponse.model_validate(response.json())
        else:
            return ToolResponse(
                success=False,
                errors=[{"error": "api_error", "message": f"HTTP {response.status_code}: {response.text}"}],
                execution_time_ms=0
            )

    async def _call_search_floats_near(self, parameters: Dict[str, Any]) -> ToolResponse:
        """Call the search_floats_near endpoint."""
        response = await self.client.post(
            f"{self.server_url}/floats/search",
            json=parameters
        )

        if response.status_code == 200:
            return ToolResponse.model_validate(response.json())
        else:
            return ToolResponse(
                success=False,
                errors=[{"error": "api_error", "message": f"HTTP {response.status_code}: {response.text}"}],
                execution_time_ms=0
            )

    async def _call_get_profile_statistics(self, parameters: Dict[str, Any]) -> ToolResponse:
        """Call the get_profile_statistics endpoint."""
        profile_id = parameters.get("profile_id")
        variable = parameters.get("variable")

        if not profile_id or not variable:
            return ToolResponse(
                success=False,
                errors=[{"error": "missing_parameter", "message": "profile_id and variable are required"}],
                execution_time_ms=0
            )

        response = await self.client.get(f"{self.server_url}/profiles/{profile_id}/stats/{variable}")

        if response.status_code == 200:
            return ToolResponse.model_validate(response.json())
        else:
            return ToolResponse(
                success=False,
                errors=[{"error": "api_error", "message": f"HTTP {response.status_code}: {response.text}"}],
                execution_time_ms=0
            )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def get_tool_descriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get tool descriptions for agent planning.

        Returns:
            Dictionary of tool descriptions with AI guidance
        """
        return self.available_tools