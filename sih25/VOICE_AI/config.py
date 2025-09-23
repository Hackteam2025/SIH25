"""
Configuration for AGNO Voice AI Pipeline

Environment variables and service configurations for the voice pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

# Default configuration values
DEFAULT_CONFIG = {
    # MCP Server Configuration
    "MCP_SERVER_URL": "http://localhost:8000",

    # Audio Transport Configuration
    "USE_DAILY_TRANSPORT": False,  # Set to True if Daily.co WebRTC is available
    "DAILY_API_KEY": None,  # Required for Daily transport

    # Speech-to-Text Configuration
    "STT_PROVIDER": "deepgram",  # Options: "deepgram", "soniox"
    "DEEPGRAM_API_KEY": None,
    "SONIOX_API_KEY": None,

    # Multi-Tier TTS Configuration with Fallback
    # Fallback order: ElevenLabs -> Deepgram -> Sarvam TTS
    "TTS_PROVIDER": "multi_tier",  # Options: "deepgram", "elevenlabs", "sarvam", "multi_tier"

    # ElevenLabs TTS Configuration
    "ELEVENLABS_API_KEY": None,
    "ELEVENLABS_VOICE_ID": None,
    "ELEVENLABS_MODEL": "eleven_monolingual_v1",
    "ELEVENLABS_STABILITY": 0.5,
    "ELEVENLABS_SIMILARITY_BOOST": 0.5,

    # Deepgram TTS Configuration
    "DEEPGRAM_TTS_MODEL": "aura-asteria-en",
    "DEEPGRAM_TTS_ENCODING": "linear16",
    "DEEPGRAM_TTS_SAMPLE_RATE": 24000,

    # Sarvam TTS Configuration (Tertiary Fallback / Hindi Support)
    "SARVAM_API_KEY": None,
    "SARVAM_TARGET_LANGUAGE": "hi-IN",
    "SARVAM_SPEAKER": "karun",
    "SARVAM_MODEL": "bulbul:v2",
    "SARVAM_SAMPLE_RATE": 24000,
    "SARVAM_PITCH": 0,
    "SARVAM_PACE": 1.0,
    "SARVAM_LOUDNESS": 1.0,
    "SARVAM_PREPROCESSING": True,

    # TTS Service Preferences (set only one to true)
    "PREFER_ELEVENLABS_TTS": False,
    "PREFER_DEEPGRAM_TTS": False,
    "PREFER_SARVAM_TTS": False,
    # When all are false, auto-fallback chain is used: ElevenLabs -> Deepgram -> Sarvam

    # TTS Fallback Configuration
    "TTS_ENABLE_AUTO_FALLBACK": True,
    "TTS_MAX_RETRY_ATTEMPTS": 3,
    "TTS_TIMEOUT_SECONDS": 10,

    # Voice Processing Configuration
    "ENABLE_INTERRUPTIONS": True,
    "VAD_THRESHOLD": 0.5,  # Voice Activity Detection threshold

    # Multilingual Support
    "DEFAULT_LANGUAGE": "en-US",
    "SUPPORTED_LANGUAGES": ["en-US", "hi-IN", "en-IN"],

    # Session Logging Configuration
    "ENABLE_SESSION_LOGGING": True,
    "LOG_DIRECTORY": "logs/voice_sessions",

    # AGNO Agent Configuration
    "AGNO_RESPONSE_MAX_LENGTH": 200,  # Max characters for voice response
    "AGNO_TIMEOUT_SECONDS": 30,  # Timeout for agent processing
}


class VoiceAIConfig:
    """Configuration manager for voice AI pipeline"""

    def __init__(self, config_file: Optional[Path] = None):
        self.config = DEFAULT_CONFIG.copy()
        self._load_from_env()

        if config_file and config_file.exists():
            self._load_from_file(config_file)

    def _load_from_env(self):
        """Load configuration from environment variables"""
        for key in self.config.keys():
            env_value = os.getenv(key)
            if env_value is not None:
                # Convert string values to appropriate types
                if key.endswith("_API_KEY") or key.endswith("_URL"):
                    self.config[key] = env_value
                elif key.startswith("ENABLE_"):
                    self.config[key] = env_value.lower() in ("true", "1", "yes", "on")
                elif key.endswith("_THRESHOLD") or key.endswith("_SECONDS"):
                    try:
                        self.config[key] = float(env_value)
                    except ValueError:
                        pass
                elif key.endswith("_LENGTH"):
                    try:
                        self.config[key] = int(env_value)
                    except ValueError:
                        pass
                else:
                    self.config[key] = env_value

    def _load_from_file(self, config_file: Path):
        """Load configuration from file (JSON format)"""
        import json
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)

    def validate_required_keys(self) -> Dict[str, str]:
        """Validate that required configuration keys are present"""
        required_keys = []
        missing_keys = {}

        # Check STT provider requirements
        stt_provider = self.get("STT_PROVIDER", "deepgram")
        if stt_provider == "deepgram" and not self.get("DEEPGRAM_API_KEY"):
            missing_keys["DEEPGRAM_API_KEY"] = "Required for Deepgram STT service"
        elif stt_provider == "soniox" and not self.get("SONIOX_API_KEY"):
            missing_keys["SONIOX_API_KEY"] = "Required for Soniox STT service"

        # Check TTS provider requirements
        tts_provider = self.get("TTS_PROVIDER", "multi_tier")

        if tts_provider == "elevenlabs":
            if not self.get("ELEVENLABS_API_KEY"):
                missing_keys["ELEVENLABS_API_KEY"] = "Required for ElevenLabs TTS service"
            if not self.get("ELEVENLABS_VOICE_ID"):
                missing_keys["ELEVENLABS_VOICE_ID"] = "Required for ElevenLabs TTS service"
        elif tts_provider == "sarvam":
            if not self.get("SARVAM_API_KEY"):
                missing_keys["SARVAM_API_KEY"] = "Required for Sarvam TTS service"
        elif tts_provider == "multi_tier":
            # For multi-tier, check if at least one TTS service is configured
            tts_services_configured = 0
            if self.get("ELEVENLABS_API_KEY") and self.get("ELEVENLABS_VOICE_ID"):
                tts_services_configured += 1
            if self.get("DEEPGRAM_API_KEY"):
                tts_services_configured += 1
            if self.get("SARVAM_API_KEY"):
                tts_services_configured += 1

            if tts_services_configured == 0:
                missing_keys["TTS_SERVICES"] = "At least one TTS service must be configured for multi-tier support"

        # Check transport requirements
        if self.get("USE_DAILY_TRANSPORT") and not self.get("DAILY_API_KEY"):
            missing_keys["DAILY_API_KEY"] = "Required for Daily.co WebRTC transport"

        return missing_keys

    def get_summary(self) -> str:
        """Get configuration summary for logging"""
        stt_provider = self.get("STT_PROVIDER")
        tts_provider = self.get("TTS_PROVIDER")
        transport = "Daily WebRTC" if self.get("USE_DAILY_TRANSPORT") else "Local Audio"
        default_language = self.get("DEFAULT_LANGUAGE")

        # TTS Service Details
        tts_details = f"Provider: {tts_provider}"
        if tts_provider == "multi_tier":
            configured_services = []
            if self.get("ELEVENLABS_API_KEY"):
                configured_services.append("ElevenLabs")
            if self.get("DEEPGRAM_API_KEY"):
                configured_services.append("Deepgram")
            if self.get("SARVAM_API_KEY"):
                configured_services.append("Sarvam")
            tts_details += f" (Services: {', '.join(configured_services)})"

        return f"""
Voice AI Configuration:
  Transport: {transport}
  STT Provider: {stt_provider}
  TTS: {tts_details}
  Default Language: {default_language}
  Supported Languages: {', '.join(self.get("SUPPORTED_LANGUAGES", []))}
  MCP Server: {self.get("MCP_SERVER_URL")}
  Session Logging: {self.get("ENABLE_SESSION_LOGGING")}
  Interruptions: {self.get("ENABLE_INTERRUPTIONS")}
  TTS Auto-Fallback: {self.get("TTS_ENABLE_AUTO_FALLBACK")}
        """.strip()


# Create default config instance
config = VoiceAIConfig()