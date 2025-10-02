#!/usr/bin/env python3
"""
Data Loader Core Functionality
Loads processed ARGO data from Parquet files into PostgreSQL database
Following the three-table schema: floats, profiles, observations
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from prefect import task, get_run_logger

try:
    from .database import DatabaseManager, get_db_manager
except ImportError:
    # Handle when run directly
    from database import DatabaseManager, get_db_manager


@task(name="load-parquet-to-postgres")
async def load_parquet_to_postgres(
    parquet_files_dir: str,
    file_prefix: str,
    create_tables: bool = True,
    deduplication_strategy: str = "upsert"
) -> Dict[str, Any]:
    """
    Load Parquet files from DATAOPS into PostgreSQL database

    Args:
        parquet_files_dir: Directory containing Parquet files
        file_prefix: Prefix of the files to load (e.g., "D2900765_067")
        create_tables: Whether to create tables if they don't exist
        deduplication_strategy: "upsert" or "ignore" for handling duplicates

    Returns:
        Dictionary with loading results and statistics
    """
    logger = get_run_logger()

    # Paths to expected files
    data_parquet = Path(parquet_files_dir) / f"{file_prefix}_data.parquet"
    profiles_parquet = Path(parquet_files_dir) / f"{file_prefix}_profiles.parquet"
    quality_report = Path(parquet_files_dir) / f"{file_prefix}_quality_report.json"
    processing_log = Path(parquet_files_dir) / f"{file_prefix}_processing_log.json"

    # Verify files exist
    if not data_parquet.exists():
        raise FileNotFoundError(f"Data parquet file not found: {data_parquet}")

    logger.info(f"Loading data from {file_prefix} into PostgreSQL...")

    try:
        # Get database manager
        db_manager = await get_db_manager()

        # Create tables if requested
        if create_tables:
            await db_manager.create_tables_if_not_exist()

        # Load Parquet data
        logger.info("Reading Parquet files...")
        data_df = pd.read_parquet(data_parquet)

        profiles_df = None
        if profiles_parquet.exists():
            profiles_df = pd.read_parquet(profiles_parquet)

        # Load metadata files
        quality_data = {}
        processing_data = {}

        if quality_report.exists():
            with open(quality_report, 'r') as f:
                quality_data = json.load(f)

        if processing_log.exists():
            with open(processing_log, 'r') as f:
                processing_data = json.load(f)

        logger.info(f"Loaded {len(data_df)} data records")
        if profiles_df is not None:
            logger.info(f"Loaded {len(profiles_df)} profile records")

        # Check if this is metadata
        if 'file_type' in data_df.columns and (data_df['file_type'] == 'metadata').any():
            logger.info("Detected metadata file - skipping observation data loading")
            return {
                "floats_processed": 0,
                "profiles_processed": 0,
                "observations_processed": 0,
                "metadata_processed": len(data_df),
                "message": "Metadata file processed (stored in parquet only)"
            }

        # Process and insert data
        results = await _process_and_insert_data(
            db_manager=db_manager,
            data_df=data_df,
            profiles_df=profiles_df,
            quality_data=quality_data,
            processing_data=processing_data,
            deduplication_strategy=deduplication_strategy
        )

        logger.info(f"Data loading completed successfully")
        logger.info(f"  - Floats processed: {results['floats_processed']}")
        logger.info(f"  - Profiles processed: {results['profiles_processed']}")
        logger.info(f"  - Observations processed: {results['observations_processed']}")

        return results

    except Exception as e:
        logger.error(f"Failed to load data into PostgreSQL: {e}")
        raise


async def _process_and_insert_data(
    db_manager: DatabaseManager,
    data_df: pd.DataFrame,
    profiles_df: Optional[pd.DataFrame],
    quality_data: Dict[str, Any],
    processing_data: Dict[str, Any],
    deduplication_strategy: str
) -> Dict[str, Any]:
    """Process dataframes and insert into PostgreSQL tables"""

    logger = get_run_logger()

    # Extract unique floats
    floats_data = _extract_floats_data(data_df, quality_data, processing_data)

    # Extract profiles data
    profiles_data = _extract_profiles_data(data_df, profiles_df)

    # Extract observations data
    observations_data = _extract_observations_data(data_df)

    # Insert data with separate transactions for better error handling
    # Insert floats and profiles together since they have foreign key relationship
    async with db_manager.get_transaction() as conn:
        # Insert floats
        floats_processed = await _insert_floats(
            conn, floats_data, deduplication_strategy
        )

        # Insert profiles
        profiles_processed = await _insert_profiles(
            conn, profiles_data, deduplication_strategy
        )

    # Insert observations using individual connections to avoid transaction rollback issues
    observations_processed = await _insert_observations_individually(
        db_manager, observations_data, deduplication_strategy
    )

    return {
        "floats_processed": floats_processed,
        "profiles_processed": profiles_processed,
        "observations_processed": observations_processed,
        "deduplication_strategy": deduplication_strategy,
        "processing_timestamp": datetime.now().isoformat()
    }


async def _insert_observations_individually(
    db_manager: DatabaseManager,
    observations_data: List[Dict[str, Any]],
    strategy: str
) -> int:
    """Insert observations data one by one to avoid transaction rollback issues"""

    if not observations_data:
        return 0

    logger = get_run_logger()
    count = 0

    # First, ensure the unique constraint exists
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("""
                ALTER TABLE observations
                ADD CONSTRAINT observations_unique_key
                UNIQUE (profile_id, depth, parameter)
            """)
    except Exception:
        # Constraint likely already exists
        pass

    if strategy == "upsert":
        query = """
            INSERT INTO observations (profile_id, depth, parameter, value, qc_flag)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT ON CONSTRAINT observations_unique_key
            DO UPDATE SET
                value = EXCLUDED.value,
                qc_flag = EXCLUDED.qc_flag,
                created_at = NOW()
        """
    else:  # ignore
        query = """
            INSERT INTO observations (profile_id, depth, parameter, value, qc_flag)
            SELECT $1, $2, $3, $4, $5
            WHERE NOT EXISTS (
                SELECT 1 FROM observations
                WHERE profile_id = $1 AND depth = $2 AND parameter = $3
            )
        """

    # Insert each observation with its own connection to avoid transaction rollback
    for obs_data in observations_data:
        try:
            # Validate the data before insertion
            if obs_data["depth"] is None or obs_data["value"] is None:
                logger.warning(f"Skipping observation with null depth or value: {obs_data}")
                continue

            async with db_manager.get_connection() as conn:
                await conn.execute(
                    query,
                    obs_data["profile_id"],
                    obs_data["depth"],
                    obs_data["parameter"],
                    obs_data["value"],
                    obs_data["qc_flag"]
                )
                count += 1
        except Exception as e:
            # Log but continue with other observations
            logger.warning(f"Failed to insert observation {obs_data.get('parameter', 'unknown')} at depth {obs_data.get('depth', 'unknown')}: {e}")
            continue

    return count


def _clean_string_for_postgres(value) -> str:
    """
    Clean string data for PostgreSQL insertion.
    PostgreSQL cannot handle null bytes (0x00) in text fields.

    Args:
        value: Any value to be converted to a clean string

    Returns:
        Cleaned string safe for PostgreSQL insertion
    """
    if value is None:
        return ""

    # Convert to string
    text = str(value)

    # Remove null bytes (0x00) which PostgreSQL cannot handle in text fields
    text = text.replace('\x00', '')

    # Remove other potentially problematic control characters (including 0x03, 0x19, 0x01)
    for i in range(32):  # Remove all control characters (0x00-0x1F)
        text = text.replace(chr(i), '')

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def _extract_float_id_from_data(row) -> str:
    """
    Extract a clean float ID from the data row.
    Handles cases where float_id field is corrupted or contains binary data.

    Args:
        row: Pandas row containing the data

    Returns:
        Clean float ID string
    """
    # First try to clean the existing float_id
    if 'float_id' in row and pd.notna(row['float_id']):
        cleaned_id = _clean_string_for_postgres(row['float_id'])
        # Check if the cleaned ID is meaningful (non-empty and not just spaces)
        if cleaned_id and not cleaned_id.isspace() and len(cleaned_id) > 1:
            return cleaned_id

    # Fallback: Extract from filename
    if 'file_name' in row and pd.notna(row['file_name']):
        filename = str(row['file_name']).replace('.nc', '')
        # Handle formats like "D2900765_067.nc" -> "D2900765"
        if '_' in filename:
            return filename.split('_')[0]
        else:
            return filename

    # Last resort: generate a placeholder ID
    return "UNKNOWN_FLOAT"


def _extract_floats_data(
    data_df: pd.DataFrame,
    quality_data: Dict[str, Any],
    processing_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Extract unique floats from data"""

    floats = []

    # Get unique float IDs using our robust extraction method
    unique_floats = set()
    for _, row in data_df.iterrows():
        float_id = _extract_float_id_from_data(row)
        unique_floats.add(float_id)

    for clean_float_id in unique_floats:
        # Filter data by trying to match the original data
        # Since we derived the clean ID, we need to find rows that would produce this ID
        matching_rows = []
        for _, row in data_df.iterrows():
            if _extract_float_id_from_data(row) == clean_float_id:
                matching_rows.append(row)

        if not matching_rows:
            continue

        float_data = matching_rows[0]

        # Create deployment info from available data - clean all strings
        deployment_info = {
            "source_file": _clean_string_for_postgres(float_data.get('file_name', 'unknown')),
            "processing_timestamp": processing_data.get('export_timestamp'),
            "data_mode": _clean_string_for_postgres(float_data.get('data_mode', '')),
            "coordinate_coverage": quality_data.get('coordinate_coverage', {}),
            "parameter_coverage": quality_data.get('parameter_coverage', {})
        }

        # PI details (placeholder - would need original NetCDF metadata)
        pi_details = {
            "processing_system": "SIH25_DATAOPS",
            "quality_control": quality_data.get('qc_summary', {}),
            "completeness": quality_data.get('completeness', {})
        }

        floats.append({
            "wmo_id": clean_float_id,  # Use cleaned float_id
            "deployment_info": deployment_info,
            "pi_details": pi_details
        })

    return floats


