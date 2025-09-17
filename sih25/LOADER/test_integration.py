#!/usr/bin/env python3
"""
Test suite for DATA LOADER integration
Tests the Parquet to PostgreSQL loading functionality
"""

import os
import sys
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sih25.LOADER.database import DatabaseManager, DatabaseConfig
from sih25.LOADER.data_loader import load_parquet_to_postgres


class MockDatabaseConfig:
    """Mock database config for testing"""
    def __init__(self):
        self.database_url = "postgresql://test:test@localhost:5432/test"
        self.host = "localhost"
        self.port = 5432
        self.database = "test"
        self.user = "test"
        self.password = "test"
        self.min_connections = 1
        self.max_connections = 2
        self.max_inactive_connection_lifetime = 60.0


async def test_database_manager_initialization():
    """Test database manager initialization"""
    print("Testing database manager initialization...")

    with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost:5432/test'}):
        config = DatabaseConfig()
        manager = DatabaseManager(config)

        # Mock the pool creation
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # Mock connection for health check
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

            await manager.initialize()

            assert manager._pool == mock_pool
            mock_create_pool.assert_called_once()
            print("✓ Database manager initialization test passed")


async def test_parquet_loading_logic():
    """Test the core Parquet loading logic without actual database"""
    print("Testing Parquet loading logic...")

    # Create temporary test data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock Parquet data
        import pandas as pd

        # Mock data matching DATAOPS output format
        test_data = pd.DataFrame({
            'file_name': ['test.nc'] * 5,
            'float_id': ['TEST01'] * 5,
            'profile_idx': [0] * 5,
            'data_mode': ['D'] * 5,
            'timestamp': [None] * 5,
            'latitude': [14.926] * 5,
            'longitude': [88.67] * 5,
            'cycle_number': [1] * 5,
            'level_idx': [0, 1, 2, 3, 4],
            'pres_qc': ['1'] * 5,
            'pres': [5.0, 10.0, 20.0, 30.0, 50.0],
            'pres_error': [0.1] * 5,
            'temp_qc': ['1'] * 5,
            'temp': [25.5, 25.3, 25.0, 24.8, 24.5],
            'temp_error': [0.01] * 5,
            'psal_qc': ['1'] * 5,
            'psal': [34.5, 34.6, 34.7, 34.8, 34.9],
            'psal_error': [0.01] * 5,
            'depth_m': [5.0, 10.0, 20.0, 30.0, 50.0],
            'n_levels': [5] * 5,
            'max_pressure': [50.0] * 5,
            'temp_range': [1.0] * 5,
            'sal_range': [0.4] * 5
        })

        # Save test data
        test_data.to_parquet(temp_path / "test_data.parquet")

        # Create profiles data
        profiles_data = pd.DataFrame({
            'profile_idx': [0],
            'float_id': ['TEST01'],
            'timestamp': [None],
            'latitude': [14.926],
            'longitude': [88.67],
            'n_levels': [5],
            'max_pressure': [50.0],
            'min_pressure': [5.0],
            'temp_min': [24.5],
            'temp_max': [25.5],
            'temp_mean': [25.0],
            'temp_count': [5],
            'psal_min': [34.5],
            'psal_max': [34.9],
            'psal_mean': [34.7],
            'psal_count': [5]
        })

        profiles_data.to_parquet(temp_path / "test_profiles.parquet")

        # Create quality report
        quality_report = {
            "total_records": 5,
            "completeness": {"temp": {"non_null_count": 5, "completeness_ratio": 1.0}},
            "qc_summary": {"temp_qc": {"1": 5}},
            "coordinate_coverage": {"valid_coordinates": 5, "lat_range": [14.926, 14.926]},
            "parameter_coverage": {"temp": {"available": True, "valid_measurements": 5}}
        }

        with open(temp_path / "test_quality_report.json", 'w') as f:
            json.dump(quality_report, f)

        # Create processing log
        processing_log = {
            "file_prefix": "test",
            "export_timestamp": "2024-01-01T00:00:00",
            "input_records": 5,
            "columns_exported": list(test_data.columns)
        }

        with open(temp_path / "test_processing_log.json", 'w') as f:
            json.dump(processing_log, f)

        print(f"✓ Created test data in {temp_path}")

        # Now test the loading function with mocked database
        with patch('sih25.LOADER.data_loader.get_db_manager') as mock_get_db:
            mock_manager = AsyncMock()
            mock_conn = AsyncMock()

            # Mock the transaction context manager
            mock_manager.get_transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_manager.get_transaction.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_get_db.return_value = mock_manager

            # Test the loading function
            result = await load_parquet_to_postgres(
                parquet_files_dir=str(temp_path),
                file_prefix="test",
                create_tables=False,
                deduplication_strategy="upsert"
            )

            # Verify results
            assert result["floats_processed"] == 1
            assert result["profiles_processed"] == 1
            assert result["observations_processed"] == 20  # 5 records × 4 parameters (pres, temp, psal, doxy - but doxy not in data so 3)

            print("✓ Parquet loading logic test passed")
            print(f"  - Processed {result['floats_processed']} floats")
            print(f"  - Processed {result['profiles_processed']} profiles")
            print(f"  - Processed {result['observations_processed']} observations")


