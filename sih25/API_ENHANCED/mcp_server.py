"""
MCP (Model Context Protocol) Server Wrapper for FloatChat
Wraps existing FloatChat API endpoints as MCP tools for AI agents
"""

import sys
import logging
from typing import Any, Dict, List
from dataclasses import dataclass, asdict
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    """MCP Tool Specification"""
    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class FloatChatMCPServer:
    """
    MCP Server that wraps FloatChat backend API endpoints
    Provides oceanographic data query tools for AI agents
    """

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.tools = self._register_tools()

    def _register_tools(self) -> List[MCPTool]:
        """Register available MCP tools"""
        return [
            MCPTool(
                name="query_ocean_data",
                description="Query ARGO float ocean data with natural language",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query about ocean data"
                        },
                        "language": {
                            "type": "string",
                            "enum": ["en", "hi", "ta", "te"],
                            "default": "en",
                            "description": "Response language"
                        },
                        "region": {
                            "type": "string",
                            "optional": True,
                            "description": "Specific ocean region (Arabian Sea, Bay of Bengal, etc.)"
                        },
                        "parameters": {
                            "type": "array",
                            "items": {"type": "string"},
                            "optional": True,
                            "description": "Specific parameters to query (TEMP, PSAL, DOXY, etc.)"
                        },
                        "date_range": {
                            "type": "object",
                            "optional": True,
                            "properties": {
                                "start": {"type": "string", "format": "date"},
                                "end": {"type": "string", "format": "date"}
                            },
                            "description": "Date range for data query"
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="get_ocean_profiles",
                description="Get detailed ocean profiles for specific locations",
                input_schema={
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude coordinate"
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude coordinate"
                        },
                        "radius_km": {
                            "type": "number",
                            "default": 50,
                            "description": "Search radius in kilometers"
                        },
                        "parameters": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": ["TEMP", "PSAL"],
                            "description": "Parameters to include in profiles"
                        },
                        "depth_levels": {
                            "type": "array",
                            "items": {"type": "number"},
                            "optional": True,
                            "description": "Specific depth levels to query"
                        }
                    },
                    "required": ["latitude", "longitude"]
                }
            ),
            MCPTool(
                name="analyze_ocean_trends",
                description="Analyze temporal trends in ocean parameters",
                input_schema={
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "Ocean region to analyze"
                        },
                        "parameter": {
                            "type": "string",
                            "enum": ["TEMP", "PSAL", "DOXY", "CHLA"],
                            "description": "Parameter to analyze"
                        },
                        "time_period": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly", "yearly"],
                            "default": "monthly",
                            "description": "Time aggregation period"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["mean", "anomaly", "trend", "variability"],
                            "default": "mean",
                            "description": "Type of analysis to perform"
                        }
                    },
                    "required": ["region", "parameter"]
                }
            ),
            MCPTool(
                name="get_data_statistics",
                description="Get statistical summary of ocean data",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Description of data to summarize"
                        },
                        "include_quality_info": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include data quality statistics"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool by calling the appropriate backend endpoint
        """
        try:
            if tool_name == "query_ocean_data":
                return await self._query_ocean_data(arguments)
            elif tool_name == "get_ocean_profiles":
                return await self._get_ocean_profiles(arguments)
            elif tool_name == "analyze_ocean_trends":
                return await self._analyze_ocean_trends(arguments)
            elif tool_name == "get_data_statistics":
                return await self._get_data_statistics(arguments)
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "success": False
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "error": str(e),
                "success": False
            }

    async def _query_ocean_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute natural language query against ocean data"""
        # Use the chat endpoint for natural language queries
        response = await self.client.post(
            f"{self.backend_url}/chat/",
            json={
                "message": args["query"],
                "latitude": args.get("latitude"),
                "longitude": args.get("longitude")
            }
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "answer": data.get("answer"),
                "suggestions": data.get("suggestions", []),
                "data_insights": data.get("data_insights", {}),
                "metadata": {
                    "query_time": datetime.now().isoformat(),
                    "language": args.get("language", "en"),
                    "region": args.get("region")
                }
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code}",
                "details": response.text
            }

    async def _get_ocean_profiles(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get ocean profiles for specific location"""
        # Use the data/nearest endpoint
        response = await self.client.get(
            f"{self.backend_url}/data/nearest",
            params={
                "latitude": args["latitude"],
                "longitude": args["longitude"],
                "radius": args.get("radius_km", 50),
                "limit": 100
            }
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "profiles": data.get("results", []),
                "count": data.get("count", 0),
                "location": {
                    "lat": args["latitude"],
                    "lon": args["longitude"],
                    "radius_km": args.get("radius_km", 50)
                },
                "metadata": {
                    "center": data.get("center", {}),
                    "radius_km": data.get("radius_km", 0)
                }
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code}",
                "details": response.text
            }

    async def _analyze_ocean_trends(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal trends in ocean data"""
        # Use the analytics endpoints
        response = await self.client.get(
            f"{self.backend_url}/data/analytics/temporal"
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "trends": data,
                "analysis_type": args.get("analysis_type", "temporal"),
                "parameter": args["parameter"],
                "region": args["region"],
                "metadata": {
                    "analysis_time": datetime.now().isoformat(),
                    "time_period": args.get("time_period", "monthly")
                }
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code}",
                "details": response.text
            }

    async def _get_data_statistics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistical summary of ocean data"""
        # Use the statistics endpoint
        response = await self.client.get(
            f"{self.backend_url}/data/statistics"
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "statistics": data,
                "query": args["query"],
                "include_quality_info": args.get("include_quality_info", True),
                "metadata": {
                    "stats_time": datetime.now().isoformat()
                }
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code}",
                "details": response.text
            }

    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """Get all tool descriptions for LLM configuration"""
        return [tool.to_dict() for tool in self.tools]

    async def close(self):
        """Clean up resources"""
        await self.client.aclose()


# MCP Protocol Handler
class MCPProtocolHandler:
    """
    Handles MCP protocol communication
    """

    def __init__(self, mcp_server: FloatChatMCPServer):
        self.mcp_server = mcp_server

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method")

        if method == "tools/list":
            return {
                "tools": self.mcp_server.get_tool_descriptions()
            }
        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            arguments = request.get("params", {}).get("arguments", {})
            result = await self.mcp_server.execute_tool(tool_name, arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        else:
            return {
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }


# Add stdin/stdout handling for MCP protocol
async def handle_mcp_stdio():
    """Handle MCP protocol over stdin/stdout"""
    server = FloatChatMCPServer()
    handler = MCPProtocolHandler(server)

    try:
        while True:
            # Read JSON-RPC message from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            try:
                request = json.loads(line.strip())

                # Handle initialization
                if request.get("method") == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {"listChanged": False},
                                "resources": {"subscribe": False, "listChanged": False},
                                "prompts": {"listChanged": False},
                                "logging": {}
                            },
                            "serverInfo": {
                                "name": "floatchat-mcp-server",
                                "version": "1.0.0",
                                "description": "MCP server for ARGO oceanographic data"
                            }
                        }
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                    continue

                # Handle other requests
                result = await handler.handle_request(request)
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result if "error" not in result else None,
                    "error": result.get("error") if "error" in result else None
                }

                print(json.dumps(response))
                sys.stdout.flush()

            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        await server.close()

if __name__ == "__main__":
    import asyncio
    import json

    # Set up logging to stderr so it doesn't interfere with MCP protocol
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

    asyncio.run(handle_mcp_stdio())