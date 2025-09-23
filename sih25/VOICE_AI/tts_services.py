"""
Multi-Tier TTS Service with Fallback Support
Supports ElevenLabs, Deepgram, and Sarvam TTS with automatic fallback
"""

import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from loguru import logger
import base64


class TTSProvider(Enum):
    ELEVENLABS = "elevenlabs"
    DEEPGRAM = "deepgram"
    SARVAM = "sarvam"


@dataclass
class TTSConfig:
    """Configuration for TTS providers"""
    # ElevenLabs Configuration
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    elevenlabs_model: str = "eleven_monolingual_v1"
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity_boost: float = 0.5

    # Deepgram Configuration
    deepgram_api_key: Optional[str] = None
    deepgram_model: str = "aura-asteria-en"
    deepgram_encoding: str = "linear16"
    deepgram_sample_rate: int = 24000

    # Sarvam TTS Configuration
    sarvam_api_key: Optional[str] = None
    sarvam_target_language: str = "hi-IN"
    sarvam_speaker: str = "karun"
    sarvam_model: str = "bulbul:v2"
    sarvam_sample_rate: int = 24000
    sarvam_pitch: float = 0.0
    sarvam_pace: float = 1.0
    sarvam_loudness: float = 1.0
    sarvam_preprocessing: bool = True

    # Service Preferences
    prefer_elevenlabs: bool = False
    prefer_deepgram: bool = False
    prefer_sarvam: bool = False

    # Fallback Configuration
    enable_auto_fallback: bool = True
    max_retry_attempts: int = 3
    timeout_seconds: int = 10


