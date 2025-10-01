#!/usr/bin/env python3
"""
FastAPI DataOps Server for SIH25
This server provides an API to trigger the data processing pipeline.
"""

import os
import logging
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from pathlib import Path
import base64

# Fixed import path to use proper package structure
from sih25.DATAOPS.PROFILES.main_orchestrator import argo_batch_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SIH25 DataOps Server",
    description="Provides an API to trigger the ARGO data processing pipeline.",
    version="1.0.0",
)

class ProcessRequest(BaseModel):
    files: Dict[str, str] # filename: base64_content
    output_dir: str = "output"
    load_to_database: bool = True

UPLOAD_DIR = "sih25/DATAOPS/PROFILES/data"

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