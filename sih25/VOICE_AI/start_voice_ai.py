#!/usr/bin/env python3
"""
AGNO Voice AI Startup Script

Simple script to launch the voice AI pipeline with proper configuration.
"""

import asyncio
import os
import sys
from pathlib import Path
import argparse

# Add project paths
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))
sys.path.append(str(project_root / "VOICE_AI"))
sys.path.append(str(project_root / "AGENT"))

from loguru import logger
from dotenv import load_dotenv

# Load environment variables
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)
    logger.info(f"Loaded environment from {env_file}")

def setup_logging():
    """Configure logging for voice AI"""
    logger.remove()  # Remove default handler

    # Console logging
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | {message}"
    )

    # File logging
    log_dir = project_root / "logs" / "voice_ai"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "voice_ai_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        format="{time} | {level} | {name}:{line} | {message}"
    )

async def run_voice_pipeline():
    """Run the main voice AI pipeline"""
    try:
        from oceanographic_voice_pipeline import main
        await main()
    except ImportError as e:
        logger.error(f"Failed to import voice pipeline: {e}")
        logger.error("Make sure all dependencies are installed: uv sync")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Voice pipeline error: {e}")
        raise

async def run_tests():
    """Run voice AI tests"""
    try:
        from test_voice_ai import main as test_main
        await test_main()
    except ImportError as e:
        logger.error(f"Failed to import tests: {e}")
        sys.exit(1)

def check_mcp_server():
    """Check if MCP server is running"""
    import aiohttp

    async def check():
        mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{mcp_url}/health") as response:
                    if response.status == 200:
                        logger.info(f"✅ MCP server is running at {mcp_url}")
                        return True
        except Exception:
            pass

        logger.warning(f"⚠️  MCP server not available at {mcp_url}")
        logger.info("Make sure to start the MCP Tool Server first:")
        logger.info("  cd sih25/API && python main.py")
        return False

    return asyncio.run(check())

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AGNO Voice AI Launcher")
    parser.add_argument(
        "command",
        choices=["run", "test", "check"],
        help="Command to execute"
    )
    parser.add_argument(
        "--no-mcp-check",
        action="store_true",
        help="Skip MCP server availability check"
    )

    args = parser.parse_args()

    setup_logging()

    logger.info("🌊 AGNO Voice AI Launcher")
    logger.info("=" * 50)

    # Check MCP server unless skipped
    if not args.no_mcp_check and args.command == "run":
        if not check_mcp_server():
            logger.error("MCP server check failed. Use --no-mcp-check to skip this check.")
            sys.exit(1)

    if args.command == "run":
        logger.info("Starting voice AI pipeline...")
        try:
            asyncio.run(run_voice_pipeline())
        except KeyboardInterrupt:
            logger.info("Voice AI pipeline stopped by user")
        except Exception as e:
            logger.error(f"Voice AI pipeline failed: {e}")
            sys.exit(1)

    elif args.command == "test":
        logger.info("Running voice AI tests...")
        try:
            asyncio.run(run_tests())
        except Exception as e:
            logger.error(f"Tests failed: {e}")
            sys.exit(1)

    elif args.command == "check":
        logger.info("Checking voice AI configuration...")
        mcp_ok = check_mcp_server()

        # Check configuration
        from config import VoiceAIConfig
        config = VoiceAIConfig()
        missing_keys = config.validate_required_keys()

        if missing_keys:
            logger.warning("⚠️  Missing configuration:")
            for key, desc in missing_keys.items():
                logger.warning(f"  {key}: {desc}")
        else:
            logger.info("✅ Configuration looks good")

        logger.info(config.get_summary())

        if mcp_ok and not missing_keys:
            logger.info("🎉 Ready to run voice AI pipeline!")
        else:
            logger.warning("⚠️  Some issues detected. Please resolve before running.")

if __name__ == "__main__":
    main()