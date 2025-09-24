"""
JARVIS Voice Pipeline - Real-time Voice Interface for Ocean Data

Flow: Silero VAD -> STT -> JARVIS Agent (MCP) -> TTS
This provides the seamless voice experience for JARVIS Ocean Agent.
"""

import asyncio
import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.frames.frames import Frame, TextFrame, AudioRawFrame, EndFrame
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAITTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer
from pipecat.services.deepgram import DeepgramSTTService

from loguru import logger

# Import JARVIS
from sih25.AGENT.jarvis_ocean_agent import JarvisOceanAgent


class JarvisVoicePipeline:
    """
    Voice pipeline that connects to JARVIS for oceanographic queries.

    Pipeline: Silero VAD → STT → JARVIS → TTS → User
    """

    def __init__(self, room_url: Optional[str] = None):
        self.room_url = room_url
        self.jarvis_agent = None
        self.session_id = None
        self.pipeline = None
        self.runner = None

    async def initialize_jarvis(self):
        """Initialize JARVIS Ocean Agent"""
        logger.info("🚀 Initializing JARVIS for voice interface...")

        self.jarvis_agent = JarvisOceanAgent()
        if await self.jarvis_agent.initialize():
            logger.info("✅ JARVIS online and ready for voice commands")
            return True
        else:
            logger.error("❌ Failed to initialize JARVIS")
            return False

    async def create_pipeline(self) -> Pipeline:
        """Create the voice processing pipeline"""

        # Initialize transport (Daily for WebRTC)
        transport = DailyTransport(
            room_name=self.room_url,
            params=DailyParams(
                audio_out_enabled=True,
                transcription_enabled=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer()
            )
        )

        # Initialize STT (Speech-to-Text)
        stt = DeepgramSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            live_options={
                "language": "en-US",
                "model": "nova-2",
                "smart_format": True,
                "filler_words": False,
                "punctuate": True
            }
        )

        # Initialize TTS (Text-to-Speech)
        tts = OpenAITTSService(
            api_key=os.getenv("OPENAI_API_KEY"),
            voice="nova",  # Natural voice for JARVIS
            model="tts-1",
            sample_rate=24000
        )

        # Create JARVIS processor
        jarvis_processor = JarvisVoiceProcessor(self.jarvis_agent)

        # Build the pipeline
        pipeline = Pipeline([
            transport.input(),     # Audio input from user
            stt,                  # Convert speech to text
            jarvis_processor,     # Process with JARVIS
            tts,                  # Convert response to speech
            transport.output()    # Send audio back to user
        ])

        return pipeline

    async def run(self):
        """Run the voice pipeline"""
        try:
            # Initialize JARVIS first
            if not await self.initialize_jarvis():
                logger.error("Cannot start voice pipeline without JARVIS")
                return

            # Create and run pipeline
            self.pipeline = await self.create_pipeline()
            self.runner = PipelineRunner()

            logger.info("🎤 JARVIS Voice Pipeline active - speak naturally!")
            logger.info("Say 'Hey JARVIS' to start, or ask directly about ocean data")

            # Run the pipeline
            await self.runner.run(self.pipeline)

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}")
        finally:
            if self.runner:
                await self.runner.stop()


class JarvisVoiceProcessor:
    """
    Custom processor that connects voice input to JARVIS Agent.
    Handles the flow: STT text → JARVIS → Response text for TTS
    """

    def __init__(self, jarvis_agent: JarvisOceanAgent):
        self.jarvis = jarvis_agent
        self.current_session = None
        self.processing = False

    async def process_frame(self, frame: Frame) -> Frame:
        """Process incoming frames from the pipeline"""

        if isinstance(frame, TextFrame):
            # This is transcribed text from STT
            user_text = frame.text.strip()

            if not user_text:
                return None

            logger.info(f"🎙️ User said: {user_text}")

            # Check for wake word or direct query
            if self._is_wake_word(user_text):
                response_text = "Yes, I'm here. How can I help you explore ocean data?"
            else:
                # Process with JARVIS
                response_text = await self._process_with_jarvis(user_text)

            logger.info(f"🤖 JARVIS responds: {response_text}")

            # Return text frame for TTS
            return TextFrame(text=response_text)

        # Pass through other frame types
        return frame

    def _is_wake_word(self, text: str) -> bool:
        """Check if user said wake word"""
        wake_words = ["hey jarvis", "jarvis", "hello jarvis", "hi jarvis"]
        text_lower = text.lower()
        return any(wake in text_lower for wake in wake_words)

    async def _process_with_jarvis(self, user_text: str) -> str:
        """Process user query with JARVIS agent"""
        try:
            # Call JARVIS with voice context
            result = await self.jarvis.process_query(
                message=user_text,
                session_id=self.current_session,
                voice_input=True,
                context={"interface": "voice"}
            )

            # Get voice-optimized response
            response = result.response_text

            # Clean up for voice output
            response = self._optimize_for_voice(response)

            # Add visualization notification if needed
            if result.visualization_needed:
                response += " I'm displaying the visualization on your screen now."

            return response

        except Exception as e:
            logger.error(f"JARVIS processing error: {e}")
            return "I apologize, I'm having trouble accessing the ocean database. Please try again."

    def _optimize_for_voice(self, text: str) -> str:
        """Optimize JARVIS response for natural speech"""
        import re

        # Remove markdown
        text = re.sub(r'[*_`#]', '', text)

        # Convert numbers to speech-friendly format
        text = re.sub(r'(\d+)\.(\d+)', r'\1 point \2', text)

        # Remove technical IDs for cleaner speech
        text = re.sub(r'\b[A-Z]{3,}_\d+\b', '', text)

        # Ensure proper sentence ending
        if text and not text[-1] in '.!?':
            text += '.'

        return text.strip()


class VoiceHandler:
    """
    Simple interface for managing voice sessions.
    Used by the main application to start/stop voice.
    """

    def __init__(self):
        self.pipeline = None
        self.active = False

    async def start_session(self, session_id: str, room_url: Optional[str] = None):
        """Start a voice session"""
        try:
            self.pipeline = JarvisVoicePipeline(room_url)
            self.active = True

            # Run in background
            asyncio.create_task(self.pipeline.run())

            logger.info(f"Voice session {session_id} started")
            return True

        except Exception as e:
            logger.error(f"Failed to start voice session: {e}")
            self.active = False
            return False

    async def stop_session(self):
        """Stop the current voice session"""
        self.active = False
        if self.pipeline and self.pipeline.runner:
            await self.pipeline.runner.stop()
        logger.info("Voice session stopped")

    def is_active(self) -> bool:
        """Check if voice is active"""
        return self.active


# Standalone runner for testing
async def main():
    """Test the JARVIS voice pipeline"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logger.info("🌊 Starting JARVIS Voice Interface for Ocean Data")
    logger.info("Pipeline: Silero VAD → STT → JARVIS (MCP) → TTS")

    pipeline = JarvisVoicePipeline()
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())