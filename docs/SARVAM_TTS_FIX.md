# Fixed: Using Native Pipecat Sarvam AI TTS

## The Issue

Initial error:
```
AttributeError: 'MultiTierTTSService' object has no attribute 'link'
```

**Root Cause**: Was using custom `MultiTierTTSService` wrapper which wasn't a proper Pipecat processor.

## The Solution

Switched to **Pipecat's native Sarvam AI TTS service** which is built into Pipecat 0.0.85.

### Code Changes

**File**: `sih25/VOICE_AI/pipecat_bot.py`

```python
# Import Pipecat's native Sarvam TTS
from pipecat.services.sarvam.tts import SarvamTTSService

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
```

### Why Pipecat's Native Sarvam TTS?

✅ **Proper Pipeline Integration**: Inherits from `TTSService` base class with all required methods
✅ **Indian Language Support**: Specialized for Hindi and other Indian languages
✅ **Voice Customization**: Pitch, pace, loudness, preprocessing controls
✅ **Already Configured**: Your `.env` has all required Sarvam AI settings
✅ **No Custom Wrapper Needed**: Works directly in Pipecat pipeline

### Sarvam AI Features

- **Languages**: Hindi (hi-IN), English, and other Indian languages
- **Voices**: Multiple speakers including "karun" (default)
- **Model**: bulbul:v2 (latest Sarvam TTS model)
- **Preprocessing**: Handles mixed-language content (Hindi + English)
- **Sample Rate**: 24kHz (configurable)

### Configuration from .env

```bash
SARVAM_API_KEY=sk_8tl8x7bb_U64EeJc9FbnwMF50NyOpoP8M
SARVAM_TARGET_LANGUAGE=hi-IN
SARVAM_SPEAKER=karun
SARVAM_MODEL=bulbul:v2
SARVAM_SAMPLE_RATE=24000
SARVAM_PITCH=0
SARVAM_PACE=1.0
SARVAM_LOUDNESS=1.0
SARVAM_PREPROCESSING=true
```

## Additional Fix: VAD Deprecation Warning

Also fixed the deprecation warning:
```
Parameter 'vad_enabled' is deprecated, use 'audio_in_enabled' and 'vad_analyzer' instead
```

**Changed**:
```python
# Before
params=DailyParams(
    vad_enabled=True,  # ❌ Deprecated
    vad_analyzer=SileroVADAnalyzer(...)
)

# After
params=DailyParams(
    vad_analyzer=SileroVADAnalyzer(...)  # ✅ Correct
)
```

## Verification

```bash
python verify_voice_setup.py
```

Expected output:
```
✅ SARVAM_API_KEY       (Sarvam AI Text-to-Speech (Hindi/English))
   → sk_8tl8x7b...
```

## Testing

```bash
# Start backend
python run_mvp.py

# Look for in logs:
🔊 Initializing Sarvam AI TTS...
✅ Voice bot is now listening for audio input...
```

## Pipecat Sarvam AI Documentation

- [Sarvam TTS API Reference](https://reference-server.pipecat.ai/en/latest/api/pipecat.services.sarvam.tts.html)
- [Example Implementation](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/07z-interruptible-sarvam.py)
- [Sarvam AI Docs](https://docs.sarvam.ai/api-reference-docs/text-to-speech/convert)

## Benefits Over Custom Wrapper

| Feature | Custom MultiTierTTSService | Native SarvamTTSService |
|---------|---------------------------|-------------------------|
| Pipeline Integration | ❌ Missing `.link()` method | ✅ Full Pipecat processor |
| Frame Handling | ❌ Manual implementation | ✅ Built-in frame processing |
| Error Handling | ⚠️ Custom logic | ✅ Pipecat error handling |
| Word Timestamps | ❌ Not implemented | ✅ Supported (if available) |
| Maintenance | ⚠️ Requires updates | ✅ Updated with Pipecat |

## Ready to Test! 🎤

The voice AI pipeline is now properly configured with:
- ✅ Groq LLM (for conversation intelligence)
- ✅ Soniox STT (for speech recognition)
- ✅ Sarvam AI TTS (for Hindi/English voice synthesis)
- ✅ Daily.co WebRTC (for real-time audio transport)

All using native Pipecat services that work seamlessly in the pipeline!