def _extract_profiles_data(
    data_df: pd.DataFrame,
    profiles_df: Optional[pd.DataFrame]
) -> List[Dict[str, Any]]:
    """Extract profile data from dataframes"""

    profiles = []

    # Group by profile_idx to get unique profiles
    for profile_idx in data_df['profile_idx'].unique():
        profile_data = data_df[data_df['profile_idx'] == profile_idx].iloc[0]

        # Generate profile_id combining clean float_id and profile_idx
        clean_float_id = _extract_float_id_from_data(profile_data)
        profile_id = f"{clean_float_id}_{profile_idx:03d}"

        # Handle timestamp conversion
        timestamp = None
        if 'timestamp' in profile_data and pd.notna(profile_data['timestamp']):
            try:
                if isinstance(profile_data['timestamp'], str):
                    timestamp = pd.to_datetime(profile_data['timestamp'])
                elif isinstance(profile_data['timestamp'], (int, float)):
                    # Assume Unix timestamp
                    timestamp = pd.to_datetime(profile_data['timestamp'], unit='s')
                else:
                    timestamp = profile_data['timestamp']
            except:
                timestamp = None

        # Extract position QC (default to 1 if not available)
        position_qc = 1
        if 'position_qc' in profile_data:
            position_qc = profile_data['position_qc']
        elif 'latitude' in profile_data and 'longitude' in profile_data:
            # If we have valid coordinates, assume good QC
            if pd.notna(profile_data['latitude']) and pd.notna(profile_data['longitude']):
                position_qc = 1
            else:
                position_qc = 4  # Bad position

        profiles.append({
            "profile_id": profile_id,
            "float_wmo_id": clean_float_id,  # Use cleaned float_id
            "timestamp": timestamp,
            "latitude": float(profile_data['latitude']) if pd.notna(profile_data['latitude']) else None,
            "longitude": float(profile_data['longitude']) if pd.notna(profile_data['longitude']) else None,
            "position_qc": int(position_qc),
            "data_mode": _clean_string_for_postgres(profile_data.get('data_mode', 'D'))[:1]  # Clean and ensure single character
        })

    return profiles


