# Argo NetCDF Data Profiling Pipeline Setup Guide

## Project Structure
```
DATAOPS/
├── step3_schema_explorer.py    # Schema exploration module
├── step4_data_validator.py          # Data validation module  
├── step5_data_preprocessor.py       # Data preprocessing module
├── step6_data_exporter.py           # Parquet export module
├── main_orchestrator.py             # Prefect orchestration DAG
├── data/                       # Input NetCDF files
└── output/                     # Processed output files
```

## Environment Setup with uv 

### 1. Create Virtual Environment
```bash
# Create virtual environment with Python 3.11
uv venv --python 3.11

# Activate environment (uv auto-activates for subsequent commands)
source .venv/bin/activate  # On Linux/Mac
# OR
.venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
```bash
# Install core scientific computing packages
uv pip install \
    xarray \
    netcdf4 \
    numpy \
    pandas \
    pyarrow \
    prefect \
    pydantic \
    cftime

# Install additional utilities
uv pip install \
    pathlib \
    asyncio \
    argparse
```

### 3. Alternative: Install from requirements.txt
```bash
# Save this as requirements.txt first, then:
uv pip install -r requirements.txt
```

## Requirements.txt Content
```
# Core scientific computing
xarray>=2024.1.0
netcdf4>=1.6.0
numpy>=1.24.0
pandas>=2.0.0
pyarrow>=15.0.0
cftime>=1.6.0

# Workflow orchestration
prefect>=2.18.0

# Data validation
pydantic>=2.5.0

# Standard library enhancements (usually included)
pathlib2>=2.3.7
```

## Usage Examples

### Single File Processing
```bash
# Process a single Argo NetCDF file
python pipeline_dag.py /path/to/your/argo_file.nc -o output_directory

# With additional options
python pipeline_dag.py /path/to/your/argo_file.nc \
    -o output \
    --skip-validation \
    --save-results
```

### Batch Processing
```bash
# Process all NetCDF files in a directory
python pipeline_dag.py /path/to/netcdf_directory \
    --batch \
    -o output \
    --max-concurrent 3

# Batch with error handling
python pipeline_dag.py /path/to/netcdf_directory \
    --batch \
    --skip-validation \
    --save-results \
    -o output
```

### Individual Step Execution
```bash
# Run only schema exploration
python step3_schema_explorer.py your_file.nc

# Run validation (requires schema JSON)
python step4_validator.py your_file.nc schema_report.json

# Run preprocessing (requires validation JSON)
python step5_preprocessor.py your_file.nc validation_report.json

# Export to Parquet (requires preprocessed CSV)
python step6_exporter.py preprocessed_data.csv output_directory
```

## Pipeline Output Files

### For Each Processed File:
- `{filename}_data.parquet` - Main processed data in Parquet format
- `{filename}_profiles.parquet` - Profile-level summary statistics  
- `{filename}_quality_report.json` - Data quality assessment
- `{filename}_processing_log.json` - Processing metadata and logs

### Pipeline Results:
- `{filename}_pipeline_results.json` - Complete pipeline execution results
- `batch_results.json` - Batch processing summary (batch mode)

## Data Validation Rules

The pipeline follows Argo best practices:

### Core Variables Required:
- `JULD` (timestamp)
- `LATITUDE` (-90 to 90)
- `LONGITUDE` (-180 to 180)  
- `PRES` (pressure, >= 0)

### Data Mode Handling:
- **Real-time ('R')**: Use raw variables (e.g., `TEMP`)
- **Adjusted/Delayed ('A'/'D')**: Use adjusted variables (e.g., `TEMP_ADJUSTED`)
- **BGC files**: Use `PARAMETER_DATA_MODE` per parameter

### Quality Control:
- Prefer QC flags 1 (good) and 2 (probably good)
- Filter out QC flags 3, 4 (bad data)
- Include QC flag 8 (estimated) only if specified

### Parameter Ranges:
- Temperature: -5°C to 50°C
- Salinity: 0 to 50 PSU
- Pressure: 0 to 6000 dbar

## Prefect Integration

### Start Prefect Server (Optional)
```bash
# Start local Prefect server for monitoring
prefect server start

# In another terminal, set Prefect API URL
export PREFECT_API_URL="http://127.0.0.1:4200/api"
```

### Monitor Flows
- Open http://localhost:4200 in browser
- View flow runs, logs, and task details
- Monitor pipeline performance and errors

## Troubleshooting

### Common Issues:

1. **NetCDF4 Installation Problems**
   ```bash
   # On Ubuntu/Debian
   sudo apt-get install libnetcdf-dev libhdf5-dev

   # On macOS with Homebrew
   brew install netcdf hdf5

   # Reinstall Python packages
   uv pip uninstall netcdf4
   uv pip install netcdf4
   ```

2. **Memory Issues with Large Files**
   - Reduce `max_concurrent` parameter in batch mode
   - Process files individually instead of batch
   - Increase system memory or use smaller test files

3. **Validation Failures**
   ```bash
   # Skip validation errors to continue processing
   python pipeline_dag.py your_file.nc --skip-validation
   ```

4. **Missing Adjusted Variables**
   - Check if file is real-time ('R') vs delayed mode ('D')
   - Real-time files may not have `*_ADJUSTED` variables
   - This is normal and handled by the pipeline

### File Type Detection:
- `R*.nc` - Real-time core profiles
- `D*.nc` - Delayed mode core profiles  
- `BR*.nc` - Real-time BGC profiles
- `BD*.nc` - Delayed mode BGC profiles
- `SR*.nc` - Real-time synthetic profiles
- `SD*.nc` - Delayed mode synthetic profiles

## Performance Notes

- **Single file**: ~1-5 seconds for typical Argo profile
- **Batch processing**: Scales with `max_concurrent` setting
- **Memory usage**: ~50-200MB per file during processing
- **Output size**: Parquet files are ~10-30% smaller than original NetCDF

## Integration with FloatChat Project

The processed Parquet files from this pipeline are optimized for:

1. **SQL Database Loading**: Clean, validated tabular format
2. **Vector Database Indexing**: Metadata and summary statistics
3. **RAG/LLM Integration**: Quality-filtered data with context
4. **Dashboard Visualization**: Profile summaries and geospatial data
5. **Natural Language Queries**: Structured format for SQL generation

This pipeline implements steps 3-6 of your ASCII diagram and provides the foundation for the remaining FloatChat components (database loading, AI integration, and visualization).