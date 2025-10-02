
import asyncio
import xarray as xr
import sys
import os
from typing import List, Dict, Any
import cftime
from datetime import datetime
from dotenv import load_dotenv
import argparse

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sih25.DATAOPS.METADATA.vector_store import get_vector_store, VectorStore

def safe_decode(byte_string):
    """Safely decodes a byte string to a Python string."""
    try:
        return byte_string.tobytes().decode('utf-8').strip()
    except (UnicodeDecodeError, AttributeError):
        try:
            return byte_string.tobytes().decode('latin-1').strip()
        except (UnicodeDecodeError, AttributeError):
            return str(byte_string)

def extract_profile_data_from_nc(nc_file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts profile data from a NetCDF file and formats it for the VectorStore.

    Args:
        nc_file_path: The path to the NetCDF file.

    Returns:
        A list of dictionaries, where each dictionary contains the metadata for one profile.
    """
    try:
        with xr.open_dataset(nc_file_path, decode_times=False) as ds:
            # --- IMPORTANT ---
            # You need to replace the placeholder variable names below with the actual 
            # variable names from your NetCDF file (listed above).
            
            # --- Variable Mapping ---
            timestamp_var = 'DATE_UPDATE'  # Or 'DATE_CREATION' or another date variable
            platform_var = 'PLATFORM_NUMBER' # Or another variable that identifies the float
            lat_var = 'LAUNCH_LATITUDE'
            lon_var = 'LAUNCH_LONGITUDE'
            pres_var = 'PRES'
            
            # Check if the essential variables exist
            required_vars = [timestamp_var, platform_var, lat_var, lon_var]
            if not all(var in ds for var in required_vars):
                print(f"Error: One or more required variables ({required_vars}) not found in the dataset.")
                print("Please update the 'Variable Mapping' section in the 'extract_profile_data_from_nc' function.")
                return []

            # This file seems to contain metadata for a single float, so we treat it as one profile.
            profiles = []
            
            # Decode timestamp
            try:
                time_val = ds[timestamp_var].values
                # It seems DATE_UPDATE is a string in YYYYMMDDHHMMSS format
                dt_object = datetime.strptime(safe_decode(time_val), '%Y%m%d%H%M%S')
                timestamp_str = dt_object.isoformat() + "Z"
            except (ValueError, TypeError):
                # Fallback for other date formats if needed
                timestamp_str = datetime.now().isoformat() + "Z"

            profile = {
                "profile_id": f"{safe_decode(ds[platform_var].values)}_meta",
                "float_id": safe_decode(ds[platform_var].values),
                "timestamp": timestamp_str,
                "latitude": float(ds[lat_var].values),
                "longitude": float(ds[lon_var].values),
                "min_depth": 0, # This is a metadata file, so depth is not applicable
                "max_depth": 2000, # Default value
                "parameters": [var for var in ds.data_vars if var not in required_vars],
                "qc_summary": "No QC summary available", # You might need to extract this from the file if it exists
            }
            profiles.append(profile)
            
            return profiles

    except Exception as e:
        print(f"Error reading NetCDF file: {e}")
        return []

async def main(args):
    """
    Main function to process the NetCDF file and add it to the vector store.
    """
    vector_store = await get_vector_store()

    if args.reset:
        print("Resetting the vector store...")
        success = await vector_store.reset_collection()
        if success:
            print("Vector store reset successfully.")
        else:
            print("Failed to reset vector store.")
        return

    if args.file_path:
        print(f"Processing file: {args.file_path}")
        
        # 1. Extract profile data from the NetCDF file
        profiles = extract_profile_data_from_nc(args.file_path)
        
        if not profiles:
            print("No profiles were extracted from the file.")
            return
            
        print(f"Extracted {len(profiles)} profiles from the file.")

        # 2. Add the profiles to the vector store
        success = await vector_store.add_profiles(profiles)

        if success:
            print("Successfully added profiles to the vector store.")
        else:
            print("Failed to add profiles to the vector store.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process NetCDF files and manage the vector store.")
    parser.add_argument("file_path", nargs='?', default=None, help="The path to the NetCDF file to process.")
    parser.add_argument("--reset", action="store_true", help="Reset the vector store collection.")
    
    args = parser.parse_args()

    if not args.file_path and not args.reset:
        parser.print_help()
        sys.exit(1)

    asyncio.run(main(args))
