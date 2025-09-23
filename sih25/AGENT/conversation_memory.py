"""
Conversation Memory for AGNO Agent

Manages conversation context, user preferences, and session history
for multi-turn dialogues about oceanographic data.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    timestamp: datetime
    user_message: str
    agent_response: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    context_used: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPreferences:
    """User preferences for data presentation and analysis."""
    preferred_units: Dict[str, str] = field(default_factory=dict)  # e.g., {"temperature": "celsius", "depth": "meters"}
    default_map_region: Optional[Dict[str, float]] = None  # {"lat_min": ..., "lat_max": ..., etc.}
    data_quality_threshold: str = "good"  # "any", "good", "best"
    max_results_per_query: int = 100
    preferred_time_format: str = "iso"  # "iso", "human", "relative"
    scientific_detail_level: str = "moderate"  # "basic", "moderate", "detailed"


class ConversationMemory:
    """
    Manages conversation state and memory for the AGNO agent.

    Provides:
    - Multi-turn conversation context
    - User preference tracking
    - Session management
    - Query history and patterns
    """

    def __init__(self, session_id: str, max_turns: int = 50):
        """
        Initialize conversation memory.

        Args:
            session_id: Unique identifier for this conversation session
            max_turns: Maximum number of turns to keep in memory
        """
        self.session_id = session_id
        self.max_turns = max_turns
        self.conversation_turns: List[ConversationTurn] = []
        self.user_preferences = UserPreferences()
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        self.current_context: Dict[str, Any] = {}
        self.logger = logger

    def add_turn(
        self,
        user_message: str,
        agent_response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        context_used: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a new conversation turn.

        Args:
            user_message: User's input message
            agent_response: Agent's response
            tool_calls: List of tool calls made during this turn
            context_used: Context information used for this turn
            metadata: Additional metadata about the turn
        """
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_message=user_message,
            agent_response=agent_response,
            tool_calls=tool_calls or [],
            context_used=context_used or {},
            metadata=metadata or {}
        )

        self.conversation_turns.append(turn)
        self.last_activity = datetime.now()

        # Trim conversation if too long
        if len(self.conversation_turns) > self.max_turns:
            self.conversation_turns = self.conversation_turns[-self.max_turns:]

        # Update current context
        self._update_current_context(turn)

    def get_recent_context(self, num_turns: int = 3) -> Dict[str, Any]:
        """
        Get context from recent conversation turns.

        Args:
            num_turns: Number of recent turns to include

        Returns:
            Context dictionary with recent conversation information
        """
        recent_turns = self.conversation_turns[-num_turns:] if self.conversation_turns else []

        context = {
            "session_id": self.session_id,
            "turn_count": len(self.conversation_turns),
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "recent_topics": self._extract_recent_topics(recent_turns),
            "recent_locations": self._extract_recent_locations(recent_turns),
            "recent_time_periods": self._extract_recent_time_periods(recent_turns),
            "user_preferences": self._serialize_preferences(),
            "current_context": self.current_context
        }

        # Add summaries of recent turns
        if recent_turns:
            context["recent_conversation"] = [
                {
                    "user": turn.user_message[:100] + "..." if len(turn.user_message) > 100 else turn.user_message,
                    "agent": turn.agent_response[:100] + "..." if len(turn.agent_response) > 100 else turn.agent_response,
                    "timestamp": turn.timestamp.isoformat(),
                    "had_tool_calls": len(turn.tool_calls) > 0
                }
                for turn in recent_turns
            ]

        return context

    def update_preferences(self, preference_updates: Dict[str, Any]):
        """
        Update user preferences based on conversation patterns.

        Args:
            preference_updates: Dictionary of preference updates
        """
        for key, value in preference_updates.items():
            if hasattr(self.user_preferences, key):
                setattr(self.user_preferences, key, value)
            else:
                self.logger.warning(f"Unknown preference key: {key}")

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the entire conversation.

        Returns:
            Summary dictionary with key conversation metrics
        """
        if not self.conversation_turns:
            return {"status": "no_conversation"}

        total_tool_calls = sum(len(turn.tool_calls) for turn in self.conversation_turns)
        unique_topics = set()
        unique_locations = set()

        for turn in self.conversation_turns:
            topics = self._extract_topics_from_turn(turn)
            locations = self._extract_locations_from_turn(turn)
            unique_topics.update(topics)
            unique_locations.update(locations)

        return {
            "session_id": self.session_id,
            "total_turns": len(self.conversation_turns),
            "total_tool_calls": total_tool_calls,
            "session_duration_minutes": (datetime.now() - self.session_start).total_seconds() / 60,
            "unique_topics_discussed": list(unique_topics),
            "unique_locations_queried": list(unique_locations),
            "avg_tools_per_turn": total_tool_calls / len(self.conversation_turns) if self.conversation_turns else 0,
            "user_preferences": self._serialize_preferences(),
            "last_activity": self.last_activity.isoformat()
        }

    def _update_current_context(self, turn: ConversationTurn):
        """Update current context based on the latest turn."""
        # Extract and store current geographic focus
        locations = self._extract_locations_from_turn(turn)
        if locations:
            self.current_context["current_region"] = locations[-1]  # Most recent location

        # Extract and store current time focus
        time_periods = self._extract_time_periods_from_turn(turn)
        if time_periods:
            self.current_context["current_time_period"] = time_periods[-1]

        # Extract and store current parameters of interest
        parameters = self._extract_parameters_from_turn(turn)
        if parameters:
            self.current_context["current_parameters"] = parameters

        # Update last query type
        if turn.tool_calls:
            last_tool = turn.tool_calls[-1]
            self.current_context["last_tool_used"] = last_tool.get("tool_name")

    def _extract_recent_topics(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract topics from recent conversation turns."""
        topics = []
        for turn in turns:
            topics.extend(self._extract_topics_from_turn(turn))
        return list(set(topics))

    def _extract_recent_locations(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract geographic locations from recent turns."""
        locations = []
        for turn in turns:
            locations.extend(self._extract_locations_from_turn(turn))
        return list(set(locations))

    def _extract_recent_time_periods(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract time periods from recent turns."""
        time_periods = []
        for turn in turns:
            time_periods.extend(self._extract_time_periods_from_turn(turn))
        return list(set(time_periods))

    def _extract_topics_from_turn(self, turn: ConversationTurn) -> List[str]:
        """Extract topics from a conversation turn."""
        topics = []
        message_lower = turn.user_message.lower()

        # Oceanographic parameters
        if any(param in message_lower for param in ["temperature", "temp"]):
            topics.append("temperature")
        if any(param in message_lower for param in ["salinity", "salt"]):
            topics.append("salinity")
        if any(param in message_lower for param in ["oxygen", "doxy"]):
            topics.append("dissolved_oxygen")
        if any(param in message_lower for param in ["chlorophyll", "chla"]):
            topics.append("chlorophyll")
        if any(param in message_lower for param in ["pressure", "depth"]):
            topics.append("pressure_depth")

        # Analysis types
        if any(analysis in message_lower for analysis in ["profile", "vertical"]):
            topics.append("vertical_profiles")
        if any(analysis in message_lower for analysis in ["float", "instrument"]):
            topics.append("float_analysis")
        if any(analysis in message_lower for analysis in ["statistics", "stats", "mean", "average"]):
            topics.append("statistical_analysis")

        return topics

    def _extract_locations_from_turn(self, turn: ConversationTurn) -> List[str]:
        """Extract geographic references from a turn."""
        locations = []
        message_lower = turn.user_message.lower()

        # Ocean regions
        ocean_regions = [
            "atlantic", "pacific", "indian", "arctic", "southern",
            "mediterranean", "caribbean", "gulf", "equator", "equatorial",
            "north", "south", "east", "west", "tropical", "subtropical"
        ]

        for region in ocean_regions:
            if region in message_lower:
                locations.append(region)

        # Check tool calls for coordinate data
        for tool_call in turn.tool_calls:
            if "parameters" in tool_call:
                params = tool_call["parameters"]
                if any(coord in params for coord in ["lat", "lon", "latitude", "longitude"]):
                    locations.append("coordinates_specified")

        return locations

    def _extract_time_periods_from_turn(self, turn: ConversationTurn) -> List[str]:
        """Extract temporal references from a turn."""
        time_periods = []
        message_lower = turn.user_message.lower()

        # Temporal keywords
        temporal_terms = [
            "recent", "latest", "current", "today", "yesterday",
            "last week", "last month", "last year",
            "winter", "spring", "summer", "fall", "autumn",
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]

        for term in temporal_terms:
            if term in message_lower:
                time_periods.append(term)

        return time_periods

    def _extract_parameters_from_turn(self, turn: ConversationTurn) -> List[str]:
        """Extract oceanographic parameters from a turn."""
        parameters = []
        message_lower = turn.user_message.lower()

        parameter_mapping = {
            "temperature": ["TEMP"],
            "salinity": ["PSAL"],
            "pressure": ["PRES"],
            "oxygen": ["DOXY"],
            "chlorophyll": ["CHLA"]
        }

        for param_name, param_codes in parameter_mapping.items():
            if param_name in message_lower:
                parameters.extend(param_codes)

        return parameters

    def _serialize_preferences(self) -> Dict[str, Any]:
        """Serialize user preferences to dictionary."""
        return {
            "preferred_units": self.user_preferences.preferred_units,
            "default_map_region": self.user_preferences.default_map_region,
            "data_quality_threshold": self.user_preferences.data_quality_threshold,
            "max_results_per_query": self.user_preferences.max_results_per_query,
            "preferred_time_format": self.user_preferences.preferred_time_format,
            "scientific_detail_level": self.user_preferences.scientific_detail_level
        }

    def is_session_expired(self, timeout_minutes: int = 30) -> bool:
        """
        Check if the session has expired based on inactivity.

        Args:
            timeout_minutes: Minutes of inactivity before expiration

        Returns:
            True if session is expired
        """
        return (datetime.now() - self.last_activity) > timedelta(minutes=timeout_minutes)