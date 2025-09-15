#!/usr/bin/env python3
"""
Step 6: Argo Data Export to Parquet
Exports preprocessed data to Parquet format with metadata preservation
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from prefect import task, get_run_logger


@task(name="export-to-parquet")
def export_to_parquet(
    df: pd.DataFrame, 
    output_dir: str = "output", 
    file_prefix: Optional[str] = None,
    include_metadata: bool = True
) -> Dict[str, str]:
    """
    Export preprocessed Argo data to Parquet format with metadata
    
    Args:
        df: Preprocessed DataFrame from step 5
        output_dir: Directory to save output files
        file_prefix: Prefix for output files (auto-generated if None)
        include_metadata: Whether to include processing metadata
        
    Returns:
        Dictionary with file paths of created files
    """
    logger = get_run_logger()
    
    if df.empty:
        logger.error("Cannot export empty DataFrame")
        raise ValueError("DataFrame is empty")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate file prefix if not provided
    if file_prefix is None:
        if 'file_name' in df.columns:
            original_name = df['file_name'].iloc[0]
            file_prefix = Path(original_name).stem
        else:
            file_prefix = "argo_data"
    
    logger.info(f"Exporting data to Parquet format with prefix: {file_prefix}")
    
    created_files = {}
    
    # 1. Export main data to Parquet
    main_parquet_path = output_path / f"{file_prefix}_data.parquet"
    
    # Optimize data types before export
    optimized_df = optimize_dataframe_dtypes(df)
    
    # Create Parquet table with metadata
    table = pa.Table.from_pandas(optimized_df)
    
    # Add custom metadata
    if include_metadata:
        processing_metadata = {
            'source_file': df['file_name'].iloc[0] if 'file_name' in df.columns else 'unknown',
            'processing_timestamp': pd.Timestamp.now().isoformat(),
            'total_records': str(len(df)),
            'total_profiles': str(df['profile_idx'].nunique()) if 'profile_idx' in df.columns else '1',
            'parameters_included': ','.join([col for col in df.columns if col in ['pres', 'temp', 'psal', 'doxy', 'chla', 'bbp', 'ph_in_situ_total', 'nitrate']]),
            'data_quality': 'qc_filtered' if any('_qc' in col for col in df.columns) else 'unfiltered',
            'coordinate_bounds': json.dumps({
                'lat_min': float(df['latitude'].min()) if 'latitude' in df.columns else None,
                'lat_max': float(df['latitude'].max()) if 'latitude' in df.columns else None,
                'lon_min': float(df['longitude'].min()) if 'longitude' in df.columns else None,
                'lon_max': float(df['longitude'].max()) if 'longitude' in df.columns else None,
                'pressure_max': float(df['pres'].max()) if 'pres' in df.columns else None
            })
        }
        
        # Add metadata to Parquet table
        existing_metadata = table.schema.metadata or {}
        updated_metadata = {**existing_metadata}
        for key, value in processing_metadata.items():
            updated_metadata[f'argo_processing_{key}'.encode()] = str(value).encode()
        
        table = table.replace_schema_metadata(updated_metadata)
    
    # Write with compression and optimal settings
    pq.write_table(
        table,
        main_parquet_path,
        compression='snappy',  # Good balance of speed and compression
        use_dictionary=True,   # Efficient for string columns
        write_statistics=True, # Enable column statistics for better querying
        row_group_size=50000   # Optimize for typical Argo profile sizes
    )
    
    created_files['data_parquet'] = str(main_parquet_path)
    logger.info(f"Main data exported to: {main_parquet_path}")
    
    # 2. Export profile-level summary
    if 'profile_idx' in df.columns:
        profile_summary = create_profile_summary(df)
        profile_parquet_path = output_path / f"{file_prefix}_profiles.parquet"
        profile_summary.to_parquet(profile_parquet_path, compression='snappy')
        created_files['profiles_parquet'] = str(profile_parquet_path)
        logger.info(f"Profile summary exported to: {profile_parquet_path}")
    
    # 3. Export data quality report
    quality_report = create_quality_report(df)
    quality_json_path = output_path / f"{file_prefix}_quality_report.json"
    with open(quality_json_path, 'w') as f:
        json.dump(quality_report, f, indent=2, default=str)
    created_files['quality_report'] = str(quality_json_path)
    
    # 4. Export processing log
    processing_log = {
        'file_prefix': file_prefix,
        'export_timestamp': pd.Timestamp.now().isoformat(),
        'input_records': len(df),
        'columns_exported': list(df.columns),
        'files_created': created_files,
        'parquet_compression': 'snappy',
        'optimization_applied': True
    }
    
    log_path = output_path / f"{file_prefix}_processing_log.json"
    with open(log_path, 'w') as f:
        json.dump(processing_log, f, indent=2, default=str)
    created_files['processing_log'] = str(log_path)
    
    logger.info(f"Export complete. Files created:")
    for file_type, file_path in created_files.items():
        logger.info(f"  - {file_type}: {file_path}")
    
    return created_files


def optimize_dataframe_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Optimize DataFrame data types for efficient Parquet storage"""
    optimized_df = df.copy()
    
    # Optimize integer columns
    int_cols = df.select_dtypes(include=['int64']).columns
    for col in int_cols:
        if col.endswith('_qc') or col in ['profile_idx', 'level_idx', 'cycle_number']:
            # QC flags and indices can be int8/int16
            if df[col].max() < 128:
                optimized_df[col] = df[col].astype('Int8')  # Nullable int8
            else:
                optimized_df[col] = df[col].astype('Int16')  # Nullable int16
        else:
            optimized_df[col] = df[col].astype('Int32')  # Nullable int32
    
    # Optimize float columns for scientific data
    float_cols = df.select_dtypes(include=['float64']).columns
    for col in float_cols:
        if col in ['latitude', 'longitude']:
            # High precision needed for coordinates
            optimized_df[col] = df[col].astype('float64')
        else:
            # Scientific measurements can use float32 for space efficiency
            optimized_df[col] = df[col].astype('float32')
    
    # Optimize string columns
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        if df[col].dtype == 'object' and pd.api.types.is_string_dtype(df[col]):
            optimized_df[col] = df[col].astype('string')  # Use pandas string type
    
    # Convert timestamp strings to datetime if possible
    if 'timestamp' in df.columns:
        try:
            optimized_df['timestamp'] = pd.to_datetime(df['timestamp'])
        except:
            pass  # Keep as string if conversion fails
    
    return optimized_df


