"""
API routes for NetCDF file processing and ARGO data ingestion
"""

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..services.netcdf_processor import NetCDFProcessor, process_argo_file, process_argo_directory
from ..services.rag_pipeline import RAGPipeline, process_natural_language_query
from ..models.profile import Profile, DataSummary

router = APIRouter(prefix="/netcdf", tags=["NetCDF Processing"])

# Request/Response models
class ProcessingStatus(BaseModel):
    task_id: str
    status: str
    message: str
    progress: Dict[str, Any] = {}

class ProcessingResult(BaseModel):
    files_processed: int
    profiles_extracted: int
    records_saved: int
    errors: int
    processing_time: float
    details: List[str] = []

class QueryRequest(BaseModel):
    query: str
    include_metadata: bool = True
    max_results: int = 1000

class QueryResponse(BaseModel):
    sql_query: str
    natural_language_response: str
    data_count: int
    data_results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    confidence_score: float

# Global processing status storage (in production, use Redis or database)
processing_tasks = {}

@router.post("/upload", response_model=ProcessingStatus)
async def upload_netcdf_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process a single NetCDF file"""
    
    # Validate file type
    if not file.filename.lower().endswith(('.nc', '.netcdf')):
        raise HTTPException(status_code=400, detail="File must be a NetCDF file (.nc or .netcdf)")
    
    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    processing_tasks[task_id] = {
        'status': 'uploading',
        'message': 'File upload in progress',
        'progress': {'step': 1, 'total_steps': 4}
    }
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Start background processing
        background_tasks.add_task(
            process_netcdf_background,
            task_id,
            tmp_file_path,
            file.filename,
            db
        )
        
        return ProcessingStatus(
            task_id=task_id,
            status="processing",
            message=f"Processing {file.filename}",
            progress={'step': 2, 'total_steps': 4}
        )
        
    except Exception as e:
        processing_tasks[task_id] = {
            'status': 'error',
            'message': f'Upload failed: {str(e)}',
            'progress': {'step': 0, 'total_steps': 4}
        }
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_netcdf_background(task_id: str, file_path: str, filename: str, db: Session):
    """Background task for processing NetCDF file"""
    
    try:
        # Update status
        processing_tasks[task_id] = {
            'status': 'processing',
            'message': 'Extracting profiles from NetCDF',
            'progress': {'step': 2, 'total_steps': 4}
        }
        
        # Process file
        processor = NetCDFProcessor()
        profiles = processor.process_netcdf_file(Path(file_path))
        
        # Update status
        processing_tasks[task_id] = {
            'status': 'saving',
            'message': 'Saving profiles to database',
            'progress': {'step': 3, 'total_steps': 4}
        }
        
        # Save to database
        saved_count = processor.save_profiles_to_database(profiles, db)
        
        # Clean up temporary file
        os.unlink(file_path)
        
        # Update final status
        processing_tasks[task_id] = {
            'status': 'completed',
            'message': f'Successfully processed {filename}',
            'progress': {'step': 4, 'total_steps': 4},
            'result': {
                'profiles_extracted': len(profiles),
                'records_saved': saved_count,
                'filename': filename
            }
        }
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.unlink(file_path)
        
        processing_tasks[task_id] = {
            'status': 'error',
            'message': f'Processing failed: {str(e)}',
            'progress': {'step': 0, 'total_steps': 4}
        }

@router.get("/status/{task_id}", response_model=ProcessingStatus)
async def get_processing_status(task_id: str):
    """Get processing status for a task"""
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = processing_tasks[task_id]
    
    return ProcessingStatus(
        task_id=task_id,
        status=task_info['status'],
        message=task_info['message'],
        progress=task_info.get('progress', {})
    )

@router.post("/process-directory")
async def process_netcdf_directory(
    directory_path: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process all NetCDF files in a directory"""
    
    # Validate directory
    dir_path = Path(directory_path)
    if not dir_path.exists() or not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid directory path")
    
    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # Start background processing
    background_tasks.add_task(
        process_directory_background,
        task_id,
        directory_path,
        db
    )
    
    return ProcessingStatus(
        task_id=task_id,
        status="processing",
        message=f"Processing directory: {directory_path}"
    )

async def process_directory_background(task_id: str, directory_path: str, db: Session):
    """Background task for processing directory of NetCDF files"""
    
    try:
        processing_tasks[task_id] = {
            'status': 'processing',
            'message': 'Scanning directory for NetCDF files'
        }
        
        # Process directory
        results = process_argo_directory(directory_path, db)
        
        processing_tasks[task_id] = {
            'status': 'completed',
            'message': 'Directory processing completed',
            'result': results
        }
        
    except Exception as e:
        processing_tasks[task_id] = {
            'status': 'error',
            'message': f'Directory processing failed: {str(e)}'
        }

