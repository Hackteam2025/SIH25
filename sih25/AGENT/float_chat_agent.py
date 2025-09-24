"""
FloatChatAgent - AGNO-based AI Agent for Oceanographic Data

Main agent implementation using AGNO framework for conversational
interface to ARGO ocean data discovery and visualization.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.groq import Groq
from pydantic import BaseModel

from .mcp_client import MCPToolClient
from .conversation_memory import ConversationMemory
from .scientific_context import ScientificContext

logger = logging.getLogger(__name__)

if load_dotenv("../../../.env"):
    logger.warning("Loaded environment variables from .env")
else:
    logger.error("No .env file found, using system environment variables")

class AgentResponse(BaseModel):
    """Response from the FloatChatAgent."""
    success: bool
    response_text: str
    tool_calls_made: List[Dict[str, Any]] = []
    data_for_visualization: Optional[Dict[str, Any]] = None
    conversation_context: Optional[Dict[str, Any]] = None
    scientific_insights: List[str] = []
    follow_up_suggestions: List[str] = []
    metadata: Dict[str, Any] = {}


class FloatChatAgent:
    """
    AGNO-based conversational agent for oceanographic data discovery.

    Provides natural language interface to ARGO float data through
    MCP Tool Server integration with scientific accuracy and context.
    """

    def __init__(
        self,
        mcp_server_url: str = "http://localhost:8000",
        model_name: str = "moonshotai/kimi-k2-instruct-0905",
        api_key: Optional[str] = os.getenv("GROQ_API_KEY") 
    ):
        """
        Initialize FloatChatAgent.

        Args:
            mcp_server_url: URL of the MCP Tool Server
            model_name: Model name to use (default: moonshotai/kimi-k2-instruct-0905)
            api_key: API key for Groq provider
        """
        self.mcp_client = MCPToolClient(mcp_server_url)
        self.scientific_context = ScientificContext()
        self.sessions: Dict[str, ConversationMemory] = {}
        self.logger = logger

        # Initialize AGNO agent
        self._setup_agno_agent(model_name, api_key)

    def _setup_agno_agent(self, model_name: str, api_key: Optional[str]):
        """Setup the AGNO agent with Groq LLM."""
        # Initialize Groq model
        model = Groq(id=model_name, api_key=api_key)

        # Create AGNO agent with oceanographic expertise
        self.agent = Agent(
            name="FloatChat Oceanographer",
            model=model,
            description="Expert oceanographer specializing in ARGO float data analysis and interpretation",
            instructions=[
                "You are an expert oceanographer with deep knowledge of ARGO float data.",
                "You help users discover and understand ocean measurements through natural conversation.",
                "Always provide scientific context and explain the significance of data.",
                "Use only the MCP tools provided - never make up or hallucinate data.",
                "Ensure all data interpretations are scientifically accurate.",
                "Suggest follow-up questions to encourage exploration.",
                "Explain quality control concepts when relevant.",
                "Be conversational but maintain scientific rigor."
            ],
            tools=[],  # Tools will be added dynamically
            markdown=True
        )

    async def initialize(self) -> bool:
        """
        Initialize the agent and its components.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize MCP client
            if not await self.mcp_client.initialize():
                self.logger.error("Failed to initialize MCP client")
                return False

            # Add MCP tools to AGNO agent
            await self._setup_mcp_tools()

            self.logger.info("FloatChatAgent initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize FloatChatAgent: {e}")
            return False

    async def _setup_mcp_tools(self):
        """Setup MCP tools as AGNO tools."""
        # This would integrate MCP tools with AGNO's tool system
        # For now, we'll handle tool calls manually in process_query
        tool_descriptions = await self.mcp_client.discover_tools()
        self.logger.info(f"Discovered {len(tool_descriptions)} MCP tools")

    async def process_query(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a user's natural language query.

        Args:
            user_message: User's natural language input
            session_id: Session identifier for conversation continuity
            context: Additional context information

        Returns:
            AgentResponse with results and conversation state
        """
        start_time = datetime.now()

        try:
            # Get or create session
            if session_id is None:
                session_id = str(uuid.uuid4())

            if session_id not in self.sessions:
                self.sessions[session_id] = ConversationMemory(session_id)

            session = self.sessions[session_id]

            # Interpret query scientifically
            query_interpretation = self.scientific_context.interpret_query(user_message)

            # Get conversation context
            conversation_context = session.get_recent_context()

            # Plan and execute tool calls
            tool_calls_made = []
            tool_results = []

            # Determine which tools to call based on query interpretation
            suggested_tools = query_interpretation["suggested_tools"]

            for tool_name in suggested_tools[:3]:  # Limit to 3 tools per query
                tool_params = await self._prepare_tool_parameters(
                    tool_name, query_interpretation, conversation_context, user_message
                )

                if tool_params:
                    self.logger.info(f"Calling tool {tool_name} with params: {tool_params}")
                    tool_result = await self.mcp_client.call_tool(tool_name, tool_params)

                    tool_calls_made.append({
                        "tool_name": tool_name,
                        "parameters": tool_params,
                        "success": tool_result.success
                    })

                    tool_results.append(tool_result)

            # Generate response using AGNO agent
            agent_response_text = await self._generate_response_with_agno(
                user_message, tool_results, query_interpretation, conversation_context
            )

            # Prepare data for visualization
            viz_data = self._prepare_visualization_data(tool_results)

            # Generate scientific insights
            scientific_insights = self._generate_scientific_insights(tool_results, query_interpretation)

            # Generate follow-up suggestions
            follow_up_suggestions = self._generate_follow_up_suggestions(query_interpretation, tool_results)

            # Create response
            response = AgentResponse(
                success=True,
                response_text=agent_response_text,
                tool_calls_made=tool_calls_made,
                data_for_visualization=viz_data,
                conversation_context=conversation_context,
                scientific_insights=scientific_insights,
                follow_up_suggestions=follow_up_suggestions,
                metadata={
                    "session_id": session_id,
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "query_interpretation": query_interpretation,
                    "tools_called": len(tool_calls_made)
                }
            )

            # Update conversation memory
            session.add_turn(
                user_message=user_message,
                agent_response=agent_response_text,
                tool_calls=tool_calls_made,
                context_used=conversation_context,
                metadata=response.metadata
            )

            return response

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return AgentResponse(
                success=False,
                response_text=f"I encountered an error while processing your query: {str(e)}. Please try rephrasing your question.",
                metadata={
                    "session_id": session_id or "unknown",
                    "error": str(e),
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
                }
            )

    async def _prepare_tool_parameters(
        self,
        tool_name: str,
        query_interpretation: Dict[str, Any],
        conversation_context: Dict[str, Any],
        user_message: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Prepare parameters for a specific tool call."""
        params = {}

        if tool_name == "list_profiles":
            # Extract geographic bounds
            spatial = query_interpretation.get("spatial_context", {})

            if "coordinates" in spatial:
                coords = spatial["coordinates"]
                # Create a bounding box around the coordinates
                lat_margin = 2.0  # degrees
                lon_margin = 2.0  # degrees
                params.update({
                    "lat_min": coords["latitude"] - lat_margin,
                    "lat_max": coords["latitude"] + lat_margin,
                    "lon_min": coords["longitude"] - lon_margin,
                    "lon_max": coords["longitude"] + lon_margin
                })
            else:
                # Use default or conversation context
                region = spatial.get("region", "global")

                # Define ocean regions with their bounding boxes
                ocean_regions = {
                    "mediterranean": {"lat_min": 30, "lat_max": 46, "lon_min": -6, "lon_max": 37},
                    "north_atlantic": {"lat_min": 20, "lat_max": 60, "lon_min": -80, "lon_max": 0},
                    "south_atlantic": {"lat_min": -60, "lat_max": 0, "lon_min": -70, "lon_max": 20},
                    "north_pacific": {"lat_min": 20, "lat_max": 60, "lon_min": 120, "lon_max": -120},
                    "south_pacific": {"lat_min": -60, "lat_max": 0, "lon_min": 150, "lon_max": -70},
                    "indian": {"lat_min": -60, "lat_max": 30, "lon_min": 20, "lon_max": 120},
                    "arctic": {"lat_min": 66, "lat_max": 90, "lon_min": -180, "lon_max": 180},
                    "southern": {"lat_min": -90, "lat_max": -60, "lon_min": -180, "lon_max": 180},
                    "equatorial": {"lat_min": -5, "lat_max": 5, "lon_min": -180, "lon_max": 180},
                    "tropical": {"lat_min": -23.5, "lat_max": 23.5, "lon_min": -180, "lon_max": 180},
                    "caribbean": {"lat_min": 10, "lat_max": 27, "lon_min": -90, "lon_max": -60},
                    "gulf_mexico": {"lat_min": 18, "lat_max": 31, "lon_min": -98, "lon_max": -80},
                    "red_sea": {"lat_min": 12, "lat_max": 30, "lon_min": 32, "lon_max": 44},
                    "baltic": {"lat_min": 53, "lat_max": 66, "lon_min": 10, "lon_max": 30},
                    "black_sea": {"lat_min": 40.5, "lat_max": 47, "lon_min": 27, "lon_max": 42}
                }

                # Check if the message contains any region keywords
                message_lower = user_message.lower()
                detected_region = None

                for region_name, bounds in ocean_regions.items():
                    # Check for region name in the message
                    if region_name.replace("_", " ") in message_lower or region_name.replace("_", "") in message_lower:
                        detected_region = region_name
                        break

                # Use detected region or specified region
                final_region = detected_region or region

                if final_region in ocean_regions:
                    params.update(ocean_regions[final_region])
                else:
                    # Default global search with reasonable limits
                    params.update({"lat_min": -90, "lat_max": 90, "lon_min": -180, "lon_max": 180})

            # Add temporal constraints
            temporal = query_interpretation.get("temporal_context", {})
            if temporal.get("relative_time") == "recent":
                params["days_back"] = 30

            # Limit results
            params["max_results"] = conversation_context.get("user_preferences", {}).get("max_results_per_query", 100)

        elif tool_name == "search_floats_near":
            spatial = query_interpretation.get("spatial_context", {})
            if "coordinates" in spatial:
                coords = spatial["coordinates"]
                params.update({
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "radius_km": 100  # Default radius
                })
            else:
                # Skip this tool if no coordinates
                return None

        elif tool_name == "get_profile_statistics":
            # This requires a profile_id from previous results
            # For now, skip if we don't have one
            current_context = conversation_context.get("current_context", {})
            if "last_profile_id" in current_context:
                params["profile_id"] = current_context["last_profile_id"]

                # Determine parameter
                parameters = query_interpretation.get("parameters_of_interest", [])
                if parameters:
                    params["variable"] = parameters[0]["code"]
                else:
                    params["variable"] = "TEMP"  # Default
            else:
                return None

        return params if params else None

    async def _generate_response_with_agno(
        self,
        user_message: str,
        tool_results: List[Any],
        query_interpretation: Dict[str, Any],
        conversation_context: Dict[str, Any]
    ) -> str:
        """Generate response using AGNO agent."""
        # Prepare context for AGNO agent
        context_message = self._build_context_message(
            user_message, tool_results, query_interpretation, conversation_context
        )

        try:
            # Use AGNO agent to generate response
            response = self.agent.run(context_message)
            return str(response.content) if hasattr(response, 'content') else str(response)

        except Exception as e:
            self.logger.error(f"AGNO agent error: {e}")
            # Fallback to basic response generation
            return self._generate_fallback_response(user_message, tool_results, query_interpretation)

    def _build_context_message(
        self,
        user_message: str,
        tool_results: List[Any],
        query_interpretation: Dict[str, Any],
        conversation_context: Dict[str, Any]
    ) -> str:
        """Build context message for AGNO agent."""
        context_parts = [
            f"User Query: {user_message}",
            "",
            "Query Analysis:",
            f"- Analysis Type: {query_interpretation.get('analysis_type', 'unknown')}",
            f"- Parameters of Interest: {[p['name'] for p in query_interpretation.get('parameters_of_interest', [])]}",
            f"- Spatial Context: {query_interpretation.get('spatial_context', {})}",
            f"- Temporal Context: {query_interpretation.get('temporal_context', {})}",
            ""
        ]

        # Add tool results
        if tool_results:
            context_parts.append("Data Retrieved:")
            for i, result in enumerate(tool_results):
                if result.success:
                    data_summary = f"Tool {i+1} returned {len(result.data) if hasattr(result.data, '__len__') else 1} records"
                    context_parts.append(f"- {data_summary}")
                else:
                    context_parts.append(f"- Tool {i+1} failed: {result.errors}")
            context_parts.append("")

        # Add conversation context
        recent_turns = conversation_context.get("recent_conversation", [])
        if recent_turns:
            context_parts.append("Recent Conversation:")
            for turn in recent_turns[-2:]:  # Last 2 turns
                context_parts.append(f"- User: {turn['user'][:50]}...")
                context_parts.append(f"- Agent: {turn['agent'][:50]}...")
            context_parts.append("")

        context_parts.extend([
            "Instructions:",
            "- Provide a comprehensive, scientifically accurate response",
            "- Explain the significance of any data found",
            "- Include relevant oceanographic context",
            "- Suggest follow-up questions if appropriate",
            "- Be conversational but maintain scientific rigor"
        ])

        return "\n".join(context_parts)

    def _generate_fallback_response(
        self,
        user_message: str,
        tool_results: List[Any],
        query_interpretation: Dict[str, Any]
    ) -> str:
        """Generate a fallback response when AGNO agent fails."""
        response_parts = []

        # Start with acknowledgment
        response_parts.append("I've analyzed your query about oceanographic data.")

        # Summarize results
        successful_results = [r for r in tool_results if r.success]
        if successful_results:
            total_records = sum(len(r.data) if hasattr(r.data, '__len__') else 1 for r in successful_results)
            response_parts.append(f"I found {total_records} relevant records in the ARGO database.")

            # Add scientific context
            for param in query_interpretation.get("parameters_of_interest", []):
                param_code = param["code"]
                if param_code in self.scientific_context.argo_parameters:
                    param_info = self.scientific_context.argo_parameters[param_code]
                    response_parts.append(
                        f"{param_info['name']} measurements are {param_info['scientific_significance'].lower()}."
                    )
        else:
            response_parts.append("I wasn't able to retrieve data matching your specific criteria.")

        # Add spatial/temporal context
        spatial = query_interpretation.get("spatial_context", {})
        if spatial.get("region"):
            region_info = self.scientific_context.ocean_regions.get(spatial["region"])
            if region_info:
                response_parts.append(f"The {spatial['region']} region you're interested in is {region_info['characteristics'].lower()}.")

        return " ".join(response_parts)

    def _prepare_visualization_data(self, tool_results: List[Any]) -> Optional[Dict[str, Any]]:
        """Prepare data for frontend visualization."""
        if not tool_results or not any(r.success for r in tool_results):
            return None

        viz_data = {
            "type": "oceanographic_data",
            "data_points": [],
            "summary": {},
            "parameters": []
        }

        for result in tool_results:
            if result.success and result.data:
                if hasattr(result.data, '__iter__') and not isinstance(result.data, str):
                    # Collection of data points
                    for item in result.data:
                        if hasattr(item, '__dict__'):
                            point = {}
                            # Extract common fields
                            for attr in ['latitude', 'longitude', 'date', 'temperature', 'salinity', 'pressure']:
                                if hasattr(item, attr):
                                    point[attr] = getattr(item, attr)
                            if point:
                                viz_data["data_points"].append(point)

        # Add summary statistics
        if viz_data["data_points"]:
            viz_data["summary"] = {
                "total_points": len(viz_data["data_points"]),
                "date_range": self._get_date_range(viz_data["data_points"]),
                "geographic_bounds": self._get_geographic_bounds(viz_data["data_points"])
            }

        return viz_data if viz_data["data_points"] else None

    def _generate_scientific_insights(
        self, tool_results: List[Any], query_interpretation: Dict[str, Any]
    ) -> List[str]:
        """Generate scientific insights from the data."""
        insights = []

        # Add parameter-specific insights
        for param in query_interpretation.get("parameters_of_interest", []):
            param_code = param["code"]
            if param_code == "TEMP":
                insights.append("Temperature profiles reveal ocean thermal structure and mixing processes.")
            elif param_code == "PSAL":
                insights.append("Salinity measurements help identify water masses and circulation patterns.")
            elif param_code == "DOXY":
                insights.append("Oxygen levels indicate ocean ventilation and ecosystem health.")

        # Add spatial insights
        spatial = query_interpretation.get("spatial_context", {})
        if spatial.get("region") == "equatorial":
            insights.append("Equatorial regions show strong seasonal variability related to trade wind patterns.")

        return insights

    def _generate_follow_up_suggestions(
        self, query_interpretation: Dict[str, Any], tool_results: List[Any]
    ) -> List[str]:
        """Generate follow-up question suggestions."""
        suggestions = []

        # Based on analysis type
        analysis_type = query_interpretation.get("analysis_type", "")

        if analysis_type == "vertical_profile":
            suggestions.extend([
                "Would you like to see how these profiles compare to seasonal averages?",
                "Are you interested in the quality control status of these measurements?"
            ])
        elif analysis_type == "spatial":
            suggestions.extend([
                "Would you like to explore temporal trends in this region?",
                "Are you interested in comparing this region to others?"
            ])

        # Based on parameters
        params = [p["code"] for p in query_interpretation.get("parameters_of_interest", [])]
        if "TEMP" in params and "PSAL" not in params:
            suggestions.append("Would you also like to see salinity data for water mass identification?")

        if len(params) == 1:
            suggestions.append("Would you like to explore correlations with other oceanographic parameters?")

        return suggestions[:3]  # Limit to 3 suggestions

    def _get_date_range(self, data_points: List[Dict]) -> Optional[Dict[str, str]]:
        """Get date range from data points."""
        dates = [p.get("date") for p in data_points if p.get("date")]
        if not dates:
            return None

        return {
            "start": min(dates),
            "end": max(dates)
        }

    def _get_geographic_bounds(self, data_points: List[Dict]) -> Optional[Dict[str, float]]:
        """Get geographic bounds from data points."""
        lats = [p.get("latitude") for p in data_points if p.get("latitude") is not None]
        lons = [p.get("longitude") for p in data_points if p.get("longitude") is not None]

        if not lats or not lons:
            return None

        return {
            "lat_min": min(lats),
            "lat_max": max(lats),
            "lon_min": min(lons),
            "lon_max": max(lons)
        }

    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a conversation session."""
        if session_id not in self.sessions:
            return None

        return self.sessions[session_id].get_conversation_summary()

    async def close(self):
        """Close the agent and cleanup resources."""
        await self.mcp_client.close()
        self.logger.info("FloatChatAgent closed")