def create_profile_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create profile-level summary statistics"""
    summary_stats = []
    
    for profile_idx in df['profile_idx'].unique():
        prof_data = df[df['profile_idx'] == profile_idx]
        
        summary = {
            'profile_idx': profile_idx,
            'float_id': prof_data['float_id'].iloc[0] if 'float_id' in prof_data.columns else None,
            'timestamp': prof_data['timestamp'].iloc[0] if 'timestamp' in prof_data.columns else None,
            'latitude': prof_data['latitude'].iloc[0] if 'latitude' in prof_data.columns else None,
            'longitude': prof_data['longitude'].iloc[0] if 'longitude' in prof_data.columns else None,
            'n_levels': len(prof_data),
            'max_pressure': prof_data['pres'].max() if 'pres' in prof_data.columns else None,
            'min_pressure': prof_data['pres'].min() if 'pres' in prof_data.columns else None,
        }
        
        # Add parameter-specific statistics
        for param in ['temp', 'psal', 'doxy']:
            if param in prof_data.columns:
                valid_data = prof_data[param].dropna()
                if len(valid_data) > 0:
                    summary[f'{param}_min'] = valid_data.min()
                    summary[f'{param}_max'] = valid_data.max()
                    summary[f'{param}_mean'] = valid_data.mean()
                    summary[f'{param}_count'] = len(valid_data)
        
        summary_stats.append(summary)
    
    return pd.DataFrame(summary_stats)


def create_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Create data quality assessment report"""
    report = {
        'total_records': len(df),
        'completeness': {},
        'qc_summary': {},
        'coordinate_coverage': {},
        'parameter_coverage': {}
    }
    
    # Completeness analysis
    for col in df.columns:
        if col not in ['profile_idx', 'level_idx', 'file_name']:
            non_null_count = df[col].notna().sum()
            report['completeness'][col] = {
                'non_null_count': int(non_null_count),
                'completeness_ratio': float(non_null_count / len(df))
            }
    
    # QC flag analysis
    qc_cols = [col for col in df.columns if col.endswith('_qc')]
    for qc_col in qc_cols:
        qc_counts = df[qc_col].value_counts().to_dict()
        report['qc_summary'][qc_col] = {int(k): int(v) for k, v in qc_counts.items() if pd.notna(k)}
    
    # Coordinate coverage
    if 'latitude' in df.columns and 'longitude' in df.columns:
        valid_coords = df[['latitude', 'longitude']].dropna()
        if len(valid_coords) > 0:
            report['coordinate_coverage'] = {
                'valid_coordinates': len(valid_coords),
                'lat_range': [float(valid_coords['latitude'].min()), float(valid_coords['latitude'].max())],
                'lon_range': [float(valid_coords['longitude'].min()), float(valid_coords['longitude'].max())]
            }
    
    # Parameter coverage
    core_params = ['pres', 'temp', 'psal']
    bgc_params = ['doxy', 'chla', 'bbp']
    
    for param in core_params + bgc_params:
        if param in df.columns:
            valid_data = df[param].notna().sum()
            report['parameter_coverage'][param] = {
                'available': True,
                'valid_measurements': int(valid_data),
                'coverage_ratio': float(valid_data / len(df))
            }
        else:
            report['parameter_coverage'][param] = {'available': False}
    
    return report


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python step6_exporter.py <preprocessed_csv> [output_dir]")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    # Load preprocessed data
    df = pd.read_csv(csv_file)
    
    # Export to Parquet
    result = export_to_parquet(df, output_dir)
    
    print("Export completed successfully!")
    for file_type, path in result.items():
        print(f"{file_type}: {path}")