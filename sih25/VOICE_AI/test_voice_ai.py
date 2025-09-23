"""
Test and Demo Script for AGNO Voice AI Pipeline

This script provides testing capabilities and a simple demo interface
for the AGNO voice AI integration.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
import json

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from loguru import logger
from config import VoiceAIConfig
from agno_voice_handler import AGNOVoiceHandler


async def test_agno_handler():
    """Test the AGNO voice handler without full pipeline"""
    logger.info("Testing AGNO Voice Handler...")

    try:
        # Initialize handler
        handler = AGNOVoiceHandler()
        await handler.initialize_agent()

        # Test queries
        test_queries = [
            "Show me temperature profiles near the equator",
            "What salinity data do you have for the Mediterranean?",
            "Find floats that measured temperature in 2023",
            "Tell me about BGC measurements in the Atlantic"
        ]

        for query in test_queries:
            logger.info(f"\nTesting query: {query}")
            response = await handler.process_user_input(query)
            logger.info(f"Response: {response[:100]}...")

        logger.info("✅ AGNO Voice Handler test completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ AGNO Voice Handler test failed: {e}")
        return False


async def test_voice_processor():
    """Test the voice response processor"""
    from agno_voice_handler import AGNOVoiceProcessor

    logger.info("Testing Voice Response Processor...")

    processor = AGNOVoiceProcessor()

    # Test responses with various formats
    test_responses = [
        "<think>Processing query...</think>Here are the temperature profiles for the equatorial region.",
        "```json\n{\"profile_id\": 12345}\n```\nI found 3 temperature profiles 🌊",
        "Profile ID: 67890 shows salinity measurements between 34-36 PSU.",
        "The ARGO float data indicates temperature ranges from 15°C to 28°C across different depths."
    ]

    for response in test_responses:
        logger.info(f"\nOriginal: {response}")
        cleaned = processor.clean_for_voice(response)
        voice_friendly = processor.add_voice_friendly_context(cleaned)
        logger.info(f"Voice-friendly: {voice_friendly}")

    logger.info("✅ Voice Response Processor test completed")
    return True


def check_dependencies():
    """Check if required dependencies are available"""
    logger.info("Checking dependencies...")

    dependencies = {
        "pipecat": False,
        "agno": False,
        "mcp_client": False
    }

    # Check Pipecat
    try:
        import pipecat
        dependencies["pipecat"] = True
        logger.info("✅ Pipecat available")
    except ImportError:
        logger.error("❌ Pipecat not available - install with: uv add pipecat-ai")

    # Check AGNO agent
    try:
        sys.path.append(str(project_root / "AGENT"))
        from float_chat_agent import FloatChatAgent
        dependencies["agno"] = True
        logger.info("✅ AGNO agent available")
    except ImportError as e:
        logger.error(f"❌ AGNO agent not available: {e}")

    # Check MCP client capability
    try:
        import aiohttp
        dependencies["mcp_client"] = True
        logger.info("✅ MCP client dependencies available")
    except ImportError:
        logger.error("❌ MCP client dependencies not available")

    return all(dependencies.values())


def check_configuration():
    """Check voice AI configuration"""
    logger.info("Checking configuration...")

    config = VoiceAIConfig()
    missing_keys = config.validate_required_keys()

    if missing_keys:
        logger.warning("⚠️  Missing configuration keys:")
        for key, description in missing_keys.items():
            logger.warning(f"  {key}: {description}")
        logger.info("Note: Some features may not work without proper API keys")
    else:
        logger.info("✅ All required configuration keys present")

    logger.info(config.get_summary())

    return len(missing_keys) == 0


async def interactive_demo():
    """Run an interactive demo of the voice AI system"""
    logger.info("Starting interactive demo...")

    try:
        # Initialize handler
        handler = AGNOVoiceHandler()
        await handler.initialize_agent()

        logger.info("\n🎤 AGNO Voice AI Demo")
        logger.info("Type your oceanographic queries (or 'quit' to exit):")

        while True:
            try:
                query = input("\nYou: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break

                if not query:
                    continue

                logger.info("Processing...")
                response = await handler.process_user_input(query)
                print(f"\nAGNO: {response}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error processing query: {e}")

        logger.info("Demo completed")

    except Exception as e:
        logger.error(f"Demo failed to start: {e}")


async def main():
    """Main test and demo function"""
    logger.info("🌊 AGNO Voice AI Test Suite")

    # Check dependencies
    deps_ok = check_dependencies()
    if not deps_ok:
        logger.error("❌ Dependency check failed. Please install missing dependencies.")
        return

    # Check configuration
    config_ok = check_configuration()

    # Run tests
    logger.info("\n" + "="*50)
    logger.info("Running Tests")
    logger.info("="*50)

    # Test voice processor (doesn't require external services)
    processor_ok = await test_voice_processor()

    # Test AGNO handler (requires MCP server)
    handler_ok = await test_agno_handler()

    # Summary
    logger.info("\n" + "="*50)
    logger.info("Test Summary")
    logger.info("="*50)
    logger.info(f"Dependencies: {'✅' if deps_ok else '❌'}")
    logger.info(f"Configuration: {'✅' if config_ok else '⚠️'}")
    logger.info(f"Voice Processor: {'✅' if processor_ok else '❌'}")
    logger.info(f"AGNO Handler: {'✅' if handler_ok else '❌'}")

    if all([deps_ok, processor_ok, handler_ok]):
        logger.info("\n🎉 All tests passed! Ready for voice pipeline.")

        # Offer interactive demo
        demo_choice = input("\nRun interactive demo? (y/n): ").strip().lower()
        if demo_choice in ['y', 'yes']:
            await interactive_demo()
    else:
        logger.error("\n❌ Some tests failed. Please resolve issues before running voice pipeline.")


if __name__ == "__main__":
    asyncio.run(main())