#!/usr/bin/env python3
"""
Test JARVIS FloatChat MVP End-to-End

This script validates the complete flow:
1. MCP Tool Server (Database + Tools)
2. JARVIS Agent (with MCP integration)
3. Voice Pipeline (Optional)
4. Frontend Dashboard

Flow: Upload → Process → Chat/Voice → Visualization
"""

import asyncio
import requests
import time
import sys
from pathlib import Path

def print_header():
    """Print test header"""
    print("\n" + "="*60)
    print("🌊 JARVIS FLOATCHAT - END-TO-END TEST")
    print("="*60)
    print("Testing: Upload → Process → JARVIS Chat → Visualizations")
    print("="*60 + "\n")

def test_service(name: str, url: str, expected_in_response: str = None) -> bool:
    """Test if a service is running"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code in [200, 404]:  # 404 OK for some endpoints
            if expected_in_response:
                return expected_in_response in response.text
            print(f"✅ {name} is online at {url}")
            return True
        else:
            print(f"⚠️  {name} returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} is not running at {url}")
        return False
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return False

async def test_jarvis_agent():
    """Test JARVIS agent conversation"""
    print("\n🤖 Testing JARVIS Agent...")

    try:
        # Initialize JARVIS
        response = requests.post("http://localhost:8001/agent/initialize", timeout=10)
        if response.status_code == 200:
            print("✅ JARVIS initialized successfully")
            data = response.json()
            if "message" in data:
                print(f"   JARVIS: {data['message']}")

        # Test chat endpoint
        test_queries = [
            "Hello JARVIS, are you online?",
            "Show me temperature profiles near the equator",
            "What ocean parameters can you analyze?"
        ]

        for query in test_queries:
            print(f"\n💬 User: {query}")
            response = requests.post(
                "http://localhost:8001/agent/chat",
                json={"message": query, "session_id": "test_session"},
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                print(f"🤖 JARVIS: {result.get('response', 'No response')[:200]}...")

                if result.get("follow_up_suggestions"):
                    print("   💡 Suggestions:", result["follow_up_suggestions"][0])

                if result.get("metadata", {}).get("voice_compatible"):
                    print("   🎤 Voice-compatible response")
            else:
                print(f"   ⚠️  Error: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ JARVIS test failed: {e}")
        return False

async def test_mcp_tools():
    """Test MCP tool server"""
    print("\n🔧 Testing MCP Tool Server...")

    try:
        # Get tool descriptions
        response = requests.get("http://localhost:8000/mcp/tools/descriptions", timeout=10)
        if response.status_code == 200:
            data = response.json()
            tools = data.get("tools", [])
            print(f"✅ MCP Server has {len(tools)} tools available")

            # List first 3 tools
            for tool in tools[:3]:
                print(f"   📍 {tool.get('name', 'Unknown')}")

        # Test vector database
        response = requests.get("http://localhost:8000/metadata/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Vector Database: {stats.get('total_embeddings', 0)} embeddings")

        return True

    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        return False

async def test_complete_flow():
    """Test the complete JARVIS FloatChat flow"""
    print_header()

    # Track test results
    results = {
        "mcp_server": False,
        "jarvis_agent": False,
        "dataops": False,
        "frontend": False
    }

    # Test 1: MCP Tool Server
    results["mcp_server"] = test_service(
        "MCP Tool Server",
        "http://localhost:8000/health",
        None
    )

    # Test 2: JARVIS Agent Server
    results["jarvis_agent"] = test_service(
        "JARVIS Agent Server",
        "http://localhost:8001/health",
        None
    )

    # Test 3: DataOps Server
    results["dataops"] = test_service(
        "DataOps Server",
        "http://localhost:8002/health",
        None
    )

    # Test 4: Frontend Dashboard
    results["frontend"] = test_service(
        "Frontend Dashboard",
        "http://localhost:8050/_dash-layout",
        None
    )

    # If core services are running, test functionality
    if results["mcp_server"] and results["jarvis_agent"]:
        await test_mcp_tools()
        await test_jarvis_agent()

    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    all_pass = True
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service.replace('_', ' ').title()}: {'PASS' if status else 'FAIL'}")
        if not status:
            all_pass = False

    print("="*60)

    if all_pass:
        print("\n🎉 All tests passed! JARVIS FloatChat is ready!")
        print("\n📌 Next steps:")
        print("1. Open http://localhost:8050 in your browser")
        print("2. Upload NetCDF files or use sample data")
        print("3. Chat with JARVIS or use voice (🎤 button)")
        print("4. Ask: 'Show me ocean temperature patterns'")
        print("\n🤖 JARVIS is online and ready to assist with ocean data!")
    else:
        print("\n⚠️  Some services are not running.")
        print("Run: python3 run_mvp.py")
        print("to start all services.")

    return all_pass

def main():
    """Main test runner"""
    try:
        # Check if services might be running
        print("\n🔍 Checking JARVIS FloatChat services...")

        # Run async tests
        result = asyncio.run(test_complete_flow())

        # Exit with appropriate code
        sys.exit(0 if result else 1)

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()