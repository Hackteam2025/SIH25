"""
Ocean Agent - Simplified AGNO Agent with Direct Supabase Access

This is the core conversational agent for oceanographic data exploration.
It uses AGNO framework with direct Supabase PostgreSQL connection for data retrieval.

Architecture:
- Frontend → API → AGNO Agent → Supabase → Response
- No custom MCP layer needed - uses AGNO's built-in database tools
- Leverages Supabase's PostgreSQL directly via AGNO's PostgresDb
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

from agno.agent import Agent
from agno.models.groq import Groq
from agno.db.postgres import PostgresDb
from agno.tools import tool, Toolkit
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================================
# Response Model
# ============================================================================

class OceanAgentResponse(BaseModel):
    """Response from the Ocean Agent."""
    success: bool = True
    response: str = Field(..., description="Natural language response to user")
    session_id: str = Field(..., description="Session identifier")
    tool_calls: List[str] = Field(default_factory=list, description="Tools used in this response")
    visualization_data: Optional[Dict[str, Any]] = Field(None, description="Data for visualization")
    scientific_insights: List[str] = Field(default_factory=list, description="Scientific insights discovered")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Suggested follow-up questions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Supabase Tools for Ocean Data
# ============================================================================

class SupabaseOceanTools(Toolkit):
    """
    Custom toolkit for querying ocean data from Supabase PostgreSQL.

    This provides AGNO-compatible tools that directly query the Supabase database
    for ARGO oceanographic profiles, floats, and observations.
    """

    def __init__(self, db: PostgresDb, *args, **kwargs):
        """Initialize with Supabase database connection."""
        super().__init__(
            name="SupabaseOceanTools",
            *args,
            **kwargs
        )
        self.db = db

    @tool
    def search_profiles(
        self,
        min_lat: float = -90,
        max_lat: float = 90,
        min_lon: float = -180,
        max_lon: float = 180,
        limit: int = 50
    ) -> str:
        """
        Search for ARGO oceanographic profiles within a geographic region.

        Args:
            min_lat: Minimum latitude (-90 to 90)
            max_lat: Maximum latitude (-90 to 90)
            min_lon: Minimum longitude (-180 to 180)
            max_lon: Maximum longitude (-180 to 180)
            limit: Maximum number of results (default 50)

        Returns:
            JSON string with profile information including location, temperature, salinity, and depth
        """
        try:
            query = f"""
                SELECT
                    p.profile_id,
                    p.float_wmo_id,
                    p.latitude,
                    p.longitude,
                    p.timestamp,
                    COUNT(o.observation_id) as observation_count,
                    MIN(o.depth) as min_depth,
                    MAX(o.depth) as max_depth
                FROM profiles p
                LEFT JOIN observations o ON p.profile_id = o.profile_id
                WHERE p.latitude >= {min_lat}
                    AND p.latitude <= {max_lat}
                    AND p.longitude >= {min_lon}
                    AND p.longitude <= {max_lon}
                GROUP BY p.profile_id, p.float_wmo_id, p.latitude, p.longitude, p.timestamp
                LIMIT {limit}
            """

            result = self.db.execute(query)

            if not result or len(result) == 0:
                return f"No profiles found in region (lat: {min_lat} to {max_lat}, lon: {min_lon} to {max_lon})"

            profiles = []
            for row in result:
                profiles.append({
                    "profile_id": row[0],
                    "float_id": row[1],
                    "latitude": float(row[2]),
                    "longitude": float(row[3]),
                    "timestamp": str(row[4]),
                    "observation_count": row[5],
                    "depth_range": f"{row[6]}-{row[7]}m" if row[6] else "unknown"
                })

            return f"Found {len(profiles)} profiles. Sample data: {profiles[:3]}"

        except Exception as e:
            logger.error(f"Error searching profiles: {e}")
            return f"Error searching profiles: {str(e)}"

    @tool
    def get_profile_measurements(
        self,
        profile_id: str,
        parameter: Optional[str] = None
    ) -> str:
        """
        Get detailed measurements from a specific ARGO profile.

        Args:
            profile_id: The profile ID to retrieve
            parameter: Optional parameter filter (temp, psal, pres, etc.) - case insensitive

        Returns:
            JSON string with depth, temperature, salinity, and other measurements
        """
        try:
            # Convert parameter to lowercase for database query
            param_filter = f"AND LOWER(parameter) = LOWER('{parameter}')" if parameter else ""

            query = f"""
                SELECT
                    o.depth,
                    o.parameter,
                    o.value,
                    o.qc_flag
                FROM observations o
                WHERE o.profile_id = '{profile_id}'
                    {param_filter}
                ORDER BY o.depth ASC
                LIMIT 100
            """

            result = self.db.execute(query)

            if not result or len(result) == 0:
                return f"No measurements found for profile {profile_id}"

            measurements = []
            for row in result:
                measurements.append({
                    "depth": float(row[0]),
                    "parameter": row[1],
                    "value": float(row[2]),
                    "qc_flag": row[3]
                })

            return f"Profile {profile_id}: {len(measurements)} measurements. Data: {measurements}"

        except Exception as e:
            logger.error(f"Error getting profile measurements: {e}")
            return f"Error: {str(e)}"

    @tool
    def get_statistics(
        self,
        parameter: str = "temp",
        region: Optional[str] = None
    ) -> str:
        """
        Get statistical summary of oceanographic parameters.

        Args:
            parameter: Parameter to analyze (temp, psal, pres, etc.) - case insensitive
            region: Optional region filter (equatorial, atlantic, pacific, indian)

        Returns:
            Statistical summary including average, min, max, and count
        """
        try:
            # Define region boundaries
            region_bounds = {
                "equatorial": "AND p.latitude BETWEEN -10 AND 10",
                "atlantic": "AND p.longitude BETWEEN -80 AND 20",
                "pacific": "AND (p.longitude BETWEEN -180 AND -80 OR p.longitude BETWEEN 120 AND 180)",
                "indian": "AND p.longitude BETWEEN 20 AND 120 AND p.latitude BETWEEN -60 AND 30"
            }

            region_filter = region_bounds.get(region, "") if region else ""

            query = f"""
                SELECT
                    COUNT(*) as count,
                    AVG(o.value) as avg_value,
                    MIN(o.value) as min_value,
                    MAX(o.value) as max_value,
                    STDDEV(o.value) as std_dev
                FROM observations o
                JOIN profiles p ON o.profile_id = p.profile_id
                WHERE LOWER(o.parameter) = LOWER('{parameter}')
                    AND o.value IS NOT NULL
                    AND o.value > 0
                    {region_filter}
            """

            result = self.db.execute(query)

            if not result or len(result) == 0:
                return f"No statistics available for {parameter}"

            row = result[0]
            stats = {
                "parameter": parameter,
                "region": region or "global",
                "count": row[0],
                "average": round(float(row[1]), 2) if row[1] else None,
                "min": round(float(row[2]), 2) if row[2] else None,
                "max": round(float(row[3]), 2) if row[3] else None,
                "std_dev": round(float(row[4]), 2) if row[4] else None
            }

            return f"Statistics for {parameter} ({region or 'global'}): {stats}"

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return f"Error: {str(e)}"

    @tool
    def search_by_keywords(
        self,
        query: str
    ) -> str:
        """
        Search for relevant ocean data using natural language keywords.

        This is a simple keyword-based search that helps find profiles based on
        location names, phenomena, or general terms.

        Args:
            query: Natural language search query (e.g., "warm water", "equator", "deep ocean")

        Returns:
            Relevant profile information
        """
        # Map common keywords to database queries
        keyword_map = {
            "warm": "LOWER(o.parameter) = 'temp' AND o.value > 25",
            "cold": "LOWER(o.parameter) = 'temp' AND o.value < 10",
            "deep": "o.depth > 1000",
            "shallow": "o.depth < 200",
            "equator": "p.latitude BETWEEN -10 AND 10",
            "tropical": "p.latitude BETWEEN -23.5 AND 23.5",
            "arctic": "p.latitude > 66.5",
            "antarctic": "p.latitude < -66.5"
        }

        # Simple keyword matching
        query_lower = query.lower()
        conditions = []
        for keyword, condition in keyword_map.items():
            if keyword in query_lower:
                conditions.append(condition)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        try:
            sql_query = f"""
                SELECT DISTINCT
                    p.profile_id,
                    p.latitude,
                    p.longitude,
                    p.timestamp
                FROM profiles p
                LEFT JOIN observations o ON p.profile_id = o.profile_id
                WHERE {where_clause}
                LIMIT 20
            """

            result = self.db.execute(sql_query)

            if not result or len(result) == 0:
                return f"No profiles found matching '{query}'"

            return f"Found {len(result)} profiles matching '{query}'. Use search_profiles() for detailed data."

        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return f"Error: {str(e)}"


# ============================================================================
# Main Ocean Agent
# ============================================================================

class OceanAgent:
    """
    Simplified AGNO-based conversational agent for ocean data.

    Features:
    - Direct Supabase PostgreSQL connection
    - JARVIS-like personality
    - Scientific accuracy
    - Built-in tool calling with AGNO framework
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_password: Optional[str] = None,
        model_name: str = "llama-3.3-70b-versatile",
        groq_api_key: Optional[str] = None
    ):
        """
        Initialize Ocean Agent with Supabase connection.

        Args:
            supabase_url: Supabase project URL (or DATABASE_URL env var)
            supabase_password: Supabase password
            model_name: Groq model to use
            groq_api_key: Groq API key (or GROQ_API_KEY env var)
        """
        # Get credentials from environment if not provided
        if not supabase_url:
            supabase_url = os.getenv("DATABASE_URL")
        if not supabase_password:
            supabase_password = os.getenv("SUPABASE_PASSWORD")
        if not groq_api_key:
            groq_api_key = os.getenv("GROQ_API_KEY")

        # Initialize Supabase PostgreSQL connection
        logger.info("Connecting to Supabase PostgreSQL...")
        self.db = PostgresDb(db_url=supabase_url)

        # Initialize ocean data tools
        self.tools = SupabaseOceanTools(db=self.db)

        # Initialize AGNO agent with JARVIS personality
        self.agent = Agent(
            name="Ocean Data Assistant",
            model=Groq(id=model_name, api_key=groq_api_key),
            tools=[self.tools],
            markdown=True,
            description="AI assistant specialized in oceanographic data analysis",
            instructions=[
                # CRITICAL: Force tool usage
                "YOU MUST USE THE AVAILABLE TOOLS TO FETCH REAL DATA FROM THE DATABASE.",
                "NEVER make up data or provide example responses.",
                "ALWAYS call search_profiles() or get_profile_measurements() when asked about ocean data.",
                "If a user asks for data at specific coordinates, you MUST use search_profiles() with those exact coordinates.",

                # Core personality
                "You are an expert oceanographic AI assistant, similar to JARVIS.",
                "Be conversational, professional yet friendly, and proactive in helping users explore ocean data.",
                "Address users respectfully and anticipate their needs.",

                # Communication style
                "Use natural, clear language. Start responses with acknowledgments like 'Certainly', 'Of course', 'Right away'.",
                "Be concise but thorough - provide exactly what's needed without unnecessary verbosity.",
                "When processing data, mention what you're doing: 'Searching the ARGO database...', 'Analyzing profiles...'",

                # Scientific expertise
                "You have expertise in oceanography, marine science, and ARGO float data.",
                "Ensure scientific accuracy - explain measurements, parameters (TEMP, PSAL, PRES, etc.), and quality indicators.",
                "Reference specific data when available: exact temperatures, depths, locations, and timestamps.",

                # Tool usage - EMPHASIZED
                "The tools available to you connect directly to the Supabase database.",
                "search_profiles(min_lat, max_lat, min_lon, max_lon) - Use this to find profiles in a region",
                "get_profile_measurements(profile_id) - Use this to get detailed measurements from a profile",
                "get_statistics(parameter, region) - Use this for statistical summaries",
                "search_by_keywords(query) - Use this for keyword-based searches",
                "ALWAYS use these tools - they provide REAL data from the database",

                # Proactive assistance
                "Offer relevant follow-up suggestions based on the data found.",
                "If you notice interesting patterns or anomalies, point them out.",
                "Suggest related analyses that might be valuable.",

                # Data interpretation
                "TEMP is temperature in degrees Celsius",
                "PSAL is practical salinity (unitless, typically 30-37 for ocean water)",
                "PRES is pressure in decibars (approximately equal to depth in meters)",
                "Explain measurements in context: 'warm for this depth', 'typical for tropical waters', etc.",

                # Error handling
                "If no data is found, suggest alternative searches or broader regions.",
                "Never make up data - only use actual measurements from the tools.",
                "If a tool fails, explain clearly and suggest alternatives."
            ],
            add_datetime_to_context=True
        )

        logger.info("Ocean Agent initialized successfully")

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> OceanAgentResponse:
        """
        Process user message and return response.

        Args:
            message: User's message/question
            session_id: Optional session ID for conversation continuity

        Returns:
            OceanAgentResponse with natural language response and metadata
        """
        try:
            # Use AGNO's built-in run method
            response = self.agent.run(message, stream=False)

            # Extract tool calls from response
            tool_calls = []
            if hasattr(response, 'messages'):
                for msg in response.messages:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tool_calls.extend([tc.function.name for tc in msg.tool_calls])

            # Generate follow-up suggestions based on context
            suggestions = self._generate_suggestions(message, response.content)

            return OceanAgentResponse(
                success=True,
                response=response.content,
                session_id=session_id or "default",
                tool_calls=tool_calls,
                follow_up_suggestions=suggestions,
                metadata={
                    "voice_compatible": True,
                    "model": self.agent.model.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return OceanAgentResponse(
                success=False,
                response=f"I encountered an error processing your request. Please try rephrasing your question.",
                session_id=session_id or "default",
                metadata={"error": str(e)}
            )

    def _generate_suggestions(self, user_message: str, agent_response: str) -> List[str]:
        """Generate contextual follow-up suggestions."""
        suggestions = []

        # Check message context for relevant suggestions
        msg_lower = user_message.lower()
        resp_lower = agent_response.lower()

        if "temperature" in msg_lower or "temp" in resp_lower:
            suggestions.append("What about salinity measurements in this region?")
        if "profile" in msg_lower and "found" in resp_lower:
            suggestions.append("Can you show me detailed measurements from one of these profiles?")
        if "region" in msg_lower or "area" in msg_lower:
            suggestions.append("What are the statistical averages for this area?")
        if "equator" in msg_lower or "tropical" in msg_lower:
            suggestions.append("How does this compare to other ocean regions?")

        # Default suggestions if none generated
        if not suggestions:
            suggestions = [
                "Search for profiles in a specific region",
                "Get statistics for ocean parameters",
                "Explore temperature and salinity patterns"
            ]

        return suggestions[:3]  # Limit to 3 suggestions


# ============================================================================
# Singleton instance for API
# ============================================================================

_ocean_agent_instance: Optional[OceanAgent] = None


def get_ocean_agent() -> OceanAgent:
    """Get or create singleton Ocean Agent instance."""
    global _ocean_agent_instance
    if _ocean_agent_instance is None:
        _ocean_agent_instance = OceanAgent()
    return _ocean_agent_instance