async def test_integration_with_orchestrator():
    """Test integration with the main orchestrator"""
    print("Testing integration with orchestrator...")

    # Mock the import to avoid actual database dependencies
    with patch.dict('sys.modules', {'sih25.LOADER.data_loader': MagicMock()}):
        # Import the orchestrator
        from sih25.DATAOPS.main_orchestrator import argo_data_pipeline

        # Mock all the pipeline steps
        with patch('sih25.DATAOPS.main_orchestrator.explore_argo_schema') as mock_schema, \
             patch('sih25.DATAOPS.main_orchestrator.validate_argo_data') as mock_validate, \
             patch('sih25.DATAOPS.main_orchestrator.preprocess_argo_data') as mock_preprocess, \
             patch('sih25.DATAOPS.main_orchestrator.export_to_parquet') as mock_export, \
             patch('sih25.DATAOPS.main_orchestrator.load_parquet_to_postgres') as mock_load:

            # Set up mocks
            mock_schema.return_value = {"file_type": "argo_core"}

            mock_validation = MagicMock()
            mock_validation.is_valid = True
            mock_validation.valid_records = 5
            mock_validation.dict.return_value = {"is_valid": True}
            mock_validate.return_value = mock_validation

            # Mock processed dataframe
            import pandas as pd
            mock_df = pd.DataFrame({'col1': [1, 2, 3]})
            mock_preprocess.return_value = mock_df

            mock_export.return_value = {
                "data_parquet": "test_data.parquet",
                "profiles_parquet": "test_profiles.parquet"
            }

            mock_load.return_value = {
                "floats_processed": 1,
                "profiles_processed": 1,
                "observations_processed": 15
            }

            # Test the pipeline with database loading enabled
            result = await argo_data_pipeline(
                nc_file_path="test.nc",
                output_dir="test_output",
                skip_validation_errors=False,
                load_to_database=True,
                create_db_tables=True,
                deduplication_strategy="upsert"
            )

            # Verify the pipeline completed successfully
            assert result["status"] == "completed"
            assert "database_loading" in result["steps_completed"]
            assert "database_results" in result

            print("✓ Integration with orchestrator test passed")
            print(f"  - Pipeline status: {result['status']}")
            print(f"  - Steps completed: {result['steps_completed']}")


async def run_all_tests():
    """Run all tests"""
    print("Running DATA LOADER integration tests...\n")

    try:
        await test_database_manager_initialization()
        await test_parquet_loading_logic()
        await test_integration_with_orchestrator()

        print("\n✅ All tests passed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)