#!/usr/bin/env python3
"""
Step 4: Argo Data Validation
Validates required fields, types, ranges, and QC flags
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import xarray as xr
from pydantic import BaseModel, Field, ValidationError
from prefect import task, get_run_logger


class ArgoValidationConfig(BaseModel):
    """Configuration for Argo data validation"""
    required_core_vars: List[str] = ['JULD', 'LATITUDE', 'LONGITUDE', 'PRES']
    latitude_range: Tuple[float, float] = (-90.0, 90.0)
    longitude_range: Tuple[float, float] = (-180.0, 180.0)
    pressure_min: float = 0.0
    pressure_max: float = 6000.0  # Max ocean depth ~11km, but 6km covers most profiles
    temperature_range: Tuple[float, float] = (-5.0, 50.0)  # Reasonable ocean temps
    salinity_range: Tuple[float, float] = (0.0, 50.0)  # Reasonable ocean salinity
    valid_qc_flags: List[int] = [0, 1, 2, 3, 4, 5, 8, 9]  # All valid QC flags
    preferred_qc_flags: List[int] = [1, 2]  # Good and probably good data
    valid_data_modes: List[str] = ['R', 'A', 'D']


class ArgoValidationResult(BaseModel):
    """Results from Argo data validation"""
    file_name: str
    is_valid: bool
    total_records: int
    valid_records: int
    validation_errors: List[Dict[str, Any]]
    warnings: List[str]
    summary: Dict[str, Any]


@task(name="data-validation")
def validate_argo_data(nc_file_path: str, schema_info: Dict[str, Any]) -> ArgoValidationResult:
    """
    Validate Argo NetCDF data for required fields, ranges, and quality
    
    Args:
        nc_file_path: Path to NetCDF file
        schema_info: Schema information from step 3
        
    Returns:
        Validation results
    """
    logger = get_run_logger()
    nc_file = Path(nc_file_path)
    config = ArgoValidationConfig()
    
    logger.info(f"Starting data validation for: {nc_file.name}")
    
    # Open dataset with proper decoding for validation
    ds = xr.open_dataset(nc_file, decode_cf=True, mask_and_scale=True)
    
    validation_errors = []
    warnings_list = []
    
    try:
        # 1. Check for required core variables
        logger.info("Checking required core variables...")
        missing_vars = []
        for var in config.required_core_vars:
            if var not in ds.variables:
                missing_vars.append(var)
                validation_errors.append({
                    "type": "missing_required_variable",
                    "variable": var,
                    "message": f"Required variable {var} not found"
                })
        
        if missing_vars:
            logger.error(f"Missing required variables: {missing_vars}")
            return ArgoValidationResult(
                file_name=nc_file.name,
                is_valid=False,
                total_records=0,
                valid_records=0,
                validation_errors=validation_errors,
                warnings=warnings_list,
                summary={"status": "failed", "reason": "missing_required_variables"}
            )
        
        # 2. Extract and validate coordinate data
        logger.info("Validating coordinate data...")
        
        # Time validation
        if 'JULD' in ds.variables:
            juld = ds['JULD'].values
            valid_time_mask = ~np.isnat(pd.to_datetime(juld, errors='coerce'))
            invalid_time_count = (~valid_time_mask).sum()
            if invalid_time_count > 0:
                warnings_list.append(f"Found {invalid_time_count} invalid timestamps")
        
        # Latitude validation
        if 'LATITUDE' in ds.variables:
            lat = ds['LATITUDE'].values
            lat_valid = (lat >= config.latitude_range[0]) & (lat <= config.latitude_range[1]) & ~np.isnan(lat)
            invalid_lat_count = (~lat_valid).sum()
            if invalid_lat_count > 0:
                validation_errors.append({
                    "type": "invalid_latitude",
                    "count": int(invalid_lat_count),
                    "message": f"Found {invalid_lat_count} invalid latitude values"
                })
        
        # Longitude validation
        if 'LONGITUDE' in ds.variables:
            lon = ds['LONGITUDE'].values
            lon_valid = (lon >= config.longitude_range[0]) & (lon <= config.longitude_range[1]) & ~np.isnan(lon)
            invalid_lon_count = (~lon_valid).sum()
            if invalid_lon_count > 0:
                validation_errors.append({
                    "type": "invalid_longitude",
                    "count": int(invalid_lon_count),
                    "message": f"Found {invalid_lon_count} invalid longitude values"
                })
        
        # 3. Validate scientific parameters
        logger.info("Validating scientific parameters...")
        
        # Pressure validation
        if 'PRES' in ds.variables:
            pres = ds['PRES'].values
            pres_valid = (pres >= config.pressure_min) & (pres <= config.pressure_max) & ~np.isnan(pres)
            invalid_pres_count = (~pres_valid).sum()
            if invalid_pres_count > 0:
                warnings_list.append(f"Found {invalid_pres_count} pressure values outside expected range")
        
        # Temperature validation (if present)
        if 'TEMP' in ds.variables:
            temp = ds['TEMP'].values
            temp_valid = (temp >= config.temperature_range[0]) & (temp <= config.temperature_range[1]) & ~np.isnan(temp)
            invalid_temp_count = (~temp_valid).sum()
            if invalid_temp_count > 0:
                warnings_list.append(f"Found {invalid_temp_count} temperature values outside expected range")
        
        # Salinity validation (if present)
        if 'PSAL' in ds.variables:
            psal = ds['PSAL'].values
            psal_valid = (psal >= config.salinity_range[0]) & (psal <= config.salinity_range[1]) & ~np.isnan(psal)
            invalid_psal_count = (~psal_valid).sum()
            if invalid_psal_count > 0:
                warnings_list.append(f"Found {invalid_psal_count} salinity values outside expected range")
        
        # 4. Validate QC flags
        logger.info("Validating QC flags...")
        qc_summary = {}
        
        for qc_var in schema_info.get("qc_variables", []):
            if qc_var in ds.variables:
                qc_values = ds[qc_var].values.flatten()
                qc_values = qc_values[~np.isnan(qc_values.astype(float))]  # Remove NaN
                
                unique_flags, counts = np.unique(qc_values, return_counts=True)
                qc_summary[qc_var] = {
                    "unique_flags": [int(f) for f in unique_flags],
                    "counts": [int(c) for c in counts],
                    "total": int(len(qc_values))
                }
                
                # Check for invalid QC flags
                invalid_flags = [f for f in unique_flags if int(f) not in config.valid_qc_flags]
                if invalid_flags:
                    validation_errors.append({
                        "type": "invalid_qc_flag",
                        "variable": qc_var,
                        "invalid_flags": [int(f) for f in invalid_flags],
                        "message": f"Found invalid QC flags in {qc_var}: {invalid_flags}"
                    })
        
        # 5. Validate DATA_MODE
        logger.info("Validating DATA_MODE...")
        data_mode_valid = True
        if 'DATA_MODE' in ds.variables:
            try:
                data_mode = ds['DATA_MODE'].values
                if hasattr(data_mode, 'tobytes'):
                    mode_str = data_mode.tobytes().decode('ascii').strip()
                else:
                    mode_str = str(data_mode).strip()
                
                if mode_str not in config.valid_data_modes:
                    validation_errors.append({
                        "type": "invalid_data_mode",
                        "value": mode_str,
                        "message": f"Invalid DATA_MODE: {mode_str}"
                    })
                    data_mode_valid = False
            except Exception as e:
                warnings_list.append(f"Could not validate DATA_MODE: {e}")
        
        # 6. Calculate validation summary
        total_records = int(np.prod([ds.dims.get(dim, 1) for dim in ['N_PROF', 'N_LEVELS']]))
        
        # Estimate valid records based on coordinate validity
        coord_valid_mask = np.ones(ds.dims.get('N_PROF', 1), dtype=bool)
        if 'LATITUDE' in ds.variables and 'LONGITUDE' in ds.variables:
            lat = ds['LATITUDE'].values
            lon = ds['LONGITUDE'].values
            coord_valid_mask = (
                (lat >= config.latitude_range[0]) & (lat <= config.latitude_range[1]) &
                (lon >= config.longitude_range[0]) & (lon <= config.longitude_range[1]) &
                ~np.isnan(lat) & ~np.isnan(lon)
            )
        
        valid_records = int(coord_valid_mask.sum() * ds.dims.get('N_LEVELS', 1))
        
        # Determine overall validity
        critical_errors = [e for e in validation_errors if e["type"] in [
            "missing_required_variable", "invalid_latitude", "invalid_longitude", "invalid_data_mode"
        ]]
        is_valid = len(critical_errors) == 0
        
        validation_summary = {
            "total_variables": len(ds.variables),
            "required_variables_found": len(config.required_core_vars) - len(missing_vars),
            "qc_variables_validated": len(qc_summary),
            "data_mode_valid": data_mode_valid,
            "coordinate_coverage": float(coord_valid_mask.sum() / len(coord_valid_mask)) if len(coord_valid_mask) > 0 else 0.0,
            "qc_summary": qc_summary
        }
        
        logger.info(f"Validation complete:")
        logger.info(f"  - Valid: {is_valid}")
        logger.info(f"  - Total records: {total_records}")
        logger.info(f"  - Valid records: {valid_records}")
        logger.info(f"  - Errors: {len(validation_errors)}")
        logger.info(f"  - Warnings: {len(warnings_list)}")
        
        return ArgoValidationResult(
            file_name=nc_file.name,
            is_valid=is_valid,
            total_records=total_records,
            valid_records=valid_records,
            validation_errors=validation_errors,
            warnings=warnings_list,
            summary=validation_summary
        )
        
    finally:
        ds.close()


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python step4_validator.py <netcdf_file> <schema_json>")
        sys.exit(1)
    
    nc_file = sys.argv[1]
    schema_file = sys.argv[2]
    
    with open(schema_file, 'r') as f:
        schema_info = json.load(f)
    
    result = validate_argo_data(nc_file, schema_info)
    
    output_file = f"validation_report_{Path(nc_file).stem}.json"
    with open(output_file, 'w') as f:
        json.dump(result.dict(), f, indent=2, default=str)
    
    print(f"Validation report saved to: {output_file}")
    print(f"File is valid: {result.is_valid}")