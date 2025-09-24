#!/usr/bin/env python3
"""
FastAPI router for Voice AI capabilities.
Provides endpoints to start and stop the Pipecat voice pipeline.
"""

import logging
import subprocess
import sys
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice AI"])

# In-memory store for running voice processes
# For a production system, a more robust solution is needed.
voice_processes: Dict[str, subprocess.Popen] = {}

class VoiceSessionRequest(BaseModel):
    session_id: str

class VoiceSessionResponse(BaseModel):
    status: str
    session_id: str
    message: str

@router.post("/start", response_model=VoiceSessionResponse)
async def start_voice_session(request: VoiceSessionRequest):
    """Starts the Pipecat voice pipeline for a given session."""
    session_id = request.session_id
    if session_id in voice_processes and voice_processes[session_id].poll() is None:
        raise HTTPException(status_code=400, detail=f"Voice session {session_id} is already running.")

    try:
        voice_pipeline_script = "sih25/VOICE_AI/oceanographic_voice_pipeline.py"
        process = subprocess.Popen([sys.executable, voice_pipeline_script])
        voice_processes[session_id] = process
        logger.info(f"Started voice pipeline for session {session_id} with PID {process.pid}")
        
        return VoiceSessionResponse(
            status="started",
            session_id=session_id,
            message="Voice session started successfully."
        )
    except Exception as e:
        logger.error(f"Failed to start voice pipeline for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start voice session: {str(e)}")

@router.post("/stop", response_model=VoiceSessionResponse)
async def stop_voice_session(request: VoiceSessionRequest):
    """Stops the Pipecat voice pipeline for a given session."""
    session_id = request.session_id
    if session_id not in voice_processes or voice_processes[session_id].poll() is not None:
        raise HTTPException(status_code=404, detail=f"Voice session {session_id} not found or not running.")

    try:
        process = voice_processes[session_id]
        process.terminate()
        process.wait(timeout=5)
        
        del voice_processes[session_id]
        logger.info(f"Stopped voice pipeline for session {session_id} with PID {process.pid}")
        
        return VoiceSessionResponse(
            status="stopped",
            session_id=session_id,
            message="Voice session stopped successfully."
        )
    except Exception as e:
        logger.error(f"Failed to stop voice pipeline for session {session_id}: {e}")
        if session_id in voice_processes:
            del voice_processes[session_id]
        raise HTTPException(status_code=500, detail=f"Failed to stop voice session: {str(e)}")
