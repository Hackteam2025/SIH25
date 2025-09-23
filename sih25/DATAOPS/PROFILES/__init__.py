"""
DATAOPS Module - ARGO NetCDF Data Processing Pipeline

This module contains the complete data processing pipeline for ARGO oceanographic data:

Components:
- step3_schema_explorer: NetCDF schema exploration and profiling
- step4_data_validator: Data validation with quality control
- step5_data_preprocessor: Data cleaning and preprocessing 
- step6_data_exporter_parquet: Export to Parquet format
- main_orchestrator: Prefect-based workflow orchestration

Usage:
    from sih25.DATAOPS import main_orchestrator
    
    # Run single file pipeline
    result = await main_orchestrator.argo_data_pipeline(
        "path/to/file.nc", 
        "output_directory"
    )
"""

__all__ = [
    "main_orchestrator",
    "step3_schema_explorer", 
    "step4_data_validator",
    "step5_data_preprocessor",
    "step6_data_exporter_parquet",
]

# Import main components
try:
    from . import main_orchestrator
    from . import step3_schema_explorer
    from . import step4_data_validator
    from . import step5_data_preprocessor
    from . import step6_data_exporter_parquet
except ImportError as e:
    # Handle missing dependencies gracefully during development
    print(f"Warning: Could not import DATAOPS components: {e}")
    pass