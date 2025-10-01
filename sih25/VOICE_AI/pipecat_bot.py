#!/usr/bin/env python3
"""
Pipecat Voice Bot with Daily Transport
Integrates: Groq LLM, Soniox STT, Sarvam AI TTS (multilingual Hindi/English)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

# Pipecat core imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
    OpenAILLMContextFrame,
)
from pipecat.frames.frames import EndFrame, LLMMessagesFrame
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.transports.daily.transport import DailyTransport, DailyParams

# LLM Service
from pipecat.services.groq.llm import GroqLLMService

# TTS Service
from pipecat.services.sarvam.tts import SarvamTTSService

# Add parent directory to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Load environment variables
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f"Loaded .env from {dotenv_path}")
else:
    logger.warning(f".env file not found at {dotenv_path}")

# Configure rotating file logs to sih25/logs so subprocess output is always captured
logs_dir = Path(__file__).resolve().parents[1] / "logs"  # .../sih25/logs
logs_dir.mkdir(parents=True, exist_ok=True)

# Add a file sink (keep default stderr sink too)
logger.add(
    logs_dir / "pipecat_voice_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time} | {level} | {name}:{line} | {message}",
)


def create_oceanographic_system_prompt() -> str:
    """System prompt for ARGO oceanographic data assistant"""
    return """You are FloatChat, an expert oceanographic data assistant specializing in ARGO float measurements. You help users discover and understand ocean data through natural conversation.

## Your Expertise

### ARGO Parameters:
- **TEMP** (Temperature, °C): Ocean water temperature (-2°C to 35°C)
- **PSAL** (Practical Salinity, PSU): Salinity from conductivity (30-37 PSU)
- **PRES** (Pressure, dbar): Water pressure ≈ depth in meters
- **DOXY** (Dissolved Oxygen, μmol/kg): Marine ecosystem health (0-400 μmol/kg)

### Quality Control Flags:
- **1**: Good data (high reliability)
- **2**: Probably good data
- **3**: Bad but correctable
- **4**: Bad data - do not use

### Your Behavior:
- Provide scientific context and explain data significance
- Be conversational but maintain scientific rigor
- Keep responses under 30 seconds when spoken
- Use simple, clear language
- End with engaging follow-up questions
- Support both Hindi and English languages naturally

