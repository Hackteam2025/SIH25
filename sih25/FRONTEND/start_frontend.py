"""
FloatChat Frontend Startup Script

This script starts the frontend dashboard that integrates with existing services:
- AGENT API (port 8001) - AGNO agent with voice capabilities
- MCP API (port 8000) - Tool server for data operations
- DataOps API (port 8002) - Data processing orchestrator
"""

import subprocess
import sys
import time
import requests
import os
from pathlib import Path

def check_service(url, name):
    """Check if a service is running"""
    try:
        response = requests.get(f"{url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def wait_for_services():
    """Wait for backend services to be available"""
    services = [
        ("http://localhost:8001", "Agent API"),
        ("http://localhost:8000", "MCP Tool Server"),
        ("http://localhost:8002", "DataOps Orchestrator")
    ]

    print("🔍 Checking backend services...")

    for url, name in services:
        if check_service(url, name):
            print(f"✅ {name} is running")
        else:
            print(f"⚠️  {name} not detected - will run in offline mode")

    print()

def start_frontend():
    """Start the FloatChat frontend"""
    print("🚀 Starting FloatChat Frontend Dashboard...")
    print("🌐 Dashboard will be available at: http://localhost:8050")
    print()
    print("Features:")
    print("  🎤 Voice AI integration (AGNO voice handler)")
    print("  🤖 AI Oceanographer chat interface")
    print("  📊 Interactive oceanographic visualizations")
    print("  🗂️  NetCDF file processing")
    print("  🔄 Real-time data exploration")
    print()

    # Change to frontend directory
    frontend_dir = Path(__file__).parent
    os.chdir(frontend_dir)

    # Start the Dash app
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 FloatChat Frontend stopped")
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")

if __name__ == "__main__":
    print("🌊 FloatChat - AI-Powered Oceanographic Data Explorer")
    print("=" * 55)

    wait_for_services()
    start_frontend()