@router.post("/query", response_model=QueryResponse)
async def natural_language_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Process natural language query using RAG pipeline"""
    
    try:
        # Process query through RAG pipeline
        result = process_natural_language_query(request.query, db)
        
        # Limit results if requested
        limited_results = result.data_results[:request.max_results]
        
        return QueryResponse(
            sql_query=result.sql_query,
            natural_language_response=result.natural_language_response,
            data_count=len(limited_results),
            data_results=limited_results if request.include_metadata else [],
            metadata=result.metadata,
            confidence_score=result.confidence_score
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.get("/validate/{filename}")
async def validate_netcdf_file(filename: str):
    """Validate NetCDF file format and structure"""
    
    file_path = Path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        processor = NetCDFProcessor()
        is_valid = processor.validate_netcdf_file(file_path)
        
        # Get basic file info
        import xarray as xr
        with xr.open_dataset(file_path) as ds:
            info = {
                'is_valid': is_valid,
                'variables': list(ds.variables.keys()),
                'dimensions': dict(ds.dims),
                'global_attributes': dict(ds.attrs),
                'file_size': file_path.stat().st_size
            }
        
        return info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/summary/generate")
async def generate_data_summaries(db: Session = Depends(get_db)):
    """Generate data summaries for RAG pipeline"""
    
    try:
        # Define regions for summary generation
        regions = [
            {
                'name': 'North Atlantic',
                'lat_min': 30, 'lat_max': 70,
                'lon_min': -80, 'lon_max': 0
            },
            {
                'name': 'Equatorial Pacific',
                'lat_min': -10, 'lat_max': 10,
                'lon_min': -180, 'lon_max': -80
            },
            {
                'name': 'Indian Ocean',
                'lat_min': -30, 'lat_max': 30,
                'lon_min': 20, 'lon_max': 120
            },
            {
                'name': 'Southern Ocean',
                'lat_min': -70, 'lat_max': -30,
                'lon_min': -180, 'lon_max': 180
            }
        ]
        
        summaries_created = 0
        
        for region in regions:
            # Query data for region
            profiles = db.query(Profile).filter(
                Profile.latitude >= region['lat_min'],
                Profile.latitude <= region['lat_max'],
                Profile.longitude >= region['lon_min'],
                Profile.longitude <= region['lon_max']
            ).all()
            
            if profiles:
                # Calculate statistics
                temps = [p.temperature for p in profiles if p.temperature]
                sals = [p.salinity for p in profiles if p.salinity]
                depths = [p.depth for p in profiles if p.depth]
                
                # Generate summary text
                summary_text = f"""
                The {region['name']} region contains {len(profiles)} ARGO float profiles.
                Temperature ranges from {min(temps):.1f}°C to {max(temps):.1f}°C with an average of {sum(temps)/len(temps):.1f}°C.
                Salinity ranges from {min(sals):.1f} to {max(sals):.1f} PSU with an average of {sum(sals)/len(sals):.1f} PSU.
                Depth measurements range from {min(depths):.0f}m to {max(depths):.0f}m.
                Data spans from {min(p.date for p in profiles if p.date)} to {max(p.date for p in profiles if p.date)}.
                """
                
                # Create summary record
                summary = DataSummary(
                    region_name=region['name'],
                    min_latitude=region['lat_min'],
                    max_latitude=region['lat_max'],
                    min_longitude=region['lon_min'],
                    max_longitude=region['lon_max'],
                    profile_count=len(profiles),
                    min_temperature=min(temps),
                    max_temperature=max(temps),
                    avg_temperature=sum(temps)/len(temps),
                    min_salinity=min(sals),
                    max_salinity=max(sals),
                    avg_salinity=sum(sals)/len(sals),
                    min_depth=min(depths),
                    max_depth=max(depths),
                    start_date=min(p.date for p in profiles if p.date),
                    end_date=max(p.date for p in profiles if p.date),
                    summary_text=summary_text.strip(),
                    keywords=['temperature', 'salinity', 'depth', region['name'].lower()]
                )
                
                db.add(summary)
                summaries_created += 1
        
        db.commit()
        
        return {
            'summaries_created': summaries_created,
            'message': f'Generated {summaries_created} regional summaries'
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@router.get("/stats")
async def get_processing_stats(db: Session = Depends(get_db)):
    """Get overall processing statistics"""
    
    try:
        # Count profiles by various dimensions
        total_profiles = db.query(Profile).count()
        unique_floats = db.query(Profile.float_id).distinct().count()
        
        # Date range
        date_range = db.query(
            db.func.min(Profile.date),
            db.func.max(Profile.date)
        ).first()
        
        # Geographic coverage
        geo_range = db.query(
            db.func.min(Profile.latitude),
            db.func.max(Profile.latitude),
            db.func.min(Profile.longitude),
            db.func.max(Profile.longitude)
        ).first()
        
        # Depth and parameter ranges
        param_ranges = db.query(
            db.func.min(Profile.depth),
            db.func.max(Profile.depth),
            db.func.min(Profile.temperature),
            db.func.max(Profile.temperature),
            db.func.min(Profile.salinity),
            db.func.max(Profile.salinity)
        ).first()
        
        return {
            'total_profiles': total_profiles,
            'unique_floats': unique_floats,
            'date_range': {
                'start': date_range[0],
                'end': date_range[1]
            },
            'geographic_coverage': {
                'latitude_range': [geo_range[0], geo_range[1]],
                'longitude_range': [geo_range[2], geo_range[3]]
            },
            'parameter_ranges': {
                'depth': [param_ranges[0], param_ranges[1]],
                'temperature': [param_ranges[2], param_ranges[3]],
                'salinity': [param_ranges[4], param_ranges[5]]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")
