#!/usr/bin/env python3
"""
Load sample data into FloatChat database
"""
import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.db import engine, SessionLocal
from backend.app.models import Profile
from backend.app.startup import init_db

def load_sample_data():
    """Load sample parquet data into database"""
    print("Initializing database...")
    init_db()

    # Find sample data file
    data_file = Path("data_pipeline/DATAOPS/PROFILES/preprocessed_data/D2900765_067_profiles.parquet")

    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        return

    print(f"Loading data from {data_file}")
    df = pd.read_parquet(data_file)

    print(f"Found {len(df)} records")

    # Prepare data for database
    db = SessionLocal()

    try:
        # Clear existing data
        db.query(Profile).delete()

        # Add sample records
        for idx, row in df.iterrows():
            if idx >= 100:  # Limit to 100 records for demo
                break

            profile = Profile(
                id=idx + 1,  # Add explicit ID
                float_id=row.get('float_wmo', 'DEMO_FLOAT'),
                lat=float(row.get('latitude', 0.0)),
                lon=float(row.get('longitude', 0.0)),
                depth=int(row.get('depth', 0)),
                temperature=float(row.get('temperature', 20.0)),
                salinity=float(row.get('salinity', 35.0)),
                month=int(row.get('month', datetime.now().month)),
                year=int(row.get('year', datetime.now().year))
            )
            db.add(profile)

        db.commit()
        print(f"Successfully loaded {min(100, len(df))} sample records")

    except Exception as e:
        print(f"Error loading data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    load_sample_data()