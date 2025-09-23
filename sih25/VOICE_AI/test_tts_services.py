"""
Test script for Multi-Tier TTS Service with Fallback Support

Tests the TTS fallback chain and multilingual capabilities.
"""

import asyncio
import os
from pathlib import Path
import tempfile
from typing import Dict, Any

from loguru import logger

# Import our TTS services
from tts_services import (
    MultiTierTTSService,
    TTSConfig,
    create_tts_config_from_env,
    TTSProvider
)


async def test_individual_tts_services():
    """Test individual TTS services"""
    logger.info("=== Testing Individual TTS Services ===")

    # Create test configuration
    config = TTSConfig(
        # Configure based on environment or use dummy values for testing
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY"),
        sarvam_api_key=os.getenv("SARVAM_API_KEY"),
        timeout_seconds=5  # Shorter timeout for testing
    )

    # Test text samples
    test_texts = {
        "english": "Hello, this is a test of the oceanographic data system.",
        "hindi": "नमस्ते, यह समुद्री डेटा सिस्टम का परीक्षण है।",
        "mixed": "Hello नमस्ते, ocean data मिला है।"
    }

    service = MultiTierTTSService(config)

    for language, text in test_texts.items():
        logger.info(f"\n--- Testing {language} text ---")
        logger.info(f"Text: {text}")

        try:
            # Test synthesis
            audio_data = await service.synthesize(text, "hi-IN" if "hindi" in language else "en-US")

            if audio_data:
                logger.success(f"✅ {language} synthesis successful: {len(audio_data)} bytes")

                # Save test audio file
                output_dir = Path("test_audio_output")
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / f"test_{language}.wav"

                with open(output_file, "wb") as f:
                    f.write(audio_data)
                logger.info(f"Saved test audio: {output_file}")

            else:
                logger.error(f"❌ {language} synthesis failed")

        except Exception as e:
            logger.error(f"❌ {language} synthesis error: {e}")


async def test_fallback_behavior():
    """Test fallback behavior with simulated failures"""
    logger.info("\n=== Testing Fallback Behavior ===")

    # Test with only one service configured at a time
    configs = [
        {
            "name": "ElevenLabs Only",
            "config": TTSConfig(
                elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
                elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
                prefer_elevenlabs=True
            )
        },
        {
            "name": "Deepgram Only",
            "config": TTSConfig(
                deepgram_api_key=os.getenv("DEEPGRAM_API_KEY"),
                prefer_deepgram=True
            )
        },
        {
            "name": "Sarvam Only",
            "config": TTSConfig(
                sarvam_api_key=os.getenv("SARVAM_API_KEY"),
                prefer_sarvam=True
            )
        },
        {
            "name": "Multi-tier Fallback",
            "config": create_tts_config_from_env()
        }
    ]

    test_text = "Testing the fallback system for oceanographic data queries."

    for test_case in configs:
        logger.info(f"\n--- {test_case['name']} ---")

        service = MultiTierTTSService(test_case['config'])
        status = service.get_service_status()

        logger.info(f"Service status: {status}")

        try:
            audio_data = await service.synthesize(test_text)

            if audio_data:
                logger.success(f"✅ {test_case['name']} successful: {len(audio_data)} bytes")
            else:
                logger.warning(f"⚠️ {test_case['name']} returned no data")

        except Exception as e:
            logger.error(f"❌ {test_case['name']} error: {e}")


async def test_language_specific_routing():
    """Test language-specific TTS routing"""
    logger.info("\n=== Testing Language-Specific Routing ===")

    config = create_tts_config_from_env()
    service = MultiTierTTSService(config)

    language_tests = [
        {
            "language": "en-US",
            "text": "The ocean temperature data shows interesting patterns.",
            "expected_priority": "Should prefer ElevenLabs or Deepgram"
        },
        {
            "language": "hi-IN",
            "text": "समुद्री तापमान डेटा दिलचस्प पैटर्न दिखाता है।",
            "expected_priority": "Should prefer Sarvam TTS"
        },
        {
            "language": "en-IN",
            "text": "Ocean data analysis is very important for research.",
            "expected_priority": "Could use any service"
        }
    ]

    for test in language_tests:
        logger.info(f"\n--- Language: {test['language']} ---")
        logger.info(f"Text: {test['text']}")
        logger.info(f"Expected: {test['expected_priority']}")

        try:
            audio_data = await service.synthesize(test['text'], test['language'])

            if audio_data:
                logger.success(f"✅ Synthesis successful: {len(audio_data)} bytes")
            else:
                logger.error(f"❌ Synthesis failed")

        except Exception as e:
            logger.error(f"❌ Error: {e}")


