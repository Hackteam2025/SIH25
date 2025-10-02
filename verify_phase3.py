#!/usr/bin/env python3
"""
Quick verification script for Phase 3 Voice AI implementation
Tests all components without actually starting the services
"""

import os
import sys
from pathlib import Path

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_env_var(var_name: str) -> bool:
    """Check if environment variable exists"""
    value = os.getenv(var_name)
    if value:
        # Mask API keys for security
        if 'KEY' in var_name or 'TOKEN' in var_name:
            masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            print(f"  {GREEN}✓{RESET} {var_name}: {masked}")
        else:
            print(f"  {GREEN}✓{RESET} {var_name}: {value}")
        return True
    else:
        print(f"  {RED}✗{RESET} {var_name}: NOT SET")
        return False

def check_file_exists(filepath: str) -> bool:
    """Check if file exists"""
    if Path(filepath).exists():
        print(f"  {GREEN}✓{RESET} {filepath}")
        return True
    else:
        print(f"  {RED}✗{RESET} {filepath} NOT FOUND")
        return False

def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Phase 3 Voice AI - Implementation Verification{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    all_checks_passed = True

    # Check 1: Environment Variables
    print(f"{YELLOW}1. Checking Environment Variables...{RESET}")
    env_vars = [
        "GROQ_API_KEY",
        "GROQ_MODEL_NAME",
        "SONIOX_API_KEY",
        "SARVAM_API_KEY",
        "SARVAM_TARGET_LANGUAGE",
        "SARVAM_SPEAKER",
        "DAILY_API_KEY",
        "DAILY_ROOM_URL"
    ]

    for var in env_vars:
        if not check_env_var(var):
            all_checks_passed = False
    print()

    # Check 2: Backend Files
    print(f"{YELLOW}2. Checking Backend Files...{RESET}")
    backend_files = [
        "sih25/VOICE_AI/pipecat_bot.py",
        "sih25/VOICE_AI/api.py",
        "sih25/VOICE_AI/tts_services.py",
        "sih25/VOICE_AI/config.py"
    ]

    for file in backend_files:
        if not check_file_exists(file):
            all_checks_passed = False
    print()

    # Check 3: Frontend Files
    print(f"{YELLOW}3. Checking Frontend Files...{RESET}")
    frontend_files = [
        "sih25/FRONTEND_REACT/src/components/voice/PipecatVoiceChat.tsx",
        "sih25/FRONTEND_REACT/src/components/ChatInterface.tsx",
        "sih25/FRONTEND_REACT/.env"
    ]

    for file in frontend_files:
        if not check_file_exists(file):
            all_checks_passed = False
    print()

    # Check 4: Python Dependencies
    print(f"{YELLOW}4. Checking Python Dependencies...{RESET}")
    try:
        import pipecat
        print(f"  {GREEN}✓{RESET} pipecat: {pipecat.__version__}")
    except ImportError:
        print(f"  {RED}✗{RESET} pipecat: NOT INSTALLED")
        all_checks_passed = False

    try:
        import groq
        print(f"  {GREEN}✓{RESET} groq: installed")
    except ImportError:
        print(f"  {RED}✗{RESET} groq: NOT INSTALLED")
        all_checks_passed = False

    try:
        import aiohttp
        print(f"  {GREEN}✓{RESET} aiohttp: {aiohttp.__version__}")
    except ImportError:
        print(f"  {RED}✗{RESET} aiohttp: NOT INSTALLED")
        all_checks_passed = False
    print()

    # Check 5: React Dependencies
    print(f"{YELLOW}5. Checking React Dependencies...{RESET}")
    package_json = Path("sih25/FRONTEND_REACT/package.json")
    if package_json.exists():
        import json
        with open(package_json) as f:
            data = json.load(f)
            deps = data.get("dependencies", {})

            required_deps = [
                "@pipecat-ai/client-js",
                "@pipecat-ai/client-react",
                "@pipecat-ai/daily-transport"
            ]

            for dep in required_deps:
                if dep in deps:
                    print(f"  {GREEN}✓{RESET} {dep}: {deps[dep]}")
                else:
                    print(f"  {RED}✗{RESET} {dep}: NOT INSTALLED")
                    all_checks_passed = False
    else:
        print(f"  {RED}✗{RESET} package.json not found")
        all_checks_passed = False
    print()

    # Summary
    print(f"{BLUE}{'='*60}{RESET}")
    if all_checks_passed:
        print(f"{GREEN}✓ All checks passed! System ready for testing.{RESET}")
        print(f"\n{BLUE}Next Steps:{RESET}")
        print(f"1. Start backend: {YELLOW}python run_mvp.py{RESET}")
        print(f"2. Start frontend: {YELLOW}cd sih25/FRONTEND_REACT && bun run dev{RESET}")
        print(f"3. Open browser: {YELLOW}http://localhost:5173{RESET}")
        print(f"4. Click 'AI Chat' → 'Start Voice AI'\n")
        return 0
    else:
        print(f"{RED}✗ Some checks failed. Please review the errors above.{RESET}\n")
        return 1

if __name__ == "__main__":
    # Load .env file
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    sys.exit(main())
