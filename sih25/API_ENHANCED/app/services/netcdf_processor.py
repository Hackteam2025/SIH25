"""
ARGO NetCDF File Processing Service
Handles ingestion and processing of ARGO float NetCDF files
"""

import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
import netCDF4
from sqlalchemy.orm import Session
from ..models.profile import Profile
from ..database import get_db

logger = logging.getLogger(__name__)

@dataclass
class ArgoProfile:
    """Data class for ARGO profile data"""
    float_id: str
    cycle_number: int
    latitude: float
    longitude: float
    date: datetime
    pressure: List[float]
    temperature: List[float]
    salinity: List[float]
    depth: List[float]
    quality_flags: Dict[str, List[int]]
    metadata: Dict[str, Any]

class NetCDFProcessor:
    """Process ARGO NetCDF files and extract profile data"""
    
    def __init__(self):
        self.supported_formats = ['.nc', '.netcdf']
        self.required_variables = ['PRES', 'TEMP', 'PSAL']
        
    def validate_netcdf_file(self, file_path: Path) -> bool:
        """Validate if NetCDF file contains required ARGO variables"""
        try:
            with xr.open_dataset(file_path) as ds:
                # Check for required variables
                missing_vars = [var for var in self.required_variables if var not in ds.variables]
                if missing_vars:
                    logger.warning(f"Missing required variables: {missing_vars}")
                    return False
                
                # Check for coordinate variables
                required_coords = ['LATITUDE', 'LONGITUDE', 'JULD']
                missing_coords = [coord for coord in required_coords if coord not in ds.variables]
                if missing_coords:
                    logger.warning(f"Missing coordinate variables: {missing_coords}")
                    return False
                
                return True
        except Exception as e:
            logger.error(f"Error validating NetCDF file {file_path}: {e}")
            return False
    
    def extract_float_metadata(self, dataset: xr.Dataset) -> Dict[str, Any]:
        """Extract float metadata from NetCDF dataset"""
        metadata = {}
        
        # Platform information
        if 'PLATFORM_NUMBER' in dataset.variables:
            metadata['platform_number'] = str(dataset['PLATFORM_NUMBER'].values)
        
        # WMO identifier
        if 'WMO_INST_TYPE' in dataset.variables:
            metadata['wmo_inst_type'] = str(dataset['WMO_INST_TYPE'].values)
        
        # Project name
        if 'PROJECT_NAME' in dataset.variables:
            metadata['project_name'] = str(dataset['PROJECT_NAME'].values)
        
        # Principal investigator
        if 'PI_NAME' in dataset.variables:
            metadata['pi_name'] = str(dataset['PI_NAME'].values)
        
        # Data center
        if 'DATA_CENTRE' in dataset.variables:
            metadata['data_centre'] = str(dataset['DATA_CENTRE'].values)
        
        # Float type
        if 'FLOAT_SERIAL_NO' in dataset.variables:
            metadata['float_serial_no'] = str(dataset['FLOAT_SERIAL_NO'].values)
        
        return metadata
    
    def convert_julian_date(self, julian_date: float, reference_date: str = "1950-01-01") -> datetime:
        """Convert ARGO Julian date to Python datetime"""
        try:
            ref_date = datetime.strptime(reference_date, "%Y-%m-%d")
            return ref_date + timedelta(days=float(julian_date))
        except (ValueError, TypeError):
            logger.warning(f"Invalid Julian date: {julian_date}")
            return datetime.now()
    
    def calculate_depth_from_pressure(self, pressure: np.ndarray, latitude: float) -> np.ndarray:
        """
        Calculate depth from pressure using UNESCO algorithm
        Simplified version - for production use gsw library
        """
        # Simplified depth calculation (UNESCO 1983)
        # For accurate calculations, use gsw.z_from_p()
        g = 9.80665  # Standard gravity
        
        # Latitude correction for gravity
        lat_rad = np.radians(latitude)
        g_lat = g * (1 + 5.2885e-3 * np.sin(lat_rad)**2 - 5.9e-6 * np.sin(2*lat_rad)**2)
        
        # Simplified depth calculation
        depth = pressure * 10000 / (g_lat * 1025)  # Assuming seawater density ~1025 kg/m³
        
        return depth
    
    def apply_quality_control(self, data: np.ndarray, qc_flags: np.ndarray) -> np.ndarray:
        """Apply quality control based on ARGO QC flags"""
        # ARGO QC flags: 1=good, 2=probably good, 3=probably bad, 4=bad, 5=changed, 8=estimated, 9=missing
        good_flags = [1, 2, 5, 8]  # Accept good, probably good, changed, and estimated data
        
        # Create mask for good data
        mask = np.isin(qc_flags, good_flags)
        
        # Apply mask
        cleaned_data = np.where(mask, data, np.nan)
        
        return cleaned_data
    
    def process_single_profile(self, dataset: xr.Dataset, profile_idx: int) -> Optional[ArgoProfile]:
        """Process a single profile from the NetCDF dataset"""
        try:
            # Extract basic coordinates
            latitude = float(dataset['LATITUDE'].values[profile_idx])
            longitude = float(dataset['LONGITUDE'].values[profile_idx])
            
            # Handle longitude wrapping
            if longitude > 180:
                longitude -= 360
            elif longitude < -180:
                longitude += 360
            
            # Extract date
            julian_date = dataset['JULD'].values[profile_idx]
            date = self.convert_julian_date(julian_date)
            
            # Extract cycle number
            cycle_number = int(dataset['CYCLE_NUMBER'].values[profile_idx]) if 'CYCLE_NUMBER' in dataset else 0
            
            # Extract platform number (float ID)
            platform_number = str(dataset['PLATFORM_NUMBER'].values).strip()
            
            # Extract profile data
            pressure = dataset['PRES'].values[profile_idx, :]
            temperature = dataset['TEMP'].values[profile_idx, :]
            salinity = dataset['PSAL'].values[profile_idx, :]
            
            # Extract quality control flags
            quality_flags = {}
            if 'PRES_QC' in dataset:
                quality_flags['pressure'] = dataset['PRES_QC'].values[profile_idx, :].astype(int)
            if 'TEMP_QC' in dataset:
                quality_flags['temperature'] = dataset['TEMP_QC'].values[profile_idx, :].astype(int)
            if 'PSAL_QC' in dataset:
                quality_flags['salinity'] = dataset['PSAL_QC'].values[profile_idx, :].astype(int)
            
            # Apply quality control
            if 'pressure' in quality_flags:
                pressure = self.apply_quality_control(pressure, quality_flags['pressure'])
            if 'temperature' in quality_flags:
                temperature = self.apply_quality_control(temperature, quality_flags['temperature'])
            if 'salinity' in quality_flags:
                salinity = self.apply_quality_control(salinity, quality_flags['salinity'])
            
            # Calculate depth from pressure
            depth = self.calculate_depth_from_pressure(pressure, latitude)
            
            # Remove NaN values and create valid data points
            valid_mask = ~(np.isnan(pressure) | np.isnan(temperature) | np.isnan(salinity))
            
            if not np.any(valid_mask):
                logger.warning(f"No valid data points in profile {profile_idx}")
                return None
            
            # Filter to valid data points
            pressure_clean = pressure[valid_mask].tolist()
            temperature_clean = temperature[valid_mask].tolist()
            salinity_clean = salinity[valid_mask].tolist()
            depth_clean = depth[valid_mask].tolist()
            
            # Extract metadata
            metadata = self.extract_float_metadata(dataset)
            metadata['profile_index'] = profile_idx
            metadata['n_levels'] = len(pressure_clean)
            
            return ArgoProfile(
                float_id=platform_number,
                cycle_number=cycle_number,
                latitude=latitude,
                longitude=longitude,
                date=date,
                pressure=pressure_clean,
                temperature=temperature_clean,
                salinity=salinity_clean,
                depth=depth_clean,
                quality_flags=quality_flags,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing profile {profile_idx}: {e}")
            return None
    
    def process_netcdf_file(self, file_path: Path) -> List[ArgoProfile]:
        """Process entire NetCDF file and extract all profiles"""
        profiles = []
        
        try:
            logger.info(f"Processing NetCDF file: {file_path}")
            
            # Validate file
            if not self.validate_netcdf_file(file_path):
                logger.error(f"Invalid NetCDF file: {file_path}")
                return profiles
            
            # Open dataset
            with xr.open_dataset(file_path) as dataset:
                # Determine number of profiles
                if 'N_PROF' in dataset.dims:
                    n_profiles = dataset.dims['N_PROF']
                else:
                    # Single profile file
                    n_profiles = 1
                
                logger.info(f"Found {n_profiles} profiles in file")
                
                # Process each profile
                for i in range(n_profiles):
                    profile = self.process_single_profile(dataset, i)
                    if profile:
                        profiles.append(profile)
                
                logger.info(f"Successfully processed {len(profiles)} profiles")
                
        except Exception as e:
            logger.error(f"Error processing NetCDF file {file_path}: {e}")
        
        return profiles
    
    def save_profiles_to_database(self, profiles: List[ArgoProfile], db: Session) -> int:
        """Save processed profiles to database"""
        saved_count = 0
        
        try:
            for argo_profile in profiles:
                # Create individual database entries for each depth level
                for i, (depth, temp, sal, pres) in enumerate(zip(
                    argo_profile.depth,
                    argo_profile.temperature,
                    argo_profile.salinity,
                    argo_profile.pressure
                )):
                    # Create database profile entry
                    db_profile = Profile(
                        float_id=argo_profile.float_id,
                        latitude=argo_profile.latitude,
                        longitude=argo_profile.longitude,
                        depth=int(depth),
                        temperature=round(temp, 3),
                        salinity=round(sal, 3),
                        pressure=round(pres, 2),
                        month=argo_profile.date.month,
                        year=argo_profile.date.year,
                        date=argo_profile.date.date(),
                        cycle_number=argo_profile.cycle_number,
                        level_number=i,
                        metadata=argo_profile.metadata
                    )
                    
                    db.add(db_profile)
                    saved_count += 1
            
            db.commit()
            logger.info(f"Saved {saved_count} profile records to database")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving profiles to database: {e}")
            saved_count = 0
        
        return saved_count
    
    def process_directory(self, directory_path: Path, db: Session) -> Dict[str, int]:
        """Process all NetCDF files in a directory"""
        results = {
            'files_processed': 0,
            'profiles_extracted': 0,
            'records_saved': 0,
            'errors': 0
        }
        
        # Find all NetCDF files
        netcdf_files = []
        for ext in self.supported_formats:
            netcdf_files.extend(directory_path.glob(f"*{ext}"))
        
        logger.info(f"Found {len(netcdf_files)} NetCDF files to process")
        
        for file_path in netcdf_files:
            try:
                # Process file
                profiles = self.process_netcdf_file(file_path)
                results['files_processed'] += 1
                results['profiles_extracted'] += len(profiles)
                
                # Save to database
                saved_count = self.save_profiles_to_database(profiles, db)
                results['records_saved'] += saved_count
                
                logger.info(f"Processed {file_path.name}: {len(profiles)} profiles, {saved_count} records saved")
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                results['errors'] += 1
        
        return results

# Convenience functions
def process_argo_file(file_path: str, db: Session) -> List[ArgoProfile]:
    """Process a single ARGO NetCDF file"""
    processor = NetCDFProcessor()
    return processor.process_netcdf_file(Path(file_path))

def process_argo_directory(directory_path: str, db: Session) -> Dict[str, int]:
    """Process all ARGO NetCDF files in a directory"""
    processor = NetCDFProcessor()
    return processor.process_directory(Path(directory_path), db)