You can help users explore ARGO float data from oceans worldwide."""


async def create_bot_transport(room_url: str, token: str) -> DailyTransport:
    """Create and configure Daily transport for WebRTC"""
    logger.info(f"Creating Daily transport for room: {room_url}")

    transport = DailyTransport(
        room_url=room_url,
        token=token,
        bot_name="FloatChat Voice AI",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=False,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    confidence=0.5,
                    min_volume=0.6,
                    start_secs=0.2,
                    stop_secs=0.8
                )
            ),
            transcription_enabled=False,  # We use Soniox STT instead
        ),
    )

    return transport


def create_stt_service() -> SonioxSTTService:
    """Initialize Soniox STT with multilingual support"""
    soniox_key = os.getenv("SONIOX_API_KEY")
    if not soniox_key:
        raise ValueError("SONIOX_API_KEY not found in environment")

    logger.info("Initializing Soniox STT with Hindi/English support")

    return SonioxSTTService(
        api_key=soniox_key,
        language="en",  # Primary language, can detect Hindi automatically
        # Soniox supports automatic language detection
    )


def create_llm_service() -> GroqLLMService:
    """Initialize Groq LLM service"""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not found in environment")

    groq_model = os.getenv("GROQ_MODEL_NAME", "llama-3.1-70b-versatile")

    logger.info(f"Initializing Groq LLM: {groq_model}")

    return GroqLLMService(
        api_key=groq_key,
        model=groq_model,
    )


def create_tts_service() -> SarvamTTSService:
    """Initialize Sarvam AI TTS service for Hindi/English"""
    sarvam_key = os.getenv("SARVAM_API_KEY")
    if not sarvam_key:
        raise ValueError("SARVAM_API_KEY not found in environment")

    logger.info("Initializing Sarvam AI TTS with Hindi/English support")

    return SarvamTTSService(
        api_key=sarvam_key,
        voice_id=os.getenv("SARVAM_SPEAKER", "karun"),  # Default Hindi voice
        model=os.getenv("SARVAM_MODEL", "bulbul:v2"),
        target_language_code=os.getenv("SARVAM_TARGET_LANGUAGE", "hi-IN"),
        sample_rate=int(os.getenv("SARVAM_SAMPLE_RATE", "24000")),
        pitch=float(os.getenv("SARVAM_PITCH", "0")),
        pace=float(os.getenv("SARVAM_PACE", "1.0")),
        loudness=float(os.getenv("SARVAM_LOUDNESS", "1.0")),
        enable_preprocessing=os.getenv("SARVAM_PREPROCESSING", "true").lower() == "true"
    )


async def run_voice_bot(room_url: str, token: str):
    """Main bot logic"""

    try:
        logger.info("=" * 60)
        logger.info("🤖 VOICE BOT STARTING")
        logger.info("=" * 60)

        # Initialize all services
        logger.info("🔧 Initializing Daily transport...")
        transport = await create_bot_transport(room_url, token)

        logger.info("🎤 Initializing Soniox STT...")
        stt = create_stt_service()

        logger.info("🧠 Initializing Groq LLM...")
        llm = create_llm_service()

        logger.info("🔊 Initializing Sarvam AI TTS...")
        tts = create_tts_service()

        # Create conversation context
        logger.info("💬 Setting up conversation context...")
        context = OpenAILLMContext(
            messages=[
                {
                    "role": "system",
                    "content": create_oceanographic_system_prompt()
                }
            ]
        )
        context_aggregator = llm.create_context_aggregator(context)

        # Build pipeline
        logger.info("🔗 Building Pipecat pipeline...")
        pipeline = Pipeline([
            transport.input(),           # Audio input from user
            stt,                        # Speech-to-Text (Soniox)
            context_aggregator.user(),  # Add to conversation context
            llm,                        # LLM processing (Groq)
            tts,                        # Text-to-Speech (Sarvam AI)
            transport.output(),         # Audio output to user
            context_aggregator.assistant(),  # Save assistant response
        ])

        # Create task with interruption support
        logger.info("⚙️ Creating pipeline task...")
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            )
        )

        # Event handlers
        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            logger.info(f"👤 First participant joined: {participant.get('id')}")
            # Greet the user
            await task.queue_frames([
                LLMMessagesFrame([
                    {
                        "role": "system",
                        "content": "A user just joined. Greet them warmly and introduce yourself as FloatChat, their oceanographic data assistant."
                    }
                ])
            ])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info(f"👋 Participant left: {participant.get('id')}, reason: {reason}")
            await task.queue_frames([EndFrame()])

        @transport.event_handler("on_call_state_updated")
        async def on_call_state_updated(transport, state):
            logger.info(f"📞 Call state updated: {state}")

        # Run the pipeline
        runner = PipelineRunner()
        logger.info("🚀 Starting voice bot pipeline...")
        logger.info("✅ Voice bot is now listening for audio input...")
        await runner.run(task)

    except Exception as e:
        logger.error(f"💥 Error in voice bot: {e}", exc_info=True)
        raise
    finally:
        logger.info("🛑 Voice bot session ended")


async def main(room_url: str, token: str):
    """Entry point for voice bot"""
    logger.info(f"FloatChat Voice AI starting...")
    logger.info(f"Room URL: {room_url}")
    logger.info(f"Using Groq LLM, Soniox STT, Sarvam AI TTS")

    await run_voice_bot(room_url, token)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipecat Voice Bot with Daily Transport")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument("-t", "--token", type=str, required=True, help="Daily room token")

    args = parser.parse_args()

    asyncio.run(main(args.url, args.token))
