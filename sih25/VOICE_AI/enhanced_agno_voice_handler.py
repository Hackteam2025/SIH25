"""
Enhanced AGNO Voice Handler with Multi-Tier TTS Support

Integrates AGNO agent with multi-tier TTS fallback system for multilingual voice support.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import json
import re

from loguru import logger

# Import configuration and TTS services
from .config import VoiceAIConfig
from .tts_services import MultiTierTTSService, create_tts_config_from_env

# Import AGNO Agent
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "AGENT"))

from float_chat_agent import FloatChatAgent


class EnhancedAGNOVoiceHandler:
    """Enhanced handler for AGNO agent with multi-tier TTS support"""

    def __init__(self, voice_config: Optional[VoiceAIConfig] = None, mcp_server_url: Optional[str] = None):
        self.voice_config = voice_config or VoiceAIConfig()
        self.agent = None
        self.mcp_server_url = mcp_server_url or self.voice_config.get("MCP_SERVER_URL")

        # Initialize TTS service
        tts_config = create_tts_config_from_env()
        self.tts_service = MultiTierTTSService(tts_config)

        self.conversation_state = {
            "messages": [],
            "current_query": None,
            "query_context": {},
            "session_metadata": {
                "preferred_language": self.voice_config.get("DEFAULT_LANGUAGE", "en-US"),
                "tts_provider_used": None,
                "multilingual_enabled": True
            },
            "conversation_phase": "greeting",
            "session_id": str(uuid.uuid4()),
            "start_time": datetime.now()
        }
        self.session_logger = None
        self.session_id = None
        self.voice_processor = AGNOVoiceProcessor()

    def set_session_logger(self, logger, session_id):
        """Set the session logger for transcript tracking"""
        self.session_logger = logger
        self.session_id = session_id

    def set_preferred_language(self, language_code: str):
        """Set preferred language for TTS synthesis"""
        self.conversation_state["session_metadata"]["preferred_language"] = language_code
        logger.info(f"Language preference set to: {language_code}")

    async def initialize_agent(self):
        """Initialize the AGNO agent for oceanographic queries"""
        try:
            self.agent = FloatChatAgent(
                mcp_server_url=self.mcp_server_url
            )

            # Log TTS service status
            tts_status = self.tts_service.get_service_status()
            logger.info(f"TTS Services Status: {tts_status}")

            logger.info(f"Enhanced AGNO voice pipeline initialized for session {self.conversation_state['session_id']}")
            logger.info("AGNO agent with multi-tier TTS initialized successfully")

        except Exception as e:
            logger.error(f"Enhanced voice pipeline init error: {type(e).__name__}")
            logger.error(f"Failed to initialize enhanced AGNO agent: {e}")
            raise

    async def process_user_input(self, message: str, detect_language: bool = True) -> str:
        """Process user voice input through AGNO agent with language detection"""
        start_time = datetime.now()

        try:
            if not self.agent:
                await self.initialize_agent()

            # Detect language if enabled
            detected_language = None
            if detect_language:
                detected_language = self._detect_language(message)
                if detected_language and detected_language != self.conversation_state["session_metadata"]["preferred_language"]:
                    logger.info(f"Language detected: {detected_language}")
                    self.conversation_state["session_metadata"]["preferred_language"] = detected_language

            # Process message through AGNO agent
            result = await self.agent.process_query(message)

            # Clean response for voice output
            voice_friendly_result = self.voice_processor.clean_for_voice(result)
            voice_friendly_result = self.voice_processor.add_voice_friendly_context(voice_friendly_result)

            # Apply language-specific response modifications
            voice_friendly_result = self._adapt_response_for_language(
                voice_friendly_result,
                self.conversation_state["session_metadata"]["preferred_language"]
            )

            # Update conversation state
            self.conversation_state["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": start_time,
                "detected_language": detected_language
            })

            self.conversation_state["messages"].append({
                "role": "assistant",
                "content": voice_friendly_result,
                "timestamp": datetime.now(),
                "original_content": result,
                "target_language": self.conversation_state["session_metadata"]["preferred_language"]
            })

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"Processed voice message in {processing_time:.2f}ms")
            logger.info(f"Generated response: {len(voice_friendly_result)} chars (original: {len(result)} chars)")
            logger.info(f"Enhanced AGNO response: {voice_friendly_result}")

            # Log the assistant response to CSV if session logger available
            if self.session_logger:
                self.session_logger.log_message(
                    role="assistant",
                    content=voice_friendly_result,
                    session_id=self.session_id,
                    room_number=None,
                    confidence_score=None,
                    processing_time_ms=processing_time
                )
                logger.debug(f"[CSV] assistant: {voice_friendly_result}")

            return voice_friendly_result

        except Exception as e:
            # Track voice processing errors
            error_time = (datetime.now() - start_time).total_seconds() * 1000

            logger.error(f"Enhanced voice processing error: {type(e).__name__} after {error_time:.2f}ms")
            logger.error(f"Error processing user input: {e}")

            # Return language-appropriate error message
            return self._get_error_message(self.conversation_state["session_metadata"]["preferred_language"])

    async def synthesize_speech(self, text: str) -> Optional[bytes]:
        """Synthesize speech using multi-tier TTS with language preference"""
        try:
            preferred_language = self.conversation_state["session_metadata"]["preferred_language"]

            # Log TTS attempt
            logger.info(f"Synthesizing speech in {preferred_language}: {text[:100]}...")

            # Use multi-tier TTS service
            audio_data = await self.tts_service.synthesize(text, preferred_language)

            if audio_data:
                # Update session metadata with successful TTS provider
                tts_status = self.tts_service.get_service_status()
                self.conversation_state["session_metadata"]["tts_provider_used"] = tts_status.get("fallback_order", ["unknown"])[0]

                logger.info(f"Speech synthesis successful, audio size: {len(audio_data)} bytes")
                return audio_data
            else:
                logger.error("All TTS providers failed")
                return None

        except Exception as e:
            logger.error(f"Speech synthesis error: {e}")
            return None

    def _detect_language(self, text: str) -> Optional[str]:
        """Simple language detection based on text patterns"""
        # Basic Hindi detection
        hindi_chars = re.search(r'[\u0900-\u097F]', text)
        if hindi_chars:
            return "hi-IN"

        # Add more language detection logic as needed
        return None

    def _adapt_response_for_language(self, text: str, language_code: str) -> str:
        """Adapt response content for specific languages"""
        if language_code.startswith('hi'):
            # For Hindi users, add cultural context
            if "ocean" in text.lower() or "data" in text.lower():
                if not any(word in text.lower() for word in ["मैं", "यह", "डेटा"]):
                    # Add transliterated context for Hindi speakers
                    text = f"Ocean data ke bare mein: {text}"

        return text

    def _get_error_message(self, language_code: str) -> str:
        """Get error message in appropriate language"""
        if language_code.startswith('hi'):
            return "माफ़ करें, डेटा एक्सेस करने में कुछ तकनीकी कठिनाई हो रही है। कृपया अपना प्रश्न दोबारा पूछें।"
        else:
            return "I apologize, but I'm having some technical difficulties accessing the oceanographic data. Please try rephrasing your question."

    def get_session_metadata(self) -> Dict[str, Any]:
        """Get current session metadata with TTS information"""
        metadata = self.conversation_state.get("session_metadata", {})
        metadata["tts_service_status"] = self.tts_service.get_service_status()
        return metadata

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get enhanced conversation summary with multilingual analytics"""
        languages_used = set()
        tts_providers_used = set()

        for message in self.conversation_state["messages"]:
            if message.get("detected_language"):
                languages_used.add(message["detected_language"])
            if message.get("target_language"):
                languages_used.add(message["target_language"])

        return {
            "session_id": self.conversation_state["session_id"],
            "start_time": self.conversation_state["start_time"],
            "message_count": len(self.conversation_state["messages"]),
            "conversation_phase": self.conversation_state["conversation_phase"],
            "current_query": self.conversation_state.get("current_query"),
            "languages_used": list(languages_used),
            "tts_provider_used": self.conversation_state["session_metadata"].get("tts_provider_used"),
            "multilingual_session": len(languages_used) > 1
        }


class AGNOVoiceProcessor:
    """Enhanced processor for cleaning and preparing AGNO responses for multilingual voice output"""

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
        """Clean text for optimal voice output with multilingual support"""
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
        """Add voice-friendly context to responses with multilingual awareness"""
        # Add natural speech patterns
        if "temperature" in text.lower() or "salinity" in text.lower():
            if not text.startswith(("Here", "I found", "The data", "यहाँ", "मैंने")):
                text = f"Here's what I found: {text}"

        # Add closing phrases for natural conversation
        if not text.endswith((".", "!", "?", "।")):
            text = f"{text}."

        # Limit response length for voice
        max_length = 250  # Slightly longer for multilingual content
        if len(text) > max_length:
            # Try to find a good break point
            sentences = re.split(r'[.!?।]', text)
            trimmed = ""
            for sentence in sentences:
                if len(trimmed + sentence) <= max_length - 50:
                    trimmed += sentence + ". "
                else:
                    break

            if trimmed:
                text = trimmed.strip() + " Would you like me to explain more?"
            else:
                text = text[:max_length-50] + "... Would you like me to continue?"

        return text