def _extract_observations_data(data_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Extract observations data from main dataframe"""

    observations = []

    # Parameters to extract
    parameters = ['pres', 'temp', 'psal', 'doxy']

    for _, row in data_df.iterrows():
        clean_float_id = _extract_float_id_from_data(row)
        profile_id = f"{clean_float_id}_{row['profile_idx']:03d}"
        depth = float(row['depth_m']) if pd.notna(row['depth_m']) else float(row['pres']) if pd.notna(row['pres']) else None

        for param in parameters:
            if param in data_df.columns and pd.notna(row[param]):

                # Get QC flag
                qc_flag = 1  # Default to good
                qc_col = f"{param}_qc"
                if qc_col in data_df.columns and pd.notna(row[qc_col]):
                    qc_value = row[qc_col]
                    # Handle string QC flags like "[b'1']"
                    if isinstance(qc_value, str) and qc_value.startswith("[b'") and qc_value.endswith("']"):
                        try:
                            qc_flag = int(qc_value[3:-2])
                        except (ValueError, TypeError):
                            qc_flag = 1
                    else:
                        try:
                            qc_flag = int(qc_value)
                        except (ValueError, TypeError):
                            qc_flag = 1

                observations.append({
                    "profile_id": profile_id,
                    "depth": depth,
                    "parameter": param,
                    "value": float(row[param]),
                    "qc_flag": qc_flag
                })

    return observations


async def _insert_floats(
    conn,
    floats_data: List[Dict[str, Any]],
    strategy: str
) -> int:
    """Insert floats data with deduplication"""

    if not floats_data:
        return 0

    if strategy == "upsert":
        # Use ON CONFLICT to update if exists
        query = """
        INSERT INTO floats (wmo_id, deployment_info, pi_details)
        VALUES ($1, $2, $3)
        ON CONFLICT (wmo_id)
        DO UPDATE SET
            deployment_info = EXCLUDED.deployment_info,
            pi_details = EXCLUDED.pi_details,
            created_at = NOW()
        """
    else:  # ignore
        query = """
        INSERT INTO floats (wmo_id, deployment_info, pi_details)
        VALUES ($1, $2, $3)
        ON CONFLICT (wmo_id) DO NOTHING
        """

    count = 0
    for float_data in floats_data:
        await conn.execute(
            query,
            float_data["wmo_id"],
            json.dumps(float_data["deployment_info"]),
            json.dumps(float_data["pi_details"])
        )
        count += 1

    return count


async def _insert_profiles(
    conn,
    profiles_data: List[Dict[str, Any]],
    strategy: str
) -> int:
    """Insert profiles data with deduplication"""

    if not profiles_data:
        return 0

    if strategy == "upsert":
        query = """
        INSERT INTO profiles (profile_id, float_wmo_id, timestamp, latitude, longitude, position_qc, data_mode)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (profile_id)
        DO UPDATE SET
            timestamp = EXCLUDED.timestamp,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            position_qc = EXCLUDED.position_qc,
            data_mode = EXCLUDED.data_mode,
            created_at = NOW()
        """
    else:  # ignore
        query = """
        INSERT INTO profiles (profile_id, float_wmo_id, timestamp, latitude, longitude, position_qc, data_mode)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (profile_id) DO NOTHING
        """

    count = 0
    for profile_data in profiles_data:
        await conn.execute(
            query,
            profile_data["profile_id"],
            profile_data["float_wmo_id"],
            profile_data["timestamp"],
            profile_data["latitude"],
            profile_data["longitude"],
            profile_data["position_qc"],
            profile_data["data_mode"]
        )
        count += 1

    return count


async def _insert_observations(
    conn,
    observations_data: List[Dict[str, Any]],
    strategy: str
) -> int:
    """Insert observations data with deduplication"""

    if not observations_data:
        return 0

    logger = get_run_logger()
    count = 0

    if strategy == "upsert":
        # For observations, we'll use a composite key approach
        # First, we need to create the unique constraint if it doesn't exist
        try:
            await conn.execute("""
                ALTER TABLE observations
                ADD CONSTRAINT observations_unique_key
                UNIQUE (profile_id, depth, parameter)
            """)
        except Exception:
            # Constraint likely already exists
            pass

        query = """
            INSERT INTO observations (profile_id, depth, parameter, value, qc_flag)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT ON CONSTRAINT observations_unique_key
            DO UPDATE SET
                value = EXCLUDED.value,
                qc_flag = EXCLUDED.qc_flag,
                created_at = NOW()
        """

    else:  # ignore - use a different approach since we don't have a unique constraint
        # Check and insert only if not exists
        query = """
            INSERT INTO observations (profile_id, depth, parameter, value, qc_flag)
            SELECT $1, $2, $3, $4, $5
            WHERE NOT EXISTS (
                SELECT 1 FROM observations
                WHERE profile_id = $1 AND depth = $2 AND parameter = $3
            )
        """

    # Process observations in batches to avoid long-running transactions
    batch_size = 50
    for i in range(0, len(observations_data), batch_size):
        batch = observations_data[i:i + batch_size]

        for obs_data in batch:
            try:
                # Validate the data before insertion
                if obs_data["depth"] is None or obs_data["value"] is None:
                    logger.warning(f"Skipping observation with null depth or value: {obs_data}")
                    continue

                await conn.execute(
                    query,
                    obs_data["profile_id"],
                    obs_data["depth"],
                    obs_data["parameter"],
                    obs_data["value"],
                    obs_data["qc_flag"]
                )
                count += 1
            except Exception as e:
                # Log but continue with other observations
                logger.warning(f"Failed to insert observation {obs_data.get('parameter', 'unknown')} at depth {obs_data.get('depth', 'unknown')}: {e}")
                continue

    return count


if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        if len(sys.argv) < 3:
            print("Usage: python data_loader.py <parquet_dir> <file_prefix>")
            sys.exit(1)

        parquet_dir = sys.argv[1]
        file_prefix = sys.argv[2]

        try:
            result = await load_parquet_to_postgres(parquet_dir, file_prefix)
            print("Data loading completed successfully!")
            print(json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    asyncio.run(main())