async def test_configuration_validation():
    """Test configuration validation"""
    logger.info("\n=== Testing Configuration Validation ===")

    # Test various configuration scenarios
    test_configs = [
        {
            "name": "No API Keys",
            "config": TTSConfig()
        },
        {
            "name": "Partial ElevenLabs Config",
            "config": TTSConfig(elevenlabs_api_key="test_key")  # Missing voice_id
        },
        {
            "name": "Valid Sarvam Config",
            "config": TTSConfig(sarvam_api_key=os.getenv("SARVAM_API_KEY") or "test_key")
        }
    ]

    for test_case in test_configs:
        logger.info(f"\n--- {test_case['name']} ---")

        service = MultiTierTTSService(test_case['config'])
        status = service.get_service_status()

        logger.info(f"Configuration status:")
        for provider, provider_status in status.items():
            if isinstance(provider_status, dict):
                configured = provider_status.get("configured", False)
                status_icon = "✅" if configured else "❌"
                logger.info(f"  {status_icon} {provider}: {provider_status}")


async def test_performance_characteristics():
    """Test performance characteristics of TTS services"""
    logger.info("\n=== Testing Performance Characteristics ===")

    config = create_tts_config_from_env()
    service = MultiTierTTSService(config)

    # Test with different text lengths
    test_cases = [
        "Short text.",
        "This is a medium length text that should test the normal use case for voice responses in our oceanographic data system.",
        """This is a very long text that tests how the TTS services handle larger content.
        It includes multiple sentences and should help us understand the performance characteristics
        of each service when dealing with longer responses from the AGNO agent. This type of content
        might be generated when providing detailed explanations about oceanographic float data,
        temperature profiles, or salinity measurements."""
    ]

    for i, text in enumerate(test_cases, 1):
        logger.info(f"\n--- Test Case {i}: {len(text)} characters ---")
        logger.info(f"Text preview: {text[:100]}...")

        import time
        start_time = time.time()

        try:
            audio_data = await service.synthesize(text)

            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds

            if audio_data:
                logger.success(f"✅ Synthesis completed in {duration:.2f}ms")
                logger.info(f"Audio size: {len(audio_data)} bytes")
                logger.info(f"Efficiency: {len(audio_data)/duration:.2f} bytes/ms")
            else:
                logger.error(f"❌ Synthesis failed after {duration:.2f}ms")

        except Exception as e:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            logger.error(f"❌ Error after {duration:.2f}ms: {e}")


async def main():
    """Run all TTS tests"""
    logger.info("Starting Multi-Tier TTS Service Tests")
    logger.info("=" * 50)

    # Check environment variables
    required_vars = ["SARVAM_API_KEY"]  # Sarvam is the main addition
    optional_vars = ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "DEEPGRAM_API_KEY"]

    logger.info("Environment Check:")
    for var in required_vars + optional_vars:
        value = os.getenv(var)
        status = "✅ Set" if value else "❌ Not set"
        is_required = var in required_vars
        logger.info(f"  {var}: {status} {'(Required)' if is_required else '(Optional)'}")

    # Run tests
    try:
        await test_configuration_validation()
        await test_individual_tts_services()
        await test_language_specific_routing()
        await test_fallback_behavior()
        await test_performance_characteristics()

        logger.success("\n🎉 All TTS tests completed!")

    except KeyboardInterrupt:
        logger.warning("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Test suite error: {e}")


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())