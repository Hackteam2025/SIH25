#!/usr/bin/env python3
"""
FastAPI router for Voice AI capabilities with Daily.co integration.
Provides /voice/connect endpoint for Pipecat React client.
"""

import logging
import subprocess
import sys
import os
import asyncio
from typing import Dict, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiohttp

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice AI"])

# Store for running bot processes
voice_processes: Dict[str, subprocess.Popen] = {}


class VoiceConnectRequest(BaseModel):
    """Request model for voice connect endpoint"""
    session_id: Optional[str] = None
    config: Optional[Dict] = None


class VoiceConnectResponse(BaseModel):
    """Response model containing Daily.co room info"""
    url: str
    token: str
    session_id: str
    bot_ready: bool


class DailyRoomHelper:
    """Helper class for Daily.co room creation"""

    def __init__(self):
        self.api_key = os.getenv("DAILY_API_KEY")
        self.api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
        self.room_url = os.getenv("DAILY_ROOM_URL")

        if not self.api_key:
            raise ValueError("DAILY_API_KEY not configured")

    async def create_room_and_token(self) -> tuple[str, str]:
        """Create a Daily.co room and token"""

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # If DAILY_ROOM_URL is set, use it; otherwise create a new room
            if self.room_url:
                logger.info(f"Using pre-configured Daily room: {self.room_url}")
                room_url = self.room_url
                # Extract room name from URL (e.g., https://pdv.daily.co/prada -> prada)
                room_name = room_url.split('/')[-1]
            else:
                # Create a new room
                room_config = {
                    "properties": {
                        "enable_chat": False,
                        "enable_screenshare": False,
                        "enable_recording": False,
                        "max_participants": 2,  # Just user and bot
                        "exp": int((datetime.now().timestamp() + 3600))  # 1 hour expiry
                    }
                }

                async with session.post(
                    f"{self.api_url}/rooms",
                    headers=headers,
                    json=room_config
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to create Daily room: {error}"
                        )

                    room_data = await response.json()
                    room_url = room_data["url"]
                    room_name = room_data["name"]

            # Always create a proper meeting token (not API key!)
            token_config = {
                "properties": {
                    "room_name": room_name,
                    "is_owner": False,
                    "exp": int((datetime.now().timestamp() + 3600))
                }
            }

            async with session.post(
                f"{self.api_url}/meeting-tokens",
                headers=headers,
                json=token_config
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create meeting token: {error}"
                    )

                token_data = await response.json()
                token = token_data["token"]

            logger.info(f"Created/using Daily room: {room_url} with meeting token")
            return room_url, token


@router.post("/connect")
async def voice_connect(request: dict = None):
    """
    Pipecat React client connects here to establish voice session.
    Returns Daily.co room configuration in the format Pipecat expects: { url, token }
    """
    try:
        # Extract session_id from request if present
        session_id = None
        if request and isinstance(request, dict):
            session_id = request.get("session_id") or f"voice-{datetime.now().timestamp()}"
        else:
            session_id = f"voice-{datetime.now().timestamp()}"

        logger.info(f"Voice connect request for session: {session_id}")

        # Create Daily.co room
        daily_helper = DailyRoomHelper()
        room_url, token = await daily_helper.create_room_and_token()

        # Start bot subprocess
        bot_script = os.path.join(
            os.path.dirname(__file__),
            "pipecat_bot.py"
        )

        logger.info(f"Starting bot subprocess for room: {room_url}")

        # Run subprocess inheriting stdout/stderr so logs appear in server console,
        # and ensure unbuffered mode for timely log flushing.
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")

        process = subprocess.Popen(
            [
                sys.executable,
                "-u",  # unbuffered
                bot_script,
                "-u", room_url,
                "-t", token
            ],
            env=env,
        )

        voice_processes[session_id] = process
        logger.info(f"Bot subprocess started with PID: {process.pid}")

        # Give bot a moment to initialize
        await asyncio.sleep(2)

        # Check if process is still running
        if process.poll() is not None:
            # Process died, read error
            stderr = "See logs in sih25/logs and server console for details."
            logger.error(f"Bot process died. {stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Bot process failed to start: {stderr}"
            )

        # Return in the format Pipecat Daily transport expects
        return {
            "url": room_url,
            "token": token
        }

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice AI not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Voice connect failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def voice_disconnect(session_id: str):
    """Disconnect and cleanup voice session"""
    try:
        if session_id in voice_processes:
            process = voice_processes[session_id]
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            del voice_processes[session_id]
            logger.info(f"Voice session {session_id} disconnected")
            return {"status": "disconnected", "session_id": session_id}
        else:
            return {"status": "not_found", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error disconnecting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def voice_status():
    """Get status of voice AI service"""
    active_sessions = [
        sid for sid, proc in voice_processes.items()
        if proc.poll() is None
    ]

    return {
        "status": "operational",
        "active_sessions": len(active_sessions),
        "sessions": active_sessions,
        "daily_configured": bool(os.getenv("DAILY_API_KEY")),
        "soniox_configured": bool(os.getenv("SONIOX_API_KEY")),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "sarvam_configured": bool(os.getenv("SARVAM_API_KEY"))
    }

