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
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.services.tts_service import TTSService
from pipecat.frames.frames import TTSAudioRawFrame, TTSStartedFrame, TTSStoppedFrame

# Import your custom TTS services
from sih25.VOICE_AI.tts_services import MultiTierTTSService, create_tts_config_from_env
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.services.soniox.stt import SonioxSTTService

from loguru import logger

# Import JARVIS
from sih25.AGENT.jarvis_ocean_agent import JarvisOceanAgent

class SarvamTTSPipecatService(TTSService):
    """Pipecat-compatible wrapper for Sarvam/MultiTier TTS service"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize the multi-tier TTS with config from environment
        tts_config = create_tts_config_from_env()
        self._multi_tts = MultiTierTTSService(tts_config)

        logger.info("Initialized Sarvam/MultiTier TTS service")

    async def run_tts(self, text: str) -> None:
        """Run TTS synthesis and emit audio frames"""
        try:
            # Emit TTS started frame
            await self.push_frame(TTSStartedFrame())

            # Get audio data from multi-tier TTS
            audio_data = await self._multi_tts.synthesize(text)

            if audio_data:
                # Convert to the format expected by Pipecat
                # Assuming the audio is in the correct format already
                await self.push_frame(TTSAudioRawFrame(
                    audio=audio_data,
                    sample_rate=24000,  # Sample rate from your TTS config
                    num_channels=1
                ))
            else:
                logger.error("TTS synthesis failed - no audio data returned")

            # Emit TTS stopped frame
            await self.push_frame(TTSStoppedFrame())

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            await self.push_frame(TTSStoppedFrame())


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
        room_url = self.room_url or os.getenv("DAILY_ROOM_URL")
        if not room_url:
            raise ValueError("No Daily room URL provided. Set via argument or DAILY_ROOM_URL environment variable.")

        transport = DailyTransport(
            room_url,
            os.getenv("DAILY_API_KEY"),
            "JARVIS",
            DailyParams(
                audio_out_enabled=True,
                transcription_enabled=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer()
            )
        )

        # Initialize STT (Speech-to-Text) - Use Soniox
        soniox_api_key = os.getenv("SONIOX_API_KEY")
        if not soniox_api_key:
            # Try fallback to Deepgram
            deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
            if deepgram_api_key:
                logger.warning("SONIOX_API_KEY not found, falling back to Deepgram STT")
                from deepgram import LiveOptions
                from pipecat.services.deepgram.stt import DeepgramSTTService

                stt = DeepgramSTTService(
                    api_key=deepgram_api_key,
                    live_options=LiveOptions(
                        language="en-US",
                        model="nova-2",
                        smart_format=True,
                        filler_words=False,
                        punctuate=True
                    )
                )
            else:
                raise ValueError("No STT API key found. Please set SONIOX_API_KEY or DEEPGRAM_API_KEY in environment variables.")
        else:
            stt = SonioxSTTService(
                api_key=soniox_api_key
            )

        # Initialize TTS (Text-to-Speech) - Use Sarvam MultiTier TTS
        tts = SarvamTTSPipecatService()

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

            # Create pipeline
            self.pipeline = await self.create_pipeline()

            logger.info("🎤 JARVIS Voice Pipeline active - speak naturally!")
            logger.info("Say 'Hey JARVIS' to start, or ask directly about ocean data")

            # Use pipecat.run() pattern - let pipecat handle the pipeline execution
            # The pipeline will run until manually stopped or error occurs
            import asyncio
            await asyncio.Event().wait()  # Keep running until interrupted

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}")
        finally:
            # Cleanup will be handled automatically
            pass


class JarvisVoiceProcessor(FrameProcessor):
    """
    Custom processor that connects voice input to JARVIS Agent.
    Handles the flow: STT text → JARVIS → Response text for TTS
    """

    def __init__(self, jarvis_agent: JarvisOceanAgent, **kwargs):
        super().__init__(**kwargs)
        self.jarvis = jarvis_agent
        self.current_session = None
        self.processing = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames from the pipeline"""

        if isinstance(frame, TextFrame):
            # This is transcribed text from STT
            user_text = frame.text.strip()

            if not user_text:
                return

            logger.info(f"🎙️ User said: {user_text}")

            # Check for wake word or direct query
            if self._is_wake_word(user_text):
                response_text = "Yes, I'm here. How can I help you explore ocean data?"
            else:
                # Process with JARVIS
                response_text = await self._process_with_jarvis(user_text)

            logger.info(f"🤖 JARVIS responds: {response_text}")

            # Push text frame downstream for TTS
            await self.push_frame(TextFrame(text=response_text), direction)
        else:
            # Pass through other frame types
            await self.push_frame(frame, direction)

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
            await self.pipeline.runner.cancel()
        logger.info("Voice session stopped")

    def is_active(self) -> bool:
        """Check if voice is active"""
        return self.active


# Standalone runner for testing
async def main():
    """Create and run the JARVIS voice pipeline"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logger.info("🌊 Starting JARVIS Voice Interface for Ocean Data")
    logger.info("Pipeline: Silero VAD → STT → JARVIS (MCP) → TTS")

    # Initialize JARVIS first
    jarvis_agent = JarvisOceanAgent()
    if not await jarvis_agent.initialize():
        logger.error("Cannot start voice pipeline without JARVIS")
        return

    logger.info("✅ JARVIS online and ready for voice commands")

    # Create the pipeline components
    room_url = os.getenv("DAILY_ROOM_URL")
    if not room_url:
        logger.error("No Daily room URL provided. Set DAILY_ROOM_URL environment variable.")
        return

    transport = DailyTransport(
        room_url,
        os.getenv("DAILY_API_KEY"),
        "JARVIS",
        DailyParams(
            audio_out_enabled=True,
            transcription_enabled=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer()
        )
    )

    # Initialize STT (Speech-to-Text) - Use Soniox
    soniox_api_key = os.getenv("SONIOX_API_KEY")
    if not soniox_api_key:
        deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        if deepgram_api_key:
            logger.warning("SONIOX_API_KEY not found, falling back to Deepgram STT")
            from deepgram import LiveOptions
            from pipecat.services.deepgram.stt import DeepgramSTTService
            stt = DeepgramSTTService(
                api_key=deepgram_api_key,
                live_options=LiveOptions(
                    language="en-US",
                    model="nova-2",
                    smart_format=True,
                    filler_words=False,
                    punctuate=True
                )
            )
        else:
            logger.error("No STT API key found. Please set SONIOX_API_KEY or DEEPGRAM_API_KEY")
            return
    else:
        stt = SonioxSTTService(api_key=soniox_api_key)

    # Initialize TTS
    tts = SarvamTTSPipecatService()

    # Create JARVIS processor
    jarvis_processor = JarvisVoiceProcessor(jarvis_agent)

    # Build the pipeline
    pipeline = Pipeline([
        transport.input(),     # Audio input from user
        stt,                  # Convert speech to text
        jarvis_processor,     # Process with JARVIS
        tts,                  # Convert response to speech
        transport.output()    # Send audio back to user
    ])

    logger.info("🎤 JARVIS Voice Pipeline active - speak naturally!")
    logger.info("Say 'Hey JARVIS' to start, or ask directly about ocean data")

    # Create and run pipeline task
    task = PipelineTask(pipeline)
    runner = PipelineRunner()

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user")
    finally:
        await runner.cancel()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())