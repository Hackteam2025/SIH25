"""
Pipecat-Native Oceanographic Voice AI Pipeline

Direct Pipecat implementation with native MCP client integration.
Replaces AGNO-based approach with streamlined Pipecat LLM + MCP architecture.

Pipeline: Silero VAD -> STT -> LLM (with MCP tools) -> TTS -> Audio Output
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
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
from mcp.client.session_group import StdioServerParameters
from pipecat.services.mcp_service import MCPClient
from mcp.client.session_group import StreamableHttpParameters
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.aggregators.llm_response import (
    LLMUserAggregatorParams,
    LLMAssistantAggregatorParams,
)




# Add parent directory to path for agent imports
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

# Load environment variables
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded .env file from {dotenv_path}")
else:
    load_dotenv()  # Fallback to default .env loading
    logger.info("Loaded .env file from default location")

# Ensure logs directory exists
logs_dir = project_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
logger.add(
    logs_dir / "pipecat_voice_{time}.log",
    rotation="1 day",
    retention="7 days",
    format="{time} | {level} | {name}:{line} | {message}",
    level="INFO"
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

## Voice Interaction Guidelines:
- Keep responses conversational and under 30 seconds when spoken
- Use simple, clear language avoiding jargon
- Always acknowledge what the user is asking before diving into data
- End responses with engaging follow-up questions
- When presenting numbers, round to 2 decimal places and use descriptive context
- Example: "I found 15 profiles showing temperatures around 18.5 degrees Celsius"

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
                language_hints=[Language.EN, Language.HI_IN],
            ),
        )
    else:
        logger.info("Using Deepgram STT service")
        return DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))


def initialize_llm():
    """Initialize LLM service with oceanographic expertise."""
    # Try Groq first for faster inference
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        logger.info("Using Groq LLM for fast inference")
        return GroqLLMService(
            api_key=groq_key,
            model=os.getenv("GROQ_MODEL_NAME"),  # Good balance of speed and capability
            system_message=create_oceanographic_system_prompt()
        )

    # Fallback to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL")
    if openai_key:
        logger.info("Using OpenAI LLM")
        return OpenAILLMService(
            api_key=openai_key,
            base_url=os.getenv("OPENAI_API_BASE_URL"),
            model=openai_model,  # Cost-effective for voice conversations
            system_message=create_oceanographic_system_prompt()
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


async def initialize_mcp_services(llm):
    """Initialize multiple MCP services for ARGO data access and Supabase."""
    mcp_clients = []

    # Custom ARGO MCP Server (HTTP/SSE)
    argo_mcp_url = os.getenv("ARGO_MCP_SERVER_URL", "http://localhost:8000")
    try:
        argo_mcp = MCPClient(
            server_params=StreamableHttpParameters(
                url=f"{argo_mcp_url}/mcp/",
                headers={"Content-Type": "application/json"}
            )
        )

        # Register ARGO tools
        await argo_mcp.register_tools(llm)
        mcp_clients.append(argo_mcp)
        logger.info(f"Connected to ARGO MCP server at {argo_mcp_url}")

    except Exception as e:
        logger.warning(f"Could not connect to ARGO MCP server: {e}")

    # Supabase MCP Server (Stdio)
    try:
        supabase_mcp = MCPClient(
            server_params=StdioServerParameters(
                command="npx",
                args=[
                    "-y",
                    "@supabase/mcp-server-supabase@latest",
                    "--read-only",
                    f"--project-ref={os.getenv('SUPABASE_PROJECT_REF')}",
                    "--features=database"
                ],
                env={"SUPABASE_ACCESS_TOKEN": os.getenv("SUPABASE_ACCESS_TOKEN")}
            )
        )

        # Register Supabase tools
        await supabase_mcp.register_tools(llm)
        mcp_clients.append(supabase_mcp)
        logger.info("Connected to Supabase MCP server")

    except Exception as e:
        logger.warning(f"Could not connect to Supabase MCP server: {e}")

    # Additional MCP servers (if needed)
    # You can add more MCP clients here following the same pattern

    return mcp_clients


async def main():
    """Main function to run the Pipecat-native oceanographic voice AI."""

    session_id = str(uuid.uuid4())
    mcp_clients = []

    try:
        logger.info("Starting Pipecat Oceanographic Voice AI Pipeline")

        # Initialize all components
        transport = await initialize_transport()
        stt = initialize_stt()
        llm = initialize_llm()
        tts = initialize_tts()

        # Initialize MCP services
        mcp_clients = await initialize_mcp_services(llm)

        logger.info(f"Session started: {session_id}")

        # Initialize transcript processor
        transcript = TranscriptProcessor()

        # Set up context for conversation continuity
        context = OpenAILLMContext(
            messages=[
                {
                    "role": "system",
                    "content": create_oceanographic_system_prompt()
                },
                {
                    "role": "assistant",
                    "content": "Hello! I'm FloatChat, your oceanographic data assistant. I can help you explore ARGO float measurements from around the world's oceans. What would you like to discover today?"
                }
            ]
        )

        # Create context aggregator
        context_aggregator = llm.create_context_aggregator(
            context,
            user_params=LLMUserAggregatorParams(),
            assistant_params=LLMAssistantAggregatorParams()
        )

        # Build the pipeline
        pipeline_components = [
            transport.input(),           # Audio input
            stt,                        # Speech-to-Text
            transcript.user(),          # Log user speech
            context_aggregator.user(),  # Add to conversation context
            llm,                        # LLM with MCP tools
            tts,                        # Text-to-Speech
            transport.output(),         # Audio output
            transcript.assistant(),     # Log assistant speech
            context_aggregator.assistant(),  # Add to conversation context
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
        for mcp_client in mcp_clients:
            try:
                await mcp_client.close()
                logger.info(f"Closed MCP client")
            except Exception as e:
                logger.warning(f"Error closing MCP client: {e}")


        logger.info("Pipecat voice AI session completed")


if __name__ == "__main__":
    asyncio.run(main())