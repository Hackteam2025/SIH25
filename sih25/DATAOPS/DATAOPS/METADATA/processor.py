"""
Metadata Processing Pipeline
Handles ingestion and processing of ARGO metadata files for vector database storage
"""

import os
import json
import csv
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import asyncio

import pandas as pd
import numpy as np
from pydantic import BaseModel, validator

from .vector_store import get_vector_store, ProfileSummary

logger = logging.getLogger(__name__)


class MetadataFile(BaseModel):
    """Metadata file representation"""
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime


class MetadataProcessor:
    """Process metadata files and create vector embeddings"""

    def __init__(self, upload_dir: str = "uploads/metadata"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # Supported formats
        self.supported_formats = {'.json', '.csv', '.jsonl', '.txt'}

    async def process_uploaded_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Process an uploaded metadata file"""
        try:
            logger.info(f"Processing metadata file: {filename}")

            # Determine file format and process accordingly
            file_ext = Path(filename).suffix.lower()

            if file_ext not in self.supported_formats:
                return {
                    "success": False,
                    "error": f"Unsupported file format: {file_ext}",
                    "supported_formats": list(self.supported_formats)
                }

            # Read and parse file
            profiles = await self._parse_file(file_path, file_ext)

            if not profiles:
                return {
                    "success": False,
                    "error": "No valid profile data found in file",
                    "processed_count": 0
                }

            # Store in vector database
            vector_store = await get_vector_store()
            success = await vector_store.add_profiles(profiles)

            if success:
                return {
                    "success": True,
                    "processed_count": len(profiles),
                    "message": f"Successfully processed {len(profiles)} metadata entries",
                    "file_info": {
                        "filename": filename,
                        "format": file_ext,
                        "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to store profiles in vector database"
                }

        except Exception as e:
            logger.error(f"Error processing metadata file {filename}: {e}")
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}"
            }

    async def _parse_file(self, file_path: str, file_ext: str) -> List[Dict[str, Any]]:
        """Parse file based on its format"""
        try:
            if file_ext == '.json':
                return await self._parse_json_file(file_path)
            elif file_ext == '.csv':
                return await self._parse_csv_file(file_path)
            elif file_ext == '.jsonl':
                return await self._parse_jsonl_file(file_path)
            elif file_ext == '.txt':
                return await self._parse_text_file(file_path)
            else:
                return []

        except Exception as e:
            logger.error(f"Failed to parse {file_ext} file: {e}")
            return []

    async def _parse_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse JSON metadata file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        profiles = []

        # Handle different JSON structures
        if isinstance(data, list):
            # List of profiles
            for item in data:
                profile = self._extract_profile_data(item)
                if profile:
                    profiles.append(profile)

        elif isinstance(data, dict):
            if 'profiles' in data:
                # JSON with profiles key
                for item in data['profiles']:
                    profile = self._extract_profile_data(item)
                    if profile:
                        profiles.append(profile)
            else:
                # Single profile
                profile = self._extract_profile_data(data)
                if profile:
                    profiles.append(profile)

        return profiles

    async def _parse_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV metadata file"""
        try:
            df = pd.read_csv(file_path)
            profiles = []

            for _, row in df.iterrows():
                profile = self._extract_profile_data(row.to_dict())
                if profile:
                    profiles.append(profile)

            return profiles

        except Exception as e:
            logger.error(f"CSV parsing error: {e}")
            return []

    async def _parse_jsonl_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse JSONL metadata file"""
        profiles = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())
                    profile = self._extract_profile_data(data)
                    if profile:
                        profiles.append(profile)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on line {line_num + 1}: {e}")
                    continue

        return profiles

    async def _parse_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse text metadata file (custom format)"""
        profiles = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to parse as structured text
        sections = content.split('\n\n')

        for section in sections:
            lines = section.strip().split('\n')
            if len(lines) < 3:
                continue

            # Extract basic profile information from text
            profile_data = {
                'profile_id': f"text_profile_{len(profiles) + 1}",
                'description': section.strip()
            }

            # Try to extract common fields
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()

                    if key in ['lat', 'latitude']:
                        try:
                            profile_data['latitude'] = float(value)
                        except ValueError:
                            pass
                    elif key in ['lon', 'longitude']:
                        try:
                            profile_data['longitude'] = float(value)
                        except ValueError:
                            pass
                    elif key in ['time', 'timestamp', 'date']:
                        profile_data['timestamp'] = value
                    elif key in ['float', 'float_id', 'wmo']:
                        profile_data['float_id'] = value

            profile = self._extract_profile_data(profile_data)
            if profile:
                profiles.append(profile)

        return profiles

    def _extract_profile_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and standardize profile data from raw input"""
        try:
            # Map common field variations to standard names
            field_mappings = {
                'profile_id': ['profile_id', 'id', 'profile', 'cycle_number'],
                'float_id': ['float_id', 'wmo', 'wmo_id', 'platform_number'],
                'latitude': ['latitude', 'lat', 'y', 'juld_lat'],
                'longitude': ['longitude', 'lon', 'x', 'juld_lon'],
                'timestamp': ['timestamp', 'time', 'date', 'juld', 'date_creation'],
                'parameters': ['parameters', 'params', 'variables', 'measurements'],
                'depth_min': ['depth_min', 'min_depth', 'pres_min'],
                'depth_max': ['depth_max', 'max_depth', 'pres_max'],
                'qc_flag': ['qc_flag', 'quality', 'data_mode'],
                'region': ['region', 'ocean', 'basin'],
                'season': ['season', 'month']
            }

            profile = {}

            # Extract mapped fields
            for standard_field, possible_fields in field_mappings.items():
                for field in possible_fields:
                    if field in raw_data:
                        profile[standard_field] = raw_data[field]
                        break

            # Ensure required fields have defaults
            profile.setdefault('profile_id', f"profile_{datetime.now().timestamp()}")
            profile.setdefault('float_id', 'unknown')
            profile.setdefault('timestamp', datetime.now().isoformat())
            profile.setdefault('latitude', 0.0)
            profile.setdefault('longitude', 0.0)
            profile.setdefault('parameters', ['temperature', 'salinity'])
            profile.setdefault('min_depth', 0)
            profile.setdefault('max_depth', 2000)
            profile.setdefault('qc_summary', 'quality controlled data')

            # Determine region based on coordinates
            lat = float(profile['latitude'])
            if -30 <= lat <= 30:
                profile['region'] = 'tropical'
            elif lat > 60 or lat < -60:
                profile['region'] = 'polar'
            else:
                profile['region'] = 'temperate'

            # Determine season if timestamp is available
            try:
                if isinstance(profile['timestamp'], str):
                    dt = datetime.fromisoformat(profile['timestamp'].replace('Z', ''))
                    month = dt.month
                    seasons = {1: "winter", 4: "spring", 7: "summer", 10: "autumn"}
                    profile['season'] = seasons.get(((month-1)//3)*3 + 1, "unknown")
            except:
                profile['season'] = 'unknown'

            # Ensure parameters is a list
            if isinstance(profile['parameters'], str):
                profile['parameters'] = [p.strip() for p in profile['parameters'].split(',')]

            return profile

        except Exception as e:
            logger.error(f"Failed to extract profile data: {e}")
            return None

    async def create_sample_metadata(self) -> List[Dict[str, Any]]:
        """Create sample metadata for testing"""
        import random

        sample_profiles = []

        # Define some sample data ranges
        locations = [
            {"lat": 20.5, "lon": 65.2, "region": "Arabian Sea"},
            {"lat": -5.3, "lon": 80.1, "region": "Indian Ocean"},
            {"lat": 15.8, "lon": 70.4, "region": "Arabian Sea"},
            {"lat": -15.2, "lon": 75.6, "region": "Indian Ocean"},
            {"lat": 8.1, "lon": 78.3, "region": "Bay of Bengal"}
        ]

        parameters_sets = [
            ["temperature", "salinity"],
            ["temperature", "salinity", "pressure"],
            ["temperature", "salinity", "oxygen"],
            ["temperature", "salinity", "chlorophyll"],
            ["temperature", "salinity", "pressure", "oxygen", "chlorophyll"]
        ]

        for i in range(10):
            loc = random.choice(locations)
            params = random.choice(parameters_sets)

            # Random timestamp within last year
            days_ago = random.randint(1, 365)
            timestamp = datetime.now().replace(
                day=random.randint(1, 28),
                hour=random.randint(0, 23),
                minute=random.randint(0, 59)
            )

            profile = {
                "profile_id": f"sample_profile_{i+1:03d}",
                "float_id": f"ARGO_{5900000 + i:06d}",
                "latitude": loc["lat"] + random.uniform(-2, 2),
                "longitude": loc["lon"] + random.uniform(-2, 2),
                "timestamp": timestamp.isoformat(),
                "parameters": params,
                "min_depth": 0,
                "max_depth": random.randint(1000, 2000),
                "qc_summary": random.choice([
                    "high quality delayed mode data",
                    "good quality real-time data",
                    "quality controlled measurements"
                ]),
                "region": loc["region"],
                "description": f"Oceanographic profile from {loc['region']} with {len(params)} parameters"
            }

            sample_profiles.append(profile)

        return sample_profiles

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        vector_store = await get_vector_store()
        return vector_store.get_stats()


# Global processor instance
_processor = None


def get_metadata_processor() -> MetadataProcessor:
    """Get or create the global metadata processor instance"""
    global _processor
    if _processor is None:
        _processor = MetadataProcessor()
    return _processor