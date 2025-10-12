#!/usr/bin/env python3
"""
FastAPI DataOps Server for SIH25
This server provides an API to trigger the data processing pipeline with job tracking.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from pathlib import Path
import base64
import uuid
from datetime import datetime
from enum import Enum
import numpy as np

# Fixed import path to use proper package structure
from sih25.DATAOPS.PROFILES.main_orchestrator import argo_batch_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Job Status Enum
class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"

# In-memory job store (in production, use Redis or a database)
job_store: Dict[str, Dict] = {}

app = FastAPI(
    title="SIH25 DataOps Server",
    description="Provides an API to trigger the ARGO data processing pipeline with real-time status tracking.",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    files: Dict[str, str] # filename: base64_content
    output_dir: str = "output"
    load_to_database: bool = True

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int  # 0-100
    message: str
    files_processed: int
    files_total: int
    created_at: str
    updated_at: str
    results: Optional[Dict] = None
    errors: Optional[List[str]] = None

UPLOAD_DIR = "sih25/DATAOPS/PROFILES/data"

def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy types to Python native types for JSON serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj

# Helper functions for job management
def create_job(files_count: int) -> str:
    """Create a new processing job and return its ID"""
    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    job_store[job_id] = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "progress": 0,
        "message": "Job queued, waiting to start processing",
        "files_processed": 0,
        "files_total": files_count,
        "created_at": now,
        "updated_at": now,
        "results": None,
        "errors": []
    }
    return job_id

def update_job_status(
    job_id: str,
    status: Optional[JobStatus] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    files_processed: Optional[int] = None,
    results: Optional[Dict] = None,
    error: Optional[str] = None
):
    """Update job status"""
    if job_id not in job_store:
        return

    job = job_store[job_id]
    if status:
        job["status"] = status
    if progress is not None:
        job["progress"] = progress
    if message:
        job["message"] = message
    if files_processed is not None:
        job["files_processed"] = files_processed
    if results:
        # Convert numpy types to Python native types for JSON serialization
        job["results"] = convert_numpy_types(results)
    if error:
        job["errors"].append(error)

    job["updated_at"] = datetime.now().isoformat()

async def process_files_background(job_id: str, saved_files: List[str], output_dir: str, load_to_database: bool):
    """Background task to process files"""
    try:
        update_job_status(
            job_id,
            status=JobStatus.PROCESSING,
            progress=10,
            message="Starting data processing pipeline..."
        )

        # Run the pipeline
        results = await argo_batch_pipeline(
            nc_files=saved_files,
            output_dir=output_dir,
            load_to_database=load_to_database,
        )

        # Update progress
        files_processed = results.get("summary", {}).get("successful", 0)
        files_failed = results.get("summary", {}).get("failed", 0)

        if files_failed > 0:
            update_job_status(
                job_id,
                status=JobStatus.COMPLETED_WITH_ERRORS,
                progress=100,
                message=f"Processing completed with {files_failed} error(s)",
                files_processed=files_processed,
                results=results
            )
        else:
            update_job_status(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                message="All files processed successfully",
                files_processed=files_processed,
                results=results
            )

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        update_job_status(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            message=f"Processing failed: {str(e)}",
            error=str(e)
        )

@app.post("/upload", response_model=Dict)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    output_dir: str = "output",
    load_to_database: bool = True
):
    """
    Upload NetCDF files and start processing in the background.
    Returns a job_id for tracking progress.
    """
    logger.info(f"Received upload request for {len(files)} file(s)")

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    saved_files = []
    for file in files:
        try:
            # Validate file extension
            if not file.filename.endswith('.nc'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {file.filename}. Only .nc files are supported."
                )

            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)
            logger.info(f"Saved uploaded file to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to save file {file.filename}: {str(e)}")

    if not saved_files:
        raise HTTPException(status_code=400, detail="No valid files were uploaded")

    # Create job
    job_id = create_job(len(saved_files))

    # Start background processing
    background_tasks.add_task(
        process_files_background,
        job_id,
        saved_files,
        os.path.join("sih25/DATAOPS/PROFILES", output_dir),
        load_to_database
    )

    logger.info(f"Created job {job_id} for {len(saved_files)} file(s)")

    return {
        "job_id": job_id,
        "message": "Files uploaded successfully. Processing started.",
        "files_count": len(saved_files),
        "files": [os.path.basename(f) for f in saved_files]
    }

@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a processing job"""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(**job_store[job_id])

@app.get("/jobs")
async def list_jobs(limit: int = 50):
    """List recent jobs"""
    jobs = list(job_store.values())
    # Sort by created_at descending
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    # Convert numpy types to ensure JSON serialization
    jobs = [convert_numpy_types(job) for job in jobs[:limit]]
    return {"jobs": jobs, "total": len(job_store)}

@app.post("/process")
async def process_files(request: ProcessRequest):
    """
    Receives files, saves them, and triggers the Argo data processing pipeline.
    """
    logger.info(f"Received request to process {len(request.files)} files.")
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    saved_files = []
    for filename, content in request.files.items():
        try:
            content_type, content_string = content.split(',')
            decoded_content = base64.b64decode(content_string)
            
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(decoded_content)
            saved_files.append(file_path)
            logger.info(f"Saved uploaded file to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid file content for {filename}.")

    if not saved_files:
        raise HTTPException(status_code=400, detail="No valid files were processed.")

    try:
        results = await argo_batch_pipeline(
            nc_files=saved_files,
            output_dir=os.path.join("sih25/DATAOPS/PROFILES", request.output_dir),
            load_to_database=request.load_to_database,
        )

        # Convert numpy types to Python native types for JSON serialization
        results = convert_numpy_types(results)

        if results.get("summary", {}).get("failed", 0) > 0:
            return {
                "status": "completed_with_errors",
                "results": results
            }

        return {
            "status": "completed",
            "results": results
        }

    except Exception as e:
        logger.error(f"Data processing pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "DataOps Server"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("DATAOPS_API_PORT", "8002"))
    host = os.getenv("API_HOST", "0.0.0.0")

    logger.info(f"Starting DataOps Server on {host}:{port}")
    uvicorn.run(
        "sih25.DATAOPS.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )