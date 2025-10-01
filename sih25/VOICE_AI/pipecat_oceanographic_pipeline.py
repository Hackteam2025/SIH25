"""
Pipecat-Native Oceanographic Voice AI Pipeline

Pure Pipecat implementation with native MCP client integration.
Replaces AGNO-based approach with streamlined Pipecat LLM + MCP architecture.

Pipeline: Silero VAD -> STT -> LLM (with MCP tools) -> TTS -> Audio Output
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

# Pipecat core imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
from pipecat.services.soniox.stt import SonioxSTTService, SonioxInputParams
from pipecat.transcriptions.language import Language

# Pipecat LLM and MCP imports
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.mcp_service import MCPService

# Session logging
from sih25.VOICE_AI.session_transcript_logger import SessionTranscriptLogger

# Add parent directory to path
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
    project_root / "logs" / "pipecat_voice_{time}.log",
    rotation="1 day",
    retention="7 days",
    format="{time} | {level} | {name}:{line} | {message}"
)


def create_oceanographic_system_prompt() -> str:
    """
    Create comprehensive system prompt with ARGO oceanographic expertise.
    Based on scientific_context.py from the AGENT module.
    """
    return """You are FloatChat, an expert oceanographic data assistant specializing in ARGO float measurements. You have deep knowledge of ocean science and help users discover and understand ocean data through natural conversation.

## Your Expertise

### ARGO Parameters:
- **TEMP** (Temperature, °C): In-situ seawater temperature (-2°C to 35°C). Primary indicator of ocean thermal structure.
- **PSAL** (Practical Salinity, PSU): Salinity from conductivity (30-37 PSU). Key tracer for water masses.
- **PRES** (Pressure, dbar): Water pressure ≈ depth in meters. Determines depth level for measurements.
- **DOXY** (Dissolved Oxygen, μmol/kg): Critical for marine ecosystem health (0-400 μmol/kg).
- **CHLA** (Chlorophyll-a, mg/m³): Phytoplankton biomass indicator (0-10 mg/m³).

### Quality Control Flags:
- **1**: Good data (high reliability) - suitable for all scientific applications
- **2**: Probably good data - acceptable for most applications
- **3**: Bad but potentially correctable - use only if corrected
- **4**: Bad data - do not use for analysis
- **8**: Estimated value - use with understanding of estimation method

### Ocean Regions:
- **Equatorial** (-5° to 5°): High temperature, strong currents, El Niño effects
- **Tropical** (-23.5° to 23.5°): Warm surface waters, strong stratification
- **Subtropical** (23.5°-40°, -40° to -23.5°): Moderate temps, high surface salinity
- **Subpolar** (40°-60°, -60° to -40°): Cold waters, deep mixing, nutrient-rich
- **Polar** (60°-90°, -90° to -60°): Very cold, seasonal ice, unique ecosystems

## Your Behavior:
- Always provide scientific context and explain data significance
- Use MCP tools to access real ARGO data - never make up data
- Suggest follow-up questions to encourage exploration
- Explain quality control concepts when relevant
- Be conversational but maintain scientific rigor
- Help users understand oceanographic processes behind the numbers

## Available Tools:
You have access to MCP tools for ARGO data including:
- list_profiles: Find profiles by location and time
- search_floats_near: Locate floats near coordinates
- get_profile_statistics: Get detailed profile data
- semantic_search: Find similar profiles using AI

Always ground your responses in actual data retrieved through these tools."""


def create_voice_optimized_instructions() -> str:
    """Create instructions specifically for voice interaction."""
    return """
## Voice Interaction Guidelines:
- Keep responses conversational and under 30 seconds when spoken
- Use simple, clear language avoiding jargon
- Break complex information into digestible chunks
- Always acknowledge what the user is asking before diving into data
- End responses with engaging follow-up questions
- Use natural speech patterns: "Let me check that for you..." or "That's interesting..."
- When presenting numbers, round to 2 decimal places and use descriptive context
- Example: "I found 15 profiles showing temperatures around 18.5 degrees Celsius"
"""


async def initialize_transport():
    """Initialize audio transport with optimized VAD settings."""
    logger.info("Initializing local audio transport with Silero VAD")

    transport = LocalAudioTransport(
        params=LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                threshold=0.5,  # Optimized for oceanographic discussions
                min_volume=0.6
            ),
        )
    )

    # Prevent bot from hearing itself
    @transport.event_handler("bot_started_speaking")
    async def on_bot_started_speaking(transport):
        logger.debug("Bot speaking - pausing audio input")
        transport.input().pause(deep=False)

    @transport.event_handler("bot_stopped_speaking")
    async def on_bot_stopped_speaking(transport):
        logger.debug("Bot finished - resuming audio input")
        transport.input().unpause()

    return transport


def initialize_stt():
    """Initialize Speech-to-Text service with oceanographic optimization."""
    soniox_key = os.getenv("SONIOX_API_KEY")
    if soniox_key:
        logger.info("Using Soniox STT with English language hints")
        return SonioxSTTService(
            api_key=soniox_key,
            params=SonioxInputParams(
                language_hints=[Language.EN],
                # Add oceanographic vocabulary hints if supported
            ),
        )
    else:
        logger.info("Using Deepgram STT service")
        return DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            # Add model optimization for scientific content if available
        )


def initialize_llm():
    """Initialize LLM service with oceanographic expertise."""
    # Try Groq first for faster inference
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        logger.info("Using Groq LLM for fast inference")
        return GroqLLMService(
            api_key=groq_key,
            model="llama-3.1-70b-versatile",  # Good balance of speed and capability
            system_message=create_oceanographic_system_prompt() + create_voice_optimized_instructions()
        )

    # Fallback to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        logger.info("Using OpenAI LLM")
        return OpenAILLMService(
            api_key=openai_key,
            model="gpt-4o-mini",  # Cost-effective for voice conversations
            system_message=create_oceanographic_system_prompt() + create_voice_optimized_instructions()
        )

    raise ValueError("No LLM API key configured. Set GROQ_API_KEY or OPENAI_API_KEY")


def initialize_tts():
    """Initialize Text-to-Speech with natural voice."""
    sarvam_key = os.getenv("SARVAM_API_KEY")
    if sarvam_key:
        logger.info("Using Sarvam TTS with natural voice")
        return SarvamTTSService(
            api_key=sarvam_key,
            voice_id="karun",  # Natural sounding voice
            # Add voice optimization parameters if available
        )
    else:
        logger.error("No TTS service configured. Please set SARVAM_API_KEY")
        raise ValueError("TTS service not configured")


async def initialize_mcp_services():
    """Initialize MCP services for ARGO data access and Supabase."""
    mcp_services = []

    # Custom ARGO MCP Server
    argo_mcp_url = os.getenv("ARGO_MCP_SERVER_URL", "http://localhost:8000")
    try:
        argo_mcp = MCPService(
            server_url=argo_mcp_url,
            server_name="argo_data_server"
        )
        await argo_mcp.initialize()
        mcp_services.append(argo_mcp)
        logger.info(f"Connected to ARGO MCP server at {argo_mcp_url}")
    except Exception as e:
        logger.warning(f"Could not connect to ARGO MCP server: {e}")

    # Supabase MCP Server (if configured)
    supabase_mcp_config = os.getenv("SUPABASE_MCP_CONFIG")
    if supabase_mcp_config:
        try:
            # This would be configured based on Supabase MCP server setup
            # Implementation depends on how Supabase MCP is deployed
            logger.info("Supabase MCP configuration detected but not yet implemented")
        except Exception as e:
            logger.warning(f"Could not connect to Supabase MCP server: {e}")

    return mcp_services


async def main():
    """Main function to run the Pipecat-native oceanographic voice AI."""

    session_id = str(uuid.uuid4())
    session_logger = None

    try:
        logger.info("Starting Pipecat Oceanographic Voice AI Pipeline")

        # Initialize all components
        transport = await initialize_transport()
        stt = initialize_stt()
        llm = initialize_llm()
        tts = initialize_tts()

        # Initialize MCP services
        mcp_services = await initialize_mcp_services()

        # Add MCP services to LLM if available
        for mcp_service in mcp_services:
            llm.add_mcp_service(mcp_service)
            logger.info(f"Added MCP service: {mcp_service.server_name}")

        # Initialize session logging
        session_logger = SessionTranscriptLogger()
        session_logger.start_session(session_id)
        logger.info(f"Session started: {session_id}")

        # Initialize transcript processor
        transcript = TranscriptProcessor()

        # Set up context for conversation continuity
        context = OpenAILLMContext(
            messages=[
                {
                    "role": "system",
                    "content": create_oceanographic_system_prompt() + create_voice_optimized_instructions()
                },
                {
                    "role": "assistant",
                    "content": "Hello! I'm FloatChat, your oceanographic data assistant. I can help you explore ARGO float measurements from around the world's oceans. What would you like to discover today?"
                }
            ]
        )

        # Build the pipeline
        pipeline_components = [
            transport.input(),           # Audio input
            stt,                        # Speech-to-Text
            transcript.user(),          # Log user speech
            context.user(),             # Add to conversation context
            llm,                        # LLM with MCP tools
            tts,                        # Text-to-Speech
            transport.output(),         # Audio output
            transcript.assistant(),     # Log assistant speech
            context.assistant(),        # Add to conversation context
        ]

        # Create and configure pipeline
        pipeline = Pipeline(pipeline_components)
        logger.info("Pipecat oceanographic pipeline created successfully")

        # Create task with interruption support
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True
            )
        )

        # Run the pipeline
        runner = PipelineRunner()
        logger.info("Starting voice AI conversation...")
        await runner.run(task)

    except asyncio.CancelledError:
        logger.info("Voice AI session was cancelled by user")
    except Exception as e:
        logger.error(f"Error in Pipecat voice AI pipeline: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Cleaning up Pipecat voice AI session")

        # Close MCP services
        for mcp_service in mcp_services if 'mcp_services' in locals() else []:
            try:
                await mcp_service.close()
                logger.info(f"Closed MCP service: {mcp_service.server_name}")
            except Exception as e:
                logger.warning(f"Error closing MCP service: {e}")

        # Close session logger
        if session_logger:
            session_logger.end_session()
            logger.info(f"Session {session_id} logged and closed")

        logger.info("Pipecat voice AI session completed")


if __name__ == "__main__":
    asyncio.run(main())