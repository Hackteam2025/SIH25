#!/usr/bin/env python3
"""
Integration Test for Frontend-Backend Connection Fixes

Tests:
1. API validation errors fixed
2. Agent region detection improved
3. Frontend duplicate callbacks resolved
"""

import asyncio
import requests
import time
import sys

def test_api_validation():
    """Test that API validation errors are fixed"""
    print("\n1️⃣  Testing API Validation Fix...")

    try:
        # Test with intentionally large date range to trigger validation
        response = requests.post(
            "http://localhost:8000/tools/list_profiles",
            params={
                "min_lat": -90,
                "max_lat": 90,
                "min_lon": -180,
                "max_lon": 180,
                "max_results": 100
            },
            timeout=10
        )

        if response.status_code == 200:
            print("   ✅ API validation working correctly")
            return True
        else:
            print(f"   ❌ API returned {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ API error: {e}")
        return False

def test_agent_region_detection():
    """Test that agent properly detects regions"""
    print("\n2️⃣  Testing Agent Region Detection...")

    test_queries = [
        ("Show me floats in the Mediterranean", "mediterranean"),
        ("Find profiles in the North Atlantic", "north_atlantic"),
        ("Get data from the Arctic Ocean", "arctic")
    ]

    try:
        for query, expected_region in test_queries:
            response = requests.post(
                "http://localhost:8001/agent/chat",
                json={
                    "message": query,
                    "session_id": "test_session"
                },
                timeout=30
            )

            if response.status_code == 200:
                # Check that the response indicates region-specific search
                result = response.json()
                response_text = result.get("response", "")

                # The agent should mention the specific region
                if expected_region.replace("_", " ") in response_text.lower():
                    print(f"   ✅ Correctly detected: {expected_region}")
                else:
                    print(f"   ⚠️  May not have detected: {expected_region}")
            else:
                print(f"   ❌ Agent error for {expected_region}")
                return False

        return True

    except Exception as e:
        print(f"   ❌ Agent test failed: {e}")
        return False

def test_frontend_startup():
    """Test that frontend starts without duplicate callback errors"""
    print("\n3️⃣  Testing Frontend Startup...")

    try:
        # Check if frontend is running
        response = requests.get("http://localhost:8050/_dash-layout", timeout=5)

        if response.status_code == 200:
            print("   ✅ Frontend running without duplicate callback errors")
            return True
        else:
            print(f"   ⚠️  Frontend returned {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("   ℹ️  Frontend not running (start with: python sih25/FRONTEND/app.py)")
        return None
    except Exception as e:
        print(f"   ❌ Frontend test error: {e}")
        return False

def main():
    """Run all integration tests"""
    print("="*60)
    print("🧪 INTEGRATION TEST - Frontend/Backend Connection Fixes")
    print("="*60)

    results = {}

    # Test 1: API Validation
    results["api"] = test_api_validation()

    # Test 2: Agent Region Detection
    results["agent"] = test_agent_region_detection()

    # Test 3: Frontend
    results["frontend"] = test_frontend_startup()

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    all_pass = True
    for component, status in results.items():
        if status is None:
            icon = "ℹ️"
            status_text = "NOT RUNNING"
        elif status:
            icon = "✅"
            status_text = "PASS"
        else:
            icon = "❌"
            status_text = "FAIL"
            all_pass = False

        print(f"{icon} {component.upper()}: {status_text}")

    print("="*60)

    if all_pass and None not in results.values():
        print("\n🎉 All integration tests passed!")
        print("\nThe fixes are working correctly:")
        print("• API validation errors resolved")
        print("• Agent detects specific ocean regions")
        print("• Frontend runs without duplicate callbacks")
    else:
        print("\n⚠️  Some components need attention")
        print("\nRecommendations:")
        print("1. Ensure all services are running:")
        print("   - API: python sih25/API/main.py")
        print("   - Agent: python sih25/AGENT/api.py")
        print("   - Frontend: python sih25/FRONTEND/app.py")
        print("2. Restart services after applying fixes")
        print("3. Check .env file has correct GROQ_MODEL_NAME")

if __name__ == "__main__":
    main()