class SarvamTTSService:
    """Sarvam TTS service for Hindi and Indian language support"""

    def __init__(self, config: TTSConfig):
        self.config = config
        self.base_url = "https://api.sarvam.ai/text-to-speech"

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech using Sarvam TTS"""
        if not self.config.sarvam_api_key:
            logger.error("Sarvam API key not configured")
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.sarvam_api_key}"
        }

        payload = {
            "inputs": [text],
            "target_language_code": self.config.sarvam_target_language,
            "speaker": self.config.sarvam_speaker,
            "model": self.config.sarvam_model,
            "sample_rate": self.config.sarvam_sample_rate,
            "pitch": self.config.sarvam_pitch,
            "pace": self.config.sarvam_pace,
            "loudness": self.config.sarvam_loudness,
            "enable_preprocessing": self.config.sarvam_preprocessing
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Sarvam returns base64 encoded audio
                        if "audios" in result and result["audios"]:
                            audio_data = base64.b64decode(result["audios"][0])
                            logger.info(f"Sarvam TTS synthesis successful, audio length: {len(audio_data)} bytes")
                            return audio_data
                    else:
                        logger.error(f"Sarvam TTS API error: {response.status} - {await response.text()}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"Sarvam TTS request timeout after {self.config.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"Sarvam TTS synthesis error: {e}")
            return None


class ElevenLabsTTSService:
    """ElevenLabs TTS service"""

    def __init__(self, config: TTSConfig):
        self.config = config
        self.base_url = "https://api.elevenlabs.io/v1"

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech using ElevenLabs"""
        if not self.config.elevenlabs_api_key or not self.config.elevenlabs_voice_id:
            logger.error("ElevenLabs API key or voice ID not configured")
            return None

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.config.elevenlabs_api_key
        }

        payload = {
            "text": text,
            "model_id": self.config.elevenlabs_model,
            "voice_settings": {
                "stability": self.config.elevenlabs_stability,
                "similarity_boost": self.config.elevenlabs_similarity_boost
            }
        }

        try:
            url = f"{self.base_url}/text-to-speech/{self.config.elevenlabs_voice_id}"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info(f"ElevenLabs TTS synthesis successful, audio length: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        logger.error(f"ElevenLabs TTS API error: {response.status} - {await response.text()}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"ElevenLabs TTS request timeout after {self.config.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"ElevenLabs TTS synthesis error: {e}")
            return None


class DeepgramTTSService:
    """Deepgram TTS service"""

    def __init__(self, config: TTSConfig):
        self.config = config
        self.base_url = "https://api.deepgram.com/v1/speak"

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech using Deepgram"""
        if not self.config.deepgram_api_key:
            logger.error("Deepgram API key not configured")
            return None

        headers = {
            "Authorization": f"Token {self.config.deepgram_api_key}",
            "Content-Type": "application/json"
        }

        params = {
            "model": self.config.deepgram_model,
            "encoding": self.config.deepgram_encoding,
            "sample_rate": self.config.deepgram_sample_rate
        }

        payload = {"text": text}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info(f"Deepgram TTS synthesis successful, audio length: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        logger.error(f"Deepgram TTS API error: {response.status} - {await response.text()}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"Deepgram TTS request timeout after {self.config.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"Deepgram TTS synthesis error: {e}")
            return None


class MultiTierTTSService:
    """Multi-tier TTS service with automatic fallback"""

    def __init__(self, config: TTSConfig):
        self.config = config

        # Initialize TTS services
        self.elevenlabs = ElevenLabsTTSService(config)
        self.deepgram = DeepgramTTSService(config)
        self.sarvam = SarvamTTSService(config)

        # Define fallback order based on preferences
        self.fallback_order = self._determine_fallback_order()

    def _determine_fallback_order(self) -> List[Tuple[TTSProvider, Any]]:
        """Determine the fallback order based on preferences"""
        services = [
            (TTSProvider.ELEVENLABS, self.elevenlabs),
            (TTSProvider.DEEPGRAM, self.deepgram),
            (TTSProvider.SARVAM, self.sarvam)
        ]

        # Check preferences
        if self.config.prefer_elevenlabs:
            return [(TTSProvider.ELEVENLABS, self.elevenlabs)]
        elif self.config.prefer_deepgram:
            return [(TTSProvider.DEEPGRAM, self.deepgram)]
        elif self.config.prefer_sarvam:
            return [(TTSProvider.SARVAM, self.sarvam)]
        else:
            # Default fallback order: ElevenLabs -> Deepgram -> Sarvam
            return services

    async def synthesize(self, text: str, preferred_language: Optional[str] = None) -> Optional[bytes]:
        """
        Synthesize speech with automatic fallback

        Args:
            text: Text to synthesize
            preferred_language: Language preference (e.g., 'hi-IN' for Hindi)
        """
        if not text.strip():
            logger.warning("Empty text provided for synthesis")
            return None

        # Adjust fallback order based on language preference
        fallback_order = self._adjust_for_language(preferred_language)

        logger.info(f"Starting TTS synthesis with {len(fallback_order)} providers in fallback chain")

        for provider, service in fallback_order:
            logger.info(f"Attempting TTS synthesis with {provider.value}")

            for attempt in range(self.config.max_retry_attempts):
                try:
                    audio_data = await service.synthesize(text)
                    if audio_data:
                        logger.info(f"TTS synthesis successful with {provider.value} on attempt {attempt + 1}")
                        return audio_data
                    else:
                        logger.warning(f"TTS synthesis failed with {provider.value} on attempt {attempt + 1}")

                except Exception as e:
                    logger.error(f"TTS synthesis error with {provider.value} on attempt {attempt + 1}: {e}")

                if attempt < self.config.max_retry_attempts - 1:
                    await asyncio.sleep(1)  # Brief delay before retry

        logger.error("All TTS providers failed")
        return None

    def _adjust_for_language(self, preferred_language: Optional[str]) -> List[Tuple[TTSProvider, Any]]:
        """Adjust fallback order based on language preference"""
        if preferred_language and preferred_language.startswith('hi'):
            # For Hindi, prioritize Sarvam TTS
            return [
                (TTSProvider.SARVAM, self.sarvam),
                (TTSProvider.ELEVENLABS, self.elevenlabs),
                (TTSProvider.DEEPGRAM, self.deepgram)
            ]
        else:
            # For other languages, use default order
            return self.fallback_order

    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all TTS services"""
        return {
            "elevenlabs": {
                "configured": bool(self.config.elevenlabs_api_key and self.config.elevenlabs_voice_id),
                "preferred": self.config.prefer_elevenlabs
            },
            "deepgram": {
                "configured": bool(self.config.deepgram_api_key),
                "preferred": self.config.prefer_deepgram
            },
            "sarvam": {
                "configured": bool(self.config.sarvam_api_key),
                "preferred": self.config.prefer_sarvam,
                "target_language": self.config.sarvam_target_language
            },
            "fallback_order": [provider.value for provider, _ in self.fallback_order],
            "auto_fallback_enabled": self.config.enable_auto_fallback
        }


def create_tts_config_from_env() -> TTSConfig:
    """Create TTS configuration from environment variables"""
    return TTSConfig(
        # ElevenLabs
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID"),

        # Deepgram
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY"),

        # Sarvam TTS
        sarvam_api_key=os.getenv("SARVAM_API_KEY"),
        sarvam_target_language=os.getenv("SARVAM_TARGET_LANGUAGE", "hi-IN"),
        sarvam_speaker=os.getenv("SARVAM_SPEAKER", "karun"),
        sarvam_model=os.getenv("SARVAM_MODEL", "bulbul:v2"),
        sarvam_sample_rate=int(os.getenv("SARVAM_SAMPLE_RATE", "24000")),
        sarvam_pitch=float(os.getenv("SARVAM_PITCH", "0")),
        sarvam_pace=float(os.getenv("SARVAM_PACE", "1.0")),
        sarvam_loudness=float(os.getenv("SARVAM_LOUDNESS", "1.0")),
        sarvam_preprocessing=os.getenv("SARVAM_PREPROCESSING", "true").lower() == "true",

        # Preferences
        prefer_elevenlabs=os.getenv("PREFER_ELEVENLABS_TTS", "false").lower() == "true",
        prefer_deepgram=os.getenv("PREFER_DEEPGRAM_TTS", "false").lower() == "true",
        prefer_sarvam=os.getenv("PREFER_SARVAM_TTS", "false").lower() == "true",
    )