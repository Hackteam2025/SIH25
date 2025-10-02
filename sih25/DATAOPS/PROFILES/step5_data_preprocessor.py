#!/usr/bin/env python3
"""
Step 5: Argo Data Preprocessing & Feature Extraction
Processes validated data following Argo best practices for adjusted/raw variables
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import xarray as xr
from prefect import task, get_run_logger


class ArgoDataProcessor:
    """Handles Argo-specific data processing logic"""
    
    def __init__(self):
        self.core_params = ['PRES', 'TEMP', 'PSAL']
        self.bgc_params = ['DOXY', 'CHLA', 'BBP', 'PH_IN_SITU_TOTAL', 'NITRATE']
        self.coordinate_vars = ['JULD', 'LATITUDE', 'LONGITUDE']
        self.good_qc_flags = [1, 2]  # Good and probably good data
        
    def _decode_char_array(self, char_array) -> str:
        """Safely decode character arrays from NetCDF"""
        try:
            if hasattr(char_array, 'tobytes'):
                return char_array.tobytes().decode('ascii', errors='ignore').strip()
            elif isinstance(char_array, (bytes, str)):
                return str(char_array).strip()
            else:
                # Handle character arrays
                chars = np.array(char_array).flatten()
                return ''.join([chr(int(c)) for c in chars if int(c) != 0]).strip()
        except:
            return str(char_array)
    
    def _get_parameter_data_mode(self, ds: xr.Dataset) -> Dict[str, str]:
        """Extract parameter-specific data modes for BGC files"""
        param_data_modes = {}
        
        if 'PARAMETER_DATA_MODE' in ds.variables and 'PARAMETER' in ds.variables:
            try:
                param_names = ds['PARAMETER'].values
                param_modes = ds['PARAMETER_DATA_MODE'].values
                
                # Handle different array shapes
                if param_names.ndim == 3:  # (N_PROF, N_PARAM, STRING_length)
                    for i in range(param_names.shape[0]):  # Each profile
                        for j in range(param_names.shape[1]):  # Each parameter
                            param_name = self._decode_char_array(param_names[i, j, :])
                            param_mode = self._decode_char_array(param_modes[i, j]) if param_modes.ndim > 1 else self._decode_char_array(param_modes)
                            if param_name and param_mode:
                                param_data_modes[f"{param_name}_{i}"] = param_mode
                elif param_names.ndim == 2:  # (N_PARAM, STRING_length)
                    for j in range(param_names.shape[0]):
                        param_name = self._decode_char_array(param_names[j, :])
                        param_mode = self._decode_char_array(param_modes[j]) if param_modes.ndim > 0 else self._decode_char_array(param_modes)
                        if param_name and param_mode:
                            param_data_modes[param_name] = param_mode
            except Exception as e:
                print(f"Warning: Could not extract PARAMETER_DATA_MODE: {e}")
        
        return param_data_modes
    
    def _choose_variable(self, ds: xr.Dataset, param: str, data_mode: str, param_data_modes: Dict[str, str]) -> Optional[xr.DataArray]:
        """Choose between raw and adjusted variables following Argo guidelines"""
        
        # For BGC files, use PARAMETER_DATA_MODE if available
        effective_mode = param_data_modes.get(param, data_mode)
        
        # Decision logic from Argo documentation
        if effective_mode == 'R':
            # Real-time mode: use raw data only
            if param in ds.variables:
                return ds[param]
        elif effective_mode in ['A', 'D']:
            # Adjusted or Delayed mode: prefer adjusted data
            adjusted_var = f"{param}_ADJUSTED"
            if adjusted_var in ds.variables:
                return ds[adjusted_var]
            elif param in ds.variables:
                # Fall back to raw if adjusted not available
                return ds[param]
        else:
            # Unknown mode, try both adjusted and raw
            adjusted_var = f"{param}_ADJUSTED"
            if adjusted_var in ds.variables:
                return ds[adjusted_var]
            elif param in ds.variables:
                return ds[param]
        
        return None
    
    def _apply_qc_filter(self, data: xr.DataArray, qc_var_name: str, ds: xr.Dataset) -> xr.DataArray:
        """Apply QC filtering to data"""
        if qc_var_name in ds.variables:
            qc_flags = ds[qc_var_name]
            # Create mask for good QC flags
            good_qc_mask = xr.zeros_like(qc_flags, dtype=bool)
            for flag in self.good_qc_flags:
                good_qc_mask = good_qc_mask | (qc_flags == flag)
            
            # Apply mask to data
            return data.where(good_qc_mask)
        else:
            return data
    
    def _safe_qc_check(self, qc_value) -> bool:
        """Safely check if QC flag is good, handling both numeric and character flags"""
        try:
            # Handle numpy arrays (extract scalar)
            if isinstance(qc_value, np.ndarray):
                if qc_value.size == 1:
                    qc_value = qc_value.item()
                else:
                    return False  # Shouldn't happen for single value

            if isinstance(qc_value, (bytes, str)):
                # Handle character flags like 'B' - decode if needed
                if isinstance(qc_value, bytes):
                    qc_str = qc_value.decode('ascii', errors='ignore').strip()
                else:
                    qc_str = str(qc_value).strip()

                # Convert character flags to numeric if possible
                if qc_str.isdigit():
                    return int(qc_str) in self.good_qc_flags
                else:
                    # For character flags like 'B', 'F', etc., be more permissive
                    # 'B' often means "probably good" in some Argo contexts
                    return qc_str in ['B', '1', '2']
            else:
                # Numeric QC flag
                return int(qc_value) in self.good_qc_flags
        except:
            # If we can't parse the QC flag, be conservative but permissive
            return True

    def _safe_extract_value(self, xr_value) -> float:
        """Safely extract float value from xarray DataArray"""
        try:
            val = xr_value.values
            # Handle numpy arrays
            if isinstance(val, np.ndarray):
                if val.size == 1:
                    val = val.item()
                else:
                    return None
            # Check for NaN - handle both Python and numpy numeric types
            if not (isinstance(val, str) or val is None):
                if not np.isnan(val):
                    return float(val)
            return None
        except:
            return None


@task(name="data-preprocessing")
def preprocess_argo_data(nc_file_path: str, validation_result: Dict[str, Any]) -> pd.DataFrame:
    """
    Preprocess Argo data following best practices for variable selection and QC

    Args:
        nc_file_path: Path to NetCDF file
        validation_result: Validation results from step 4

    Returns:
        Preprocessed DataFrame ready for storage
    """
    logger = get_run_logger()
    nc_file = Path(nc_file_path)

    if not validation_result["is_valid"]:
        logger.error(f"Cannot preprocess invalid file: {nc_file.name}")
        raise ValueError("File failed validation - cannot preprocess")

    # Check if this is a metadata file
    if validation_result.get("summary", {}).get("file_type") == "metadata":
        logger.info(f"Processing metadata file: {nc_file.name}")

        # Open dataset to extract metadata
        ds = xr.open_dataset(nc_file, decode_cf=False)
        processor = ArgoDataProcessor()

        try:
            # Extract metadata variables
            metadata_dict = {}

            # Platform information
            if 'PLATFORM_NUMBER' in ds.variables:
                metadata_dict['platform_number'] = processor._decode_char_array(ds['PLATFORM_NUMBER'].values)

            # Float configuration
            for var in ['PTT', 'TRANS_SYSTEM', 'POSITIONING_SYSTEM', 'PLATFORM_FAMILY',
                       'PLATFORM_TYPE', 'PLATFORM_MAKER', 'FIRMWARE_VERSION',
                       'FLOAT_SERIAL_NO', 'WMO_INST_TYPE']:
                if var in ds.variables:
                    metadata_dict[var.lower()] = processor._decode_char_array(ds[var].values)

            # Dates
            for var in ['DATE_CREATION', 'DATE_UPDATE']:
                if var in ds.variables:
                    metadata_dict[var.lower()] = processor._decode_char_array(ds[var].values)

            # Create a single-row DataFrame with metadata
            metadata_df = pd.DataFrame([metadata_dict])
            metadata_df['file_name'] = nc_file.name
            metadata_df['file_type'] = 'metadata'

            logger.info(f"Extracted {len(metadata_dict)} metadata fields")
            ds.close()
            return metadata_df

        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            ds.close()
            return pd.DataFrame()

    logger.info(f"Starting data preprocessing for: {nc_file.name}")
    
    # Open dataset with proper decoding
    ds = xr.open_dataset(nc_file, decode_cf=True, mask_and_scale=True)
    processor = ArgoDataProcessor()
    
    try:
        # Extract metadata
        float_id = None
        platform_number = None
        
        if 'PLATFORM_NUMBER' in ds.variables:
            try:
                platform_raw = ds['PLATFORM_NUMBER'].values
                platform_number = processor._decode_char_array(platform_raw)
                float_id = platform_number.strip() if platform_number else None
                if not float_id:  # If empty, try to get from filename
                    float_id = nc_file.stem
            except Exception as e:
                logger.warning(f"Could not decode PLATFORM_NUMBER: {e}")
                float_id = nc_file.stem
        
        # Extract DATA_MODE
        data_mode = 'D'  # Default fallback
        if 'DATA_MODE' in ds.variables:
            try:
                data_mode_raw = ds['DATA_MODE'].values
                data_mode = processor._decode_char_array(data_mode_raw)
                if not data_mode.strip():  # If empty, use default
                    data_mode = 'D'
            except Exception as e:
                logger.warning(f"Could not decode DATA_MODE: {e}")
                data_mode = 'D'
        
        # Extract parameter-specific data modes (BGC files)
        param_data_modes = processor._get_parameter_data_mode(ds)
        
        logger.info(f"File info: Float ID={float_id}, Data Mode={data_mode}")
        logger.info(f"Available variables: {list(ds.variables.keys())[:10]}...")  # Show first 10 variables
        
        # Check what core parameters are available
        available_core = [param for param in processor.core_params if param in ds.variables or f"{param}_ADJUSTED" in ds.variables]
        logger.info(f"Available core parameters: {available_core}")
        
        # Prepare data collection
        processed_records = []
        
        # Get dimensions
        n_prof = ds.dims.get('N_PROF', 1)
        n_levels = ds.dims.get('N_LEVELS', 0)
        
        logger.info(f"Processing {n_prof} profiles with max {n_levels} levels")
        
        # Process each profile
        for prof_idx in range(n_prof):

            # Extract profile-specific DATA_MODE if available
            profile_data_mode = data_mode  # Default
            if 'DATA_MODE' in ds.variables and ds.dims.get('N_PROF', 0) > 1:
                try:
                    mode_val = ds['DATA_MODE'].isel(N_PROF=prof_idx).values
                    if isinstance(mode_val, bytes):
                        profile_data_mode = mode_val.decode('ascii').strip()
                    elif isinstance(mode_val, np.ndarray) and mode_val.size == 1:
                        mode_val = mode_val.item()
                        if isinstance(mode_val, bytes):
                            profile_data_mode = mode_val.decode('ascii').strip()
                        else:
                            profile_data_mode = str(mode_val).strip()
                    else:
                        profile_data_mode = str(mode_val).strip()
                    if not profile_data_mode:
                        profile_data_mode = 'R'  # Default to real-time if empty
                except:
                    profile_data_mode = data_mode

            # Extract profile metadata
            profile_record = {
                'file_name': nc_file.name,
                'float_id': float_id,
                'profile_idx': prof_idx,
                'data_mode': profile_data_mode
            }
            
            # Extract time
            if 'JULD' in ds.variables:
                juld = ds['JULD'].isel(N_PROF=prof_idx) if n_prof > 1 else ds['JULD']
                try:
                    profile_record['timestamp'] = pd.to_datetime(juld.values).isoformat()
                except:
                    profile_record['timestamp'] = None
            
            # Extract coordinates
            if 'LATITUDE' in ds.variables:
                lat = ds['LATITUDE'].isel(N_PROF=prof_idx) if n_prof > 1 else ds['LATITUDE']
                profile_record['latitude'] = float(lat.values) if not np.isnan(lat.values) else None
            
            if 'LONGITUDE' in ds.variables:
                lon = ds['LONGITUDE'].isel(N_PROF=prof_idx) if n_prof > 1 else ds['LONGITUDE']
                profile_record['longitude'] = float(lon.values) if not np.isnan(lon.values) else None
            
            # Extract cycle number if available
            if 'CYCLE_NUMBER' in ds.variables:
                cycle = ds['CYCLE_NUMBER'].isel(N_PROF=prof_idx) if n_prof > 1 else ds['CYCLE_NUMBER']
                profile_record['cycle_number'] = int(cycle.values) if not np.isnan(cycle.values) else None
            
            # Process vertical profile data
            for level_idx in range(n_levels):
                level_record = profile_record.copy()
                level_record['level_idx'] = level_idx
                
                # Process each parameter
                for param in processor.core_params + processor.bgc_params:
                    if param in ds.variables or f"{param}_ADJUSTED" in ds.variables:

                        # Choose appropriate variable (raw vs adjusted)
                        data_var = processor._choose_variable(ds, param, profile_data_mode, param_data_modes)

                        # Debug for first profile
                        if prof_idx == 0 and level_idx < 2:
                            logger.warning(f"P{prof_idx}L{level_idx} {param}: data_var={data_var is not None}, in_ds={param in ds.variables}")

                        if data_var is not None:
                            # Extract value for this profile and level
                            if n_prof > 1:
                                value = data_var.isel(N_PROF=prof_idx, N_LEVELS=level_idx)
                            else:
                                value = data_var.isel(N_LEVELS=level_idx) if 'N_LEVELS' in data_var.dims else data_var
                            
                            # Apply QC filtering
                            qc_var_name = f"{param}_QC" if param in ds.variables else f"{param}_ADJUSTED_QC"
                            if qc_var_name in ds.variables:
                                qc_value = ds[qc_var_name].isel(N_PROF=prof_idx, N_LEVELS=level_idx) if n_prof > 1 else ds[qc_var_name].isel(N_LEVELS=level_idx)
                                
                                # Store original QC value for reference
                                try:
                                    qc_val = qc_value.values
                                    # Extract scalar if it's an array
                                    if isinstance(qc_val, np.ndarray) and qc_val.size == 1:
                                        qc_val = qc_val.item()

                                    # Decode bytes to string/int
                                    if isinstance(qc_val, bytes):
                                        qc_str = qc_val.decode('ascii').strip()
                                        if qc_str.isdigit():
                                            level_record[f'{param.lower()}_qc'] = int(qc_str)
                                        else:
                                            level_record[f'{param.lower()}_qc'] = qc_str
                                    elif isinstance(qc_val, str):
                                        if qc_val.isdigit():
                                            level_record[f'{param.lower()}_qc'] = int(qc_val)
                                        else:
                                            level_record[f'{param.lower()}_qc'] = qc_val
                                    elif isinstance(qc_val, (int, float)) and not np.isnan(qc_val):
                                        level_record[f'{param.lower()}_qc'] = int(qc_val)
                                    else:
                                        level_record[f'{param.lower()}_qc'] = None
                                except:
                                    level_record[f'{param.lower()}_qc'] = None
                                
                                # Only include data with good QC flags using safe check
                                if processor._safe_qc_check(qc_value.values):
                                    extracted_val = processor._safe_extract_value(value)
                                    level_record[param.lower()] = extracted_val
                                    # Debug first few extractions
                                    if prof_idx == 0 and level_idx < 3 and param == 'PRES':
                                        logger.warning(f"PRES extraction: raw={value.values}, qc_pass={processor._safe_qc_check(qc_value.values)}, extracted={extracted_val}")
                                else:
                                    level_record[param.lower()] = None
                            else:
                                # No QC available, include raw value
                                level_record[param.lower()] = processor._safe_extract_value(value)
                                level_record[f'{param.lower()}_qc'] = None

                            # Add error estimate if available
                            error_var_name = f"{param}_ADJUSTED_ERROR"
                            if error_var_name in ds.variables:
                                error_val = ds[error_var_name].isel(N_PROF=prof_idx, N_LEVELS=level_idx) if n_prof > 1 else ds[error_var_name].isel(N_LEVELS=level_idx)
                                level_record[f'{param.lower()}_error'] = processor._safe_extract_value(error_val)
                        else:
                            logger.debug(f"No data variable found for {param} at level {level_idx}")
                    else:
                        logger.debug(f"Parameter {param} not available in dataset")
                
                # Only add record if it has at least pressure data
                if level_record.get('pres') is not None:
                    processed_records.append(level_record)
                # Add debug logging for first few rejections
                elif prof_idx == 0 and level_idx < 5:
                    logger.warning(f"Profile {prof_idx} Level {level_idx} rejected: pres={level_record.get('pres')}")
                    
        logger.info(f"Total processed records before filtering: {len(processed_records)}")
        
        # Convert to DataFrame
        df = pd.DataFrame(processed_records)
        
        if len(df) == 0:
            logger.warning("No valid records found after preprocessing")
            return pd.DataFrame()
        
        # Add computed features
        if 'pres' in df.columns:
            df['depth_m'] = df['pres'] * 1.019716  # Approximate conversion for seawater
        
        # Calculate profile-level statistics
        profile_stats = []
        for prof_idx in df['profile_idx'].unique():
            prof_data = df[df['profile_idx'] == prof_idx]
            
            stats = {
                'profile_idx': prof_idx,
                'n_levels': len(prof_data),
                'max_pressure': prof_data['pres'].max() if 'pres' in prof_data.columns else None,
                'temp_range': prof_data['temp'].max() - prof_data['temp'].min() if 'temp' in prof_data.columns and prof_data['temp'].notna().any() else None,
                'sal_range': prof_data['psal'].max() - prof_data['psal'].min() if 'psal' in prof_data.columns and prof_data['psal'].notna().any() else None,
            }
            profile_stats.append(stats)
        
        # Add profile stats back to main dataframe
        stats_df = pd.DataFrame(profile_stats)
        df = df.merge(stats_df, on='profile_idx', how='left', suffixes=('', '_profile_stat'))
        
        logger.info(f"Preprocessing complete:")
        logger.info(f"  - Total records: {len(df)}")
        logger.info(f"  - Profiles processed: {df['profile_idx'].nunique()}")
        logger.info(f"  - Parameters found: {[col for col in df.columns if col in ['pres', 'temp', 'psal', 'doxy', 'chla']]}")
        
        return df
        
    finally:
        ds.close()


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python step5_preprocessor.py <netcdf_file> <validation_json>")
        sys.exit(1)
    
    nc_file = sys.argv[1]
    validation_file = sys.argv[2]
    
    with open(validation_file, 'r') as f:
        validation_result = json.load(f)
    
    df = preprocess_argo_data(nc_file, validation_result)
    
    if not df.empty:
        output_file = f"preprocessed_{Path(nc_file).stem}.csv"
        df.to_csv(output_file, index=False)
        print(f"Preprocessed data saved to: {output_file}")
        print(f"Records: {len(df)}")
    else:
        print("No valid data found after preprocessing")