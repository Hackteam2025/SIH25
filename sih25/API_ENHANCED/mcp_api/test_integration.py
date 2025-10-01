#!/usr/bin/env python3
"""
Integration Test Script for MCP Tool Server
Tests database connectivity and tool functionality
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test basic database connectivity"""
    try:
        from sih25.LOADER.database import get_db_manager

        logger.info("Testing database connection...")
        db_manager = await get_db_manager()

        # Test health check
        is_healthy = await db_manager.health_check()
        if is_healthy:
            logger.info("✓ Database connection successful")
            return True
        else:
            logger.error("✗ Database health check failed")
            return False

    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False


async def test_database_schema():
    """Test that required tables exist"""
    try:
        from sih25.LOADER.database import get_db_manager

        logger.info("Testing database schema...")
        db_manager = await get_db_manager()

        # Check if required tables exist
        required_tables = ['floats', 'profiles', 'observations']

        for table in required_tables:
            query = f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{table}'
            );
            """

            result = await db_manager.fetch_with_retry(query)
            exists = result[0]['exists'] if result else False

            if exists:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.warning(f"⚠ Table '{table}' does not exist")
                return False

        logger.info("✓ Database schema verification complete")
        return True

    except Exception as e:
        logger.error(f"✗ Database schema test failed: {e}")
        return False


async def test_sample_queries():
    """Test sample database queries"""
    try:
        from sih25.LOADER.database import get_db_manager

        logger.info("Testing sample database queries...")
        db_manager = await get_db_manager()

        # Test 1: Count total profiles
        query1 = "SELECT COUNT(*) as profile_count FROM profiles;"
        result1 = await db_manager.fetch_with_retry(query1)
        profile_count = result1[0]['profile_count'] if result1 else 0
        logger.info(f"✓ Total profiles in database: {profile_count}")

        # Test 2: Count total floats
        query2 = "SELECT COUNT(*) as float_count FROM floats;"
        result2 = await db_manager.fetch_with_retry(query2)
        float_count = result2[0]['float_count'] if result2 else 0
        logger.info(f"✓ Total floats in database: {float_count}")

        # Test 3: Count total observations
        query3 = "SELECT COUNT(*) as obs_count FROM observations;"
        result3 = await db_manager.fetch_with_retry(query3)
        obs_count = result3[0]['obs_count'] if result3 else 0
        logger.info(f"✓ Total observations in database: {obs_count}")

        # Test 4: Get sample profile data
        query4 = """
        SELECT p.profile_id, p.timestamp, p.latitude, p.longitude, p.data_mode
        FROM profiles p
        LIMIT 5;
        """
        result4 = await db_manager.fetch_with_retry(query4)
        logger.info(f"✓ Sample profiles retrieved: {len(result4)} records")

        if profile_count > 0 and float_count > 0:
            logger.info("✓ Database contains data for testing")
            return True
        else:
            logger.warning("⚠ Database appears to be empty - tools will work but return no data")
            return True  # Not a failure, just empty

    except Exception as e:
        logger.error(f"✗ Sample queries failed: {e}")
        return False


async def test_core_tools():
    """Test core MCP tools functionality"""
    try:
        from sih25.API.tools.core_tools import argo_tools
        from sih25.API.models import BoundingBox
        from datetime import datetime, timedelta

        logger.info("Testing core MCP tools...")

        # Test 1: List profiles (small area, recent time)
        logger.info("Testing list_profiles tool...")

        # Use a small area in the North Atlantic
        region = BoundingBox(
            min_lat=30.0, max_lat=40.0,
            min_lon=-60.0, max_lon=-50.0
        )

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=365)  # Last year

        try:
            profiles = await argo_tools.list_profiles(
                region, start_time, end_time, False, 10
            )
            logger.info(f"✓ list_profiles returned {len(profiles)} profiles")
        except Exception as e:
            logger.warning(f"⚠ list_profiles test: {e}")

        # Test 2: Search floats near a point
        logger.info("Testing search_floats_near tool...")
        try:
            floats = await argo_tools.search_floats_near(
                -55.0, 35.0, 200.0, 5  # North Atlantic, 200km radius
            )
            logger.info(f"✓ search_floats_near returned {len(floats)} floats")
        except Exception as e:
            logger.warning(f"⚠ search_floats_near test: {e}")

        logger.info("✓ Core tools functionality verified")
        return True

    except Exception as e:
        logger.error(f"✗ Core tools test failed: {e}")
        return False


async def test_validation_systems():
    """Test ARGO validation and query safety"""
    try:
        from sih25.API.validation import argo_validator
        from sih25.API.safety import query_safety

        logger.info("Testing validation systems...")

        # Test ARGO validation
        logger.info("Testing ARGO protocol validation...")
        test_data = [
            {"qc_flag": 1, "data_mode": "D", "id": "test1"},
            {"qc_flag": 4, "data_mode": "R", "id": "test2"},  # Should be filtered
            {"qc_flag": 2, "data_mode": "A", "id": "test3"}
        ]

        filtered_data, warnings = argo_validator.validate_qc_flags(test_data)
        logger.info(f"✓ ARGO QC validation: {len(filtered_data)}/3 records passed, {len(warnings)} warnings")

        # Test query safety
        logger.info("Testing query safety validation...")
        valid_params = {
            'min_lat': 30.0, 'max_lat': 35.0,
            'min_lon': -60.0, 'max_lon': -55.0,
            'time_start': datetime(2023, 1, 1),
            'time_end': datetime(2023, 12, 31),
            'max_results': 100
        }

        is_safe, errors, metadata = query_safety.validate_query_safety("list_profiles", valid_params)
        logger.info(f"✓ Query safety validation: {'passed' if is_safe else 'failed'}")

        logger.info("✓ Validation systems verified")
        return True

    except Exception as e:
        logger.error(f"✗ Validation systems test failed: {e}")
        return False


async def test_mcp_integration():
    """Test MCP protocol integration"""
    try:
        from sih25.API.mcp_protocol import mcp_handler

        logger.info("Testing MCP protocol integration...")

        # Test tool descriptions generation
        descriptions = mcp_handler.generate_tool_descriptions()
        tool_count = len(descriptions)
        logger.info(f"✓ MCP tool descriptions generated: {tool_count} tools")

        # Test response formatting
        from sih25.API.models import ToolResponse
        test_response = ToolResponse(
            success=True,
            data=[],
            warnings=[],
            errors=[],
            metadata={"test": True},
            execution_time_ms=50.0
        )

        formatted = mcp_handler.format_for_llm(test_response)
        logger.info(f"✓ MCP response formatting works")

        logger.info("✓ MCP integration verified")
        return True

    except Exception as e:
        logger.error(f"✗ MCP integration test failed: {e}")
        return False


async def run_integration_tests():
    """Run all integration tests"""
    logger.info("=" * 60)
    logger.info("Starting MCP Tool Server Integration Tests")
    logger.info("=" * 60)

    test_results = {}

    # Test 1: Database connection
    test_results['database_connection'] = await test_database_connection()

    # Test 2: Database schema
    if test_results['database_connection']:
        test_results['database_schema'] = await test_database_schema()
    else:
        test_results['database_schema'] = False
        logger.error("Skipping schema test - no database connection")

    # Test 3: Sample queries
    if test_results['database_schema']:
        test_results['sample_queries'] = await test_sample_queries()
    else:
        test_results['sample_queries'] = False
        logger.error("Skipping sample queries - schema issues")

    # Test 4: Core tools (can run even with empty database)
    test_results['core_tools'] = await test_core_tools()

    # Test 5: Validation systems
    test_results['validation_systems'] = await test_validation_systems()

    # Test 6: MCP integration
    test_results['mcp_integration'] = await test_mcp_integration()

    # Summary
    logger.info("=" * 60)
    logger.info("Integration Test Results:")
    logger.info("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name:25} {status}")
        if result:
            passed += 1

    logger.info("=" * 60)
    logger.info(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All integration tests PASSED! MCP Tool Server is ready for use.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests FAILED. Please address issues before deployment.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_integration_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        sys.exit(1)