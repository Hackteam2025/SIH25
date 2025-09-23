"""
Oceanographic Voice AI Pipeline

Main voice pipeline for AGNO-based oceanographic data queries.
Replaces the LLM block in the standard Pipecat pipeline with AGNO agent integration.

Pipeline: Silero VAD -> STT -> AGNO Agent -> TTS -> Audio Output
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import json
import re
from datetime import datetime

import aiohttp
from dotenv import load_dotenv
from loguru import logger

# Pipecat imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
from pipecat.services.soniox.stt import SonioxSTTService, SonioxInputParams
from pipecat.transcriptions.language import Language
from pipecat.frames.frames import TextFrame, LLMFullResponseStartFrame, LLMFullResponseEndFrame

# Try importing enhanced TTS (using the hotel concierge pattern)
try:
    from sih25.VOICE.elevenlabs_fix import get_robust_tts_service
    ENHANCED_TTS_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced TTS not available, falling back to Deepgram TTS")
    ENHANCED_TTS_AVAILABLE = False

# Import AGNO voice handler
from agno_voice_handler import AGNOVoiceHandler, AGNOVoiceProcessor

# Import session transcript logger from hotel concierge if available
try:
    from sih25.VOICE.session_transcript_logger import SessionTranscriptLogger
    SESSION_LOGGING_AVAILABLE = True
except ImportError:
    logger.warning("Session transcript logging not available")
    SESSION_LOGGING_AVAILABLE = False

# Add parent directory to path for agent imports
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

# Load environment variables
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded .env file from {dotenv_path}")
else:
    logger.warning(f".env file not found at {dotenv_path}")

# Configure logging
logger.add(
    project_root / "logs" / "voice_ai_{time}.log",
    rotation="1 day",
    retention="7 days",
    format="{time} | {level} | {name}:{line} | {message}"
)


class AGNOLLMService:
    """
    Custom LLM service that integrates AGNO agent with Pipecat pipeline.
    Replaces the traditional LLM block with AGNO agent processing.
    """

    def __init__(self, agno_handler: AGNOVoiceHandler, **kwargs):
        self.agno_handler = agno_handler
        self.voice_processor = AGNOVoiceProcessor()
        self._push_frame_callback = None

    def set_push_frame_callback(self, callback):
        """Set the callback for pushing frames to the pipeline"""
        self._push_frame_callback = callback

    async def push_frame(self, frame):
        """Push frame to the pipeline if callback is available"""
        if self._push_frame_callback:
            await self._push_frame_callback(frame)

    async def process_context(self, context):
        """Process user input through AGNO agent instead of traditional LLM"""
        try:
            # Get the user message from context
            messages = context.get_messages() if hasattr(context, 'get_messages') else []

            if messages:
                # Extract the last user message
                user_messages = [msg for msg in messages if msg.get("role") == "user"]
                if user_messages:
                    user_input = user_messages[-1].get("content", "")

                    # Process through AGNO agent
                    agno_response = await self.agno_handler.process_user_input(user_input)

                    # Clean response for voice output
                    clean_response = self.voice_processor.clean_for_voice(agno_response)
                    voice_friendly_response = self.voice_processor.add_voice_friendly_context(clean_response)

                    if voice_friendly_response:
                        # Create response frames
                        await self.push_frame(LLMFullResponseStartFrame())
                        await self.push_frame(TextFrame(voice_friendly_response))
                        await self.push_frame(LLMFullResponseEndFrame())
                        return

            # Fallback response
            await self.push_frame(LLMFullResponseStartFrame())
            await self.push_frame(TextFrame("Hello! I'm your oceanographic data assistant. Ask me about temperature profiles, salinity measurements, or float locations."))
            await self.push_frame(LLMFullResponseEndFrame())

        except Exception as e:
            logger.error(f"Error in AGNO LLM service: {e}")
            await self.push_frame(LLMFullResponseStartFrame())
            await self.push_frame(TextFrame("I apologize for the technical difficulty. Could you please rephrase your oceanographic data question?"))
            await self.push_frame(LLMFullResponseEndFrame())

    def create_context_aggregator(self, context):
        """Create a context aggregator for the pipeline"""
        # Simple aggregator that passes through to our AGNO processing
        class AGNOContextAggregator:
            def __init__(self, agno_service, context):
                self.agno_service = agno_service
                self.context = context

            def user(self):
                return self

            def assistant(self):
                return self

            async def process_frame(self, frame):
                # Process frames and update context
                if hasattr(frame, 'text'):
                    # Add user message to context
                    self.context.add_message({"role": "user", "content": frame.text})
                    # Process through AGNO
                    await self.agno_service.process_context(self.context)

        return AGNOContextAggregator(self, context)


async def initialize_transport():
    """Initialize audio transport (Daily or Local)"""
    use_daily = os.getenv("DAILY_API_KEY")

    if use_daily:
        logger.info("Using Daily transport for WebRTC connection")
        # Would need Daily room configuration here
        # For now, falling back to local
        logger.warning("Daily transport configuration needed - using local transport")
        use_daily = False

    if not use_daily:
        logger.info("Using local microphone and speakers")
        transport = LocalAudioTransport(
            params=LocalAudioTransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            )
        )

        # Event handlers to prevent bot from hearing itself
        @transport.event_handler("bot_started_speaking")
        async def on_bot_started_speaking(transport):
            logger.debug("Bot started speaking, pausing audio input")
            transport.input().pause(deep=False)

        @transport.event_handler("bot_stopped_speaking")
        async def on_bot_stopped_speaking(transport):
            logger.debug("Bot stopped speaking, resuming audio input")
            transport.input().unpause()

    return transport


def initialize_stt():
    """Initialize Speech-to-Text service"""
    soniox_key = os.getenv("SONIOX_API_KEY")
    if soniox_key:
        logger.info("Using Soniox STT service")
        return SonioxSTTService(
            api_key=soniox_key,
            params=SonioxInputParams(
                language_hints=[Language.EN],
            ),
        )
    else:
        logger.info("Using Deepgram STT service")
        return DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))


def initialize_tts():
    """Initialize Text-to-Speech service"""
    if ENHANCED_TTS_AVAILABLE:
        logger.info("Initializing enhanced ElevenLabs TTS service")
        return get_robust_tts_service()
    else:
        logger.info("Using Deepgram TTS service")
        return DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"))


async def main():
    """Main function to set up and run the oceanographic voice AI pipeline"""

    try:
        # Initialize transport
        transport = await initialize_transport()

        # Initialize STT service
        stt = initialize_stt()

        # Initialize TTS service
        tts = initialize_tts()

        # Initialize AGNO voice handler
        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        agno_handler = AGNOVoiceHandler(mcp_server_url=mcp_server_url)
        await agno_handler.initialize_agent()

        # Initialize session logging if available
        session_id = str(uuid.uuid4())
        session_logger = None

        if SESSION_LOGGING_AVAILABLE:
            session_logger = SessionTranscriptLogger()
            session_logger.start_session(session_id)
            agno_handler.set_session_logger(session_logger, session_id)
            logger.info(f"Session started with ID: {session_id}")
            logger.info(f"Transcript logging to: {session_logger.get_filepath()}")

        # Initialize transcript processor
        transcript = TranscriptProcessor()

        # Initialize AGNO LLM service
        agno_llm_service = AGNOLLMService(agno_handler=agno_handler)

        # Set up context
        context = OpenAILLMContext()
        context_aggregator = agno_llm_service.create_context_aggregator(context)

        # Build pipeline components
        pipeline_components = [
            transport.input(),
            stt,
            transcript.user(),           # Capture user transcripts
            context_aggregator.user(),
            agno_llm_service,
            tts,
            transport.output(),
            transcript.assistant(),      # Capture assistant transcripts
            context_aggregator.assistant(),
        ]

        pipeline = Pipeline(pipeline_components)
        logger.info("AGNO voice AI pipeline created successfully")

        task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

        # Transcript event handler
        if SESSION_LOGGING_AVAILABLE and session_logger:
            @transcript.event_handler("on_transcript_update")
            async def handle_transcript_update(processor, frame):
                """Save transcripts to session CSV file"""
                try:
                    for message in frame.messages:
                        if message.role == "user":
                            session_logger.log_message(
                                role=message.role,
                                content=message.content,
                                session_id=session_id,
                                room_number=None,  # Not applicable for oceanographic queries
                                confidence_score=getattr(message, 'confidence', None),
                                processing_time_ms=getattr(message, 'processing_time', None)
                            )
                            logger.debug(f"[CSV] {message.role}: {message.content}")
                except Exception as e:
                    logger.error(f"Failed to log transcript: {e}")

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)

    except asyncio.CancelledError:
        logger.info("Voice AI session was cancelled")
    except Exception as e:
        logger.error(f"Error in voice AI pipeline: {e}")
        raise
    finally:
        # Clean up
        logger.info("Cleaning up voice AI session")

        # Close session transcript logger
        if SESSION_LOGGING_AVAILABLE and 'session_logger' in locals() and session_logger:
            session_logger.end_session()
            logger.info(f"Session {session_id} transcript saved to: {session_logger.get_filepath()}")

        logger.info("Voice AI session completed")


if __name__ == "__main__":
    asyncio.run(main())