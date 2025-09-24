#!/usr/bin/env python3
"""
Story 5 Vector Database Test Script
Quick test to verify ChromaDB integration and vector search functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

async def test_vector_store():
    """Test basic vector store functionality"""
    print("🧪 Testing Vector Database Integration...")

    try:
        # Test import
        from sih25.DATAOPS.METADATA.vector_store import get_vector_store
        print("✅ Import successful")

        # Initialize vector store
        vector_store = await get_vector_store()
        print("✅ Vector store initialized")

        # Get initial stats
        stats = vector_store.get_stats()
        print(f"📊 Initial stats: {stats}")

        # Create sample profile data
        sample_profiles = [
            {
                "profile_id": "test_001",
                "float_id": "ARGO_5900001",
                "latitude": 20.5,
                "longitude": 65.2,
                "timestamp": "2024-01-15T12:00:00",
                "parameters": ["temperature", "salinity"],
                "min_depth": 0,
                "max_depth": 2000,
                "qc_summary": "high quality delayed mode data",
                "region": "Arabian Sea"
            },
            {
                "profile_id": "test_002",
                "float_id": "ARGO_5900002",
                "latitude": -5.3,
                "longitude": 80.1,
                "timestamp": "2024-02-20T08:30:00",
                "parameters": ["temperature", "salinity", "oxygen"],
                "min_depth": 0,
                "max_depth": 1500,
                "qc_summary": "good quality real-time data",
                "region": "Indian Ocean"
            }
        ]

        # Add profiles to vector store
        success = await vector_store.add_profiles(sample_profiles)
        if success:
            print("✅ Sample profiles added to vector store")
        else:
            print("❌ Failed to add profiles")
            return False

        # Test semantic search
        print("\n🔍 Testing semantic search...")
        search_results = await vector_store.semantic_search(
            query="warm water tropical profiles",
            limit=5
        )
        print(f"Found {len(search_results)} matches for 'warm water tropical profiles'")
        for result in search_results:
            print(f"  - {result['profile_id']} (similarity: {result['similarity']:.3f})")

        # Test similar profile search
        print("\n🔍 Testing similar profile search...")
        similar_results = await vector_store.find_similar_profiles(
            profile_id="test_001",
            limit=3
        )
        print(f"Found {len(similar_results)} similar profiles to test_001")

        # Final stats
        final_stats = vector_store.get_stats()
        print(f"\n📊 Final stats: {final_stats}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_vector_search_tools():
    """Test vector search tools integration"""
    print("\n🔧 Testing Vector Search Tools...")

    try:
        from sih25.API.tools.vector_search import vector_search_tools
        print("✅ Vector search tools import successful")

        # Test semantic search tool
        response = await vector_search_tools.semantic_search_profiles(
            query="temperature profiles in Arabian Sea",
            limit=3
        )

        if response.success:
            print("✅ Semantic search tool working")
            print(f"   Found {len(response.data.get('profiles', []))} profiles")
        else:
            print("❌ Semantic search tool failed")
            return False

        # Test vector store stats
        stats_response = await vector_search_tools.get_vector_store_stats()
        if stats_response.success:
            print("✅ Vector store stats tool working")
            print(f"   Status: {stats_response.data.get('status', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ Vector search tools test failed: {e}")
        return False

async def test_metadata_processor():
    """Test metadata processor functionality"""
    print("\n📝 Testing Metadata Processor...")

    try:
        from sih25.DATAOPS.METADATA.processor import get_metadata_processor
        print("✅ Metadata processor import successful")

        processor = get_metadata_processor()

        # Test sample metadata creation
        sample_profiles = await processor.create_sample_metadata()
        print(f"✅ Created {len(sample_profiles)} sample metadata entries")

        # Test stats
        stats = await processor.get_processing_stats()
        print(f"📊 Processor stats: {stats.get('status', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ Metadata processor test failed: {e}")
        return False

async def run_tests():
    """Run all tests"""
    print("🚀 Starting Story 5 Vector Database Integration Tests\n")

    # Set environment variable if not present (for testing)
    if not os.getenv("MISTRAL_API_KEY"):
        print("⚠️  MISTRAL_API_KEY not found, will use sentence-transformers fallback")

    test_results = []

    # Run tests
    test_results.append(await test_vector_store())
    test_results.append(await test_vector_search_tools())
    test_results.append(await test_metadata_processor())

    # Summary
    print("\n" + "="*50)
    print("📋 TEST SUMMARY")
    print("="*50)

    tests = [
        "Vector Store Basic Functionality",
        "Vector Search Tools Integration",
        "Metadata Processor Functionality"
    ]

    for i, (test_name, result) in enumerate(zip(tests, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test_name}: {status}")

    all_passed = all(test_results)
    if all_passed:
        print("\n🎉 All tests passed! Story 5 implementation is working correctly.")
        print("\n💡 Next steps:")
        print("   1. Start the MCP server: cd sih25/API && python main.py")
        print("   2. Start the frontend: cd sih25/FRONTEND && python app.py")
        print("   3. Test the vertical split UI for metadata upload")
        print("   4. Try semantic search queries in the chat interface")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")

    return all_passed

if __name__ == "__main__":
    asyncio.run(run_tests())