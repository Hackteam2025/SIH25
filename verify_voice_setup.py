#!/usr/bin/env python3
"""
Quick verification script for Voice AI setup
Run this to check if everything is configured correctly before testing
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).resolve().parent
dotenv_path = project_root / '.env'

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✅ Loaded .env from {dotenv_path}\n")
else:
    print(f"❌ .env file not found at {dotenv_path}\n")
    sys.exit(1)

print("=" * 60)
print("🔍 VOICE AI SETUP VERIFICATION")
print("=" * 60)

# Check required API keys
required_keys = {
    'DAILY_API_KEY': 'Daily.co WebRTC transport',
    'SONIOX_API_KEY': 'Speech-to-Text service',
    'GROQ_API_KEY': 'LLM service',
    'SARVAM_API_KEY': 'Sarvam AI Text-to-Speech (Hindi/English)'
}

print("\n📋 API Keys Status:")
all_keys_present = True
for key, description in required_keys.items():
    value = os.getenv(key)
    if value:
        # Show first 10 chars for security
        print(f"  ✅ {key:20s} ({description})")
        print(f"     → {value[:10]}...")
    else:
        print(f"  ❌ {key:20s} ({description}) - NOT SET")
        all_keys_present = False

# Check file existence
print("\n📁 File Structure:")
files_to_check = [
    'sih25/VOICE_AI/pipecat_bot.py',
    'sih25/VOICE_AI/api.py',
    'sih25/VOICE_AI/tts_services.py',
    'sih25/FRONTEND_REACT/src/components/voice/PipecatVoiceChat.tsx',
    'docs/VOICE_AI_LOGGING_GUIDE.md'
]

all_files_exist = True
for file_path in files_to_check:
    full_path = project_root / file_path
    if full_path.exists():
        print(f"  ✅ {file_path}")
    else:
        print(f"  ❌ {file_path} - MISSING")
        all_files_exist = False

# Check Python dependencies
print("\n📦 Python Dependencies:")
try:
    import pipecat
    print(f"  ✅ pipecat: {pipecat.__version__}")
except ImportError:
    print("  ❌ pipecat - NOT INSTALLED")
    all_files_exist = False

try:
    import fastapi
    print(f"  ✅ fastapi")
except ImportError:
    print("  ❌ fastapi - NOT INSTALLED")
    all_files_exist = False

try:
    import aiohttp
    print(f"  ✅ aiohttp")
except ImportError:
    print("  ❌ aiohttp - NOT INSTALLED")
    all_files_exist = False

# Check import paths (critical fix from earlier)
print("\n🔧 Import Path Verification:")
try:
    from pipecat.services.soniox.stt import SonioxSTTService
    print("  ✅ SonioxSTTService import path correct")
except ImportError as e:
    print(f"  ❌ SonioxSTTService import failed: {e}")
    all_files_exist = False

try:
    from pipecat.services.groq.llm import GroqLLMService
    print("  ✅ GroqLLMService import path correct")
except ImportError as e:
    print(f"  ❌ GroqLLMService import failed: {e}")
    all_files_exist = False

try:
    from pipecat.transports.daily.transport import DailyTransport
    print("  ✅ DailyTransport import path correct")
except ImportError as e:
    print(f"  ❌ DailyTransport import failed: {e}")
    all_files_exist = False

# Summary
print("\n" + "=" * 60)
if all_keys_present and all_files_exist:
    print("✅ ALL CHECKS PASSED - Ready to test Voice AI!")
    print("\nNext steps:")
    print("  1. Start backend: python run_mvp.py")
    print("  2. Open frontend in browser")
    print("  3. Open DevTools Console (F12)")
    print("  4. Click 'Start Voice AI'")
    print("  5. Grant microphone permissions when prompted")
    print("  6. Speak 'hello' and watch for logs")
    print("\nExpected logs when speaking:")
    print("  - 🎤 [User] Started speaking")
    print("  - 👤 [User Transcript]: { text: '...' }")
    print("  - 🤖 [Bot] Started speaking")
else:
    print("❌ ISSUES FOUND - Please fix the above errors before testing")
print("=" * 60)
