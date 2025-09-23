#!/usr/bin/env python3
"""
Step 3: Argo NetCDF Schema Exploration
Analyzes NetCDF structure, variables, dimensions, and key attributes
"""

import json
from pathlib import Path
from typing import Dict, Any
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import xarray as xr
from prefect import task, get_run_logger


@task(name="schema-exploration")
def explore_argo_schema(nc_file_path: str) -> Dict[str, Any]:
    """
    Analyze Argo NetCDF file structure and extract schema information
    
    Args:
        nc_file_path: Path to NetCDF file
        
    Returns:
        Dict containing schema information
    """
    logger = get_run_logger()
    nc_file = Path(nc_file_path)
    
    logger.info(f"Starting schema exploration for: {nc_file.name}")
    
    # Open dataset without automatic decoding to see raw structure
    ds = xr.open_dataset(nc_file, decode_cf=False, mask_and_scale=False)
    
    try:
        schema_info = {
            "file_name": nc_file.name,
            "file_size_mb": round(nc_file.stat().st_size / (1024*1024), 2),
            "dimensions": dict(ds.dims),
            "variables": {},
            "global_attributes": dict(ds.attrs),
            "data_mode_info": {},
            "parameter_info": {},
            "qc_variables": [],
            "core_variables": [],
            "bgc_variables": []
        }
        
        # Core Argo variables (always present)
        core_vars = ['PRES', 'TEMP', 'PSAL', 'JULD', 'LATITUDE', 'LONGITUDE']
        # Common BGC variables
        bgc_vars = ['DOXY', 'CHLA', 'BBP', 'PH_IN_SITU_TOTAL', 'NITRATE']
        
        # Analyze each variable
        for var_name, var in ds.data_vars.items():
            var_info = {
                "dtype": str(var.dtype),
                "dimensions": list(var.dims),
                "shape": var.shape,
                "attributes": dict(var.attrs),
                "has_qc": f"{var_name}_QC" in ds.variables,
                "has_adjusted": f"{var_name}_ADJUSTED" in ds.variables,
                "sample_values": None
            }
            
            # Get sample values (first few non-NaN values)
            try:
                values = var.values.flatten()
                valid_values = values[~np.isnan(values.astype(float))][:5] if len(values) > 0 else []
                var_info["sample_values"] = [float(v) for v in valid_values] if len(valid_values) > 0 else None
            except:
                var_info["sample_values"] = None
            
            schema_info["variables"][var_name] = var_info
            
            # Categorize variables
            if var_name in core_vars:
                schema_info["core_variables"].append(var_name)
            elif var_name in bgc_vars:
                schema_info["bgc_variables"].append(var_name)
        
        # Extract QC variables
        qc_vars = [v for v in ds.variables if v.endswith('_QC')]
        schema_info["qc_variables"] = qc_vars
        
        # Extract DATA_MODE information
        if "DATA_MODE" in ds.variables:
            try:
                data_mode_raw = ds["DATA_MODE"].values
                if hasattr(data_mode_raw, 'tobytes'):
                    data_modes = [data_mode_raw.tobytes().decode('ascii').strip()]
                else:
                    data_modes = [str(dm).strip() for dm in data_mode_raw.flatten()]
                schema_info["data_mode_info"]["available_modes"] = list(set(data_modes))
                schema_info["data_mode_info"]["primary_mode"] = data_modes[0] if data_modes else None
            except Exception as e:
                logger.warning(f"Could not extract DATA_MODE: {e}")
        
        # Extract PARAMETER information (BGC files)
        if "PARAMETER" in ds.variables:
            try:
                param_var = ds["PARAMETER"]
                if param_var.values.dtype.kind in ('S', 'U'):  # String types
                    params = [str(p).strip() for p in param_var.values.flatten() if str(p).strip()]
                else:  # Character arrays
                    params = []
                    for i in range(param_var.shape[0]):
                        param_chars = param_var.values[i] if param_var.ndim > 1 else param_var.values
                        param_str = ''.join([chr(c) for c in param_chars if c != 0]).strip()
                        if param_str:
                            params.append(param_str)
                
                schema_info["parameter_info"]["available_parameters"] = list(set(params))
                schema_info["parameter_info"]["parameter_count"] = len(set(params))
            except Exception as e:
                logger.warning(f"Could not extract PARAMETER info: {e}")
        
        # File type detection
        file_type = "unknown"
        if nc_file.name.startswith(('R', 'D')):
            file_type = "core_profile"
        elif nc_file.name.startswith(('BR', 'BD')):
            file_type = "bgc_profile"
        elif nc_file.name.startswith(('SR', 'SD')):
            file_type = "synthetic_profile"
        elif nc_file.name.endswith('_meta.nc'):
            file_type = "metadata"
        elif nc_file.name.endswith('_Rtraj.nc') or nc_file.name.endswith('_Dtraj.nc'):
            file_type = "trajectory"
        
        schema_info["file_type"] = file_type
        
        # Summary statistics
        schema_info["summary"] = {
            "total_variables": len(schema_info["variables"]),
            "qc_variables_count": len(qc_vars),
            "core_variables_found": len(schema_info["core_variables"]),
            "bgc_variables_found": len(schema_info["bgc_variables"]),
            "has_adjusted_data": any(v["has_adjusted"] for v in schema_info["variables"].values()),
            "estimated_profiles": schema_info["dimensions"].get("N_PROF", 1),
            "max_levels": schema_info["dimensions"].get("N_LEVELS", 0)
        }
        
        logger.info(f"Schema exploration complete:")
        logger.info(f"  - File type: {file_type}")
        logger.info(f"  - Variables: {len(schema_info['variables'])}")
        logger.info(f"  - Profiles: {schema_info['summary']['estimated_profiles']}")
        logger.info(f"  - Max levels: {schema_info['summary']['max_levels']}")
        
        return schema_info
        
    finally:
        ds.close()


def save_schema_report(schema_info: Dict[str, Any], output_file: str = None) -> str:
    """Save schema information to JSON file"""
    if output_file is None:
        output_file = f"schema_report_{schema_info['file_name']}.json"
    
    output_path = Path(output_file)
    with open(output_path, 'w') as f:
        json.dump(schema_info, f, indent=2, default=str)
    
    return str(output_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python step3_schema_explorer.py <netcdf_file>")
        sys.exit(1)
    
    nc_file = sys.argv[1]
    schema = explore_argo_schema(nc_file)
    report_file = save_schema_report(schema)
    print(f"Schema report saved to: {report_file}")