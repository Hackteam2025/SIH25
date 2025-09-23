"""
AGNO Voice Handler for Oceanographic Queries

Integrates AGNO agent with Pipecat voice pipeline to enable voice-based
interaction with oceanographic float data.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import json
import re

from loguru import logger

# Import AGNO Agent
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "AGENT"))

from float_chat_agent import FloatChatAgent


class AGNOVoiceHandler:
    """Handler for AGNO agent integration with Pipecat voice pipeline"""

    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.agent = None
        self.mcp_server_url = mcp_server_url
        self.conversation_state = {
            "messages": [],
            "current_query": None,
            "query_context": {},
            "session_metadata": {},
            "conversation_phase": "greeting",
            "session_id": str(uuid.uuid4()),
            "start_time": datetime.now()
        }
        self.session_logger = None
        self.session_id = None

    def set_session_logger(self, logger, session_id):
        """Set the session logger for transcript tracking"""
        self.session_logger = logger
        self.session_id = session_id

    async def initialize_agent(self):
        """Initialize the AGNO agent for oceanographic queries"""
        try:
            self.agent = FloatChatAgent(
                mcp_server_url=self.mcp_server_url
            )

            logger.info(f"AGNO voice pipeline initialized for session {self.conversation_state['session_id']}")
            logger.info("AGNO agent initialized successfully for voice interaction")

        except Exception as e:
            logger.error(f"Voice pipeline init error: {type(e).__name__}")
            logger.error(f"Failed to initialize AGNO agent: {e}")
            raise

    async def process_user_input(self, message: str) -> str:
        """Process user voice input through AGNO agent"""
        start_time = datetime.now()

        try:
            if not self.agent:
                await self.initialize_agent()

            # Process message through AGNO agent
            result = await self.agent.process_query(message)

            # Update conversation state
            self.conversation_state["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": start_time
            })

            self.conversation_state["messages"].append({
                "role": "assistant",
                "content": result,
                "timestamp": datetime.now()
            })

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"Processed voice message in {processing_time:.2f}ms")
            logger.info(f"Generated response: {len(result)} chars")
            logger.info(f"AGNO response: {result}")

            # Log the assistant response to CSV if session logger available
            if self.session_logger:
                self.session_logger.log_message(
                    role="assistant",
                    content=result,
                    session_id=self.session_id,
                    room_number=None,  # Not applicable for oceanographic queries
                    confidence_score=None,
                    processing_time_ms=processing_time
                )
                logger.debug(f"[CSV] assistant: {result}")

            return result

        except Exception as e:
            # Track voice processing errors
            error_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.error(f"Voice processing error: {type(e).__name__} after {error_time:.2f}ms")
            logger.error(f"Error processing user input: {e}")

            return "I apologize, but I'm having some technical difficulties accessing the oceanographic data. Please try rephrasing your question or contact support for assistance."

    def get_session_metadata(self) -> Dict[str, Any]:
        """Get current session metadata"""
        return self.conversation_state.get("session_metadata", {})

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary for analytics"""
        return {
            "session_id": self.conversation_state["session_id"],
            "start_time": self.conversation_state["start_time"],
            "message_count": len(self.conversation_state["messages"]),
            "conversation_phase": self.conversation_state["conversation_phase"],
            "current_query": self.conversation_state.get("current_query")
        }


class AGNOVoiceProcessor:
    """Custom processor for cleaning and preparing AGNO responses for voice output"""

    def __init__(self):
        # Pattern to remove thinking tags and technical details
        self._think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)

        # Pattern to remove excessive technical jargon for voice
        self._technical_pattern = re.compile(r"\b(Profile ID|Float ID|WMO|ARGO)\s*:?\s*\d+", re.IGNORECASE)

        # Pattern to clean up data formatting for voice
        self._data_pattern = re.compile(r"```[\s\S]*?```")

        # Emoji pattern (voice doesn't need emojis)
        self._emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )

    def clean_for_voice(self, text: str) -> str:
        """Clean text for optimal voice output"""
        # Remove thinking tags
        no_think = self._think_pattern.sub(' ', text).strip()

        # Remove emojis
        no_emoji = self._emoji_pattern.sub('', no_think)

        # Remove code blocks
        no_code = self._data_pattern.sub(' [data shown on screen] ', no_emoji)

        # Simplify technical IDs for voice
        simplified = self._technical_pattern.sub('', no_code)

        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', simplified).strip()

        # Ensure it's not empty
        if not cleaned:
            return "I found some information for you. Please check your screen for the details."

        return cleaned

    def add_voice_friendly_context(self, text: str) -> str:
        """Add voice-friendly context to responses"""
        # Add natural speech patterns
        if "temperature" in text.lower() or "salinity" in text.lower():
            if not text.startswith(("Here", "I found", "The data")):
                text = f"Here's what I found: {text}"

        # Add closing phrases for natural conversation
        if not text.endswith((".", "!", "?")):
            text = f"{text}."

        if len(text) > 200:  # Long responses need guidance
            text = f"{text} Would you like me to explain any specific part in more detail?"

        return text