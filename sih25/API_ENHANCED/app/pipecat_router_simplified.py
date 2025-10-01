"""
Simplified Pipecat Bot Router for FloatChat Voice AI
Uses Daily.co for WebRTC without full Pipecat SDK
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import logging
import httpx
import json
from datetime import datetime, timedelta
import uuid

# Import MCP server from parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_server import FloatChatMCPServer

router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration from environment
DAILY_API_KEY = os.getenv("DAILY_API_KEY")
DAILY_ROOM_URL = os.getenv("DAILY_ROOM_URL", "https://pdv.daily.co/prada")

class PipecatConnectRequest(BaseModel):
    """Request model for Pipecat connection"""
    language: str = "en"
    languageConfig: Optional[Dict[str, str]] = None
    userId: Optional[str] = None
    sessionId: Optional[str] = None

class PipecatConnectResponse(BaseModel):
    """Response model with Daily room credentials"""
    roomUrl: str
    token: str
    botId: str
    sessionId: str
    config: Dict[str, Any]

class PipecatActionRequest(BaseModel):
    """Request model for bot actions"""
    action: str
    params: Optional[Dict[str, Any]] = None
    sessionId: str

# Active sessions storage
active_sessions = {}

@router.post("/connect")
async def connect_to_pipecat(request: PipecatConnectRequest):
    """
    Create or get Daily room credentials for voice connection
    Since we're using React Pipecat client, we just need to provide room credentials
    """
    try:
        session_id = request.sessionId or str(uuid.uuid4())
        bot_id = str(uuid.uuid4())

        # For simplicity, use the existing Daily room URL from env
        # In production, you'd create a new room per session
        room_url = DAILY_ROOM_URL

        if not room_url or not DAILY_API_KEY:
            logger.error("Daily.co credentials not configured")
            raise HTTPException(
                status_code=500,
                detail="Voice service not configured. Please check Daily.co settings."
            )

        # Create a meeting token for the user
        async with httpx.AsyncClient() as client:
            # Extract room name from URL
            room_name = room_url.split('/')[-1]  # Gets 'prada' from 'https://pdv.daily.co/prada'

            token_response = await client.post(
                "https://api.daily.co/v1/meeting-tokens",
                headers={
                    "Authorization": f"Bearer {DAILY_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "room_name": room_name,
                        "user_name": f"User-{request.userId or 'anonymous'}",
                        "is_owner": False,
                        "enable_recording": False,
                        "exp": int((datetime.now() + timedelta(hours=1)).timestamp())
                    }
                }
            )

            if token_response.status_code != 200:
                logger.error(f"Failed to create meeting token: {token_response.text}")
                # Return a simplified response for testing
                return PipecatConnectResponse(
                    roomUrl=room_url,
                    token="test-token",  # This won't work for actual connection
                    botId=bot_id,
                    sessionId=session_id,
                    config={
                        "language": request.language,
                        "sttProvider": "deepgram",
                        "ttsProvider": "elevenlabs" if request.language == "en" else "sarvam",
                        "llmModel": "groq/llama-3.1-70b-versatile",
                        "warning": "Using test mode - voice features limited"
                    }
                )

            token = token_response.json()["token"]

        # Store session info
        active_sessions[session_id] = {
            "bot_id": bot_id,
            "room_url": room_url,
            "created_at": datetime.now().isoformat(),
            "language": request.language,
            "user_id": request.userId
        }

        logger.info(f"Created voice session {session_id} for language {request.language}")

        return PipecatConnectResponse(
            roomUrl=room_url,
            token=token,
            botId=bot_id,
            sessionId=session_id,
            config={
                "language": request.language,
                "sttProvider": "deepgram",
                "ttsProvider": "elevenlabs" if request.language == "en" else "sarvam",
                "llmModel": "groq/llama-3.1-70b-versatile"
            }
        )

    except httpx.RequestError as e:
        logger.error(f"Network error connecting to Daily.co: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to voice service. Please try again."
        )
    except Exception as e:
        logger.error(f"Error creating voice connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/action")
async def perform_bot_action(request: PipecatActionRequest):
    """
    Perform an action on the bot (update config, disconnect, etc.)
    """
    session = active_sessions.get(request.sessionId)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        if request.action == "updateConfig":
            # Update session configuration
            if request.params:
                session.update(request.params)
            return {"success": True, "message": "Configuration updated"}

        elif request.action == "disconnect":
            # Clean up session
            if request.sessionId in active_sessions:
                del active_sessions[request.sessionId]
            return {"success": True, "message": "Disconnected"}

        elif request.action == "getTools":
            # Return available MCP tools
            mcp_server = FloatChatMCPServer()
            tools = mcp_server.get_tool_descriptions()
            await mcp_server.close()
            return {"success": True, "tools": tools}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    except Exception as e:
        logger.error(f"Error performing action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_active_sessions():
    """Get list of active voice sessions"""
    return {
        "count": len(active_sessions),
        "sessions": [
            {
                "sessionId": sid,
                "botId": session["bot_id"],
                "createdAt": session["created_at"],
                "language": session["language"],
                "userId": session.get("user_id", "anonymous")
            }
            for sid, session in active_sessions.items()
        ]
    }

@router.get("/health")
async def health_check():
    """Check if voice service is configured and healthy"""
    configured = bool(DAILY_API_KEY and DAILY_ROOM_URL)

    # Test Daily API connection if configured
    api_healthy = False
    if configured:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.daily.co/v1/",
                    headers={"Authorization": f"Bearer {DAILY_API_KEY}"},
                    timeout=5.0
                )
                api_healthy = response.status_code == 200
        except:
            pass

    return {
        "status": "healthy" if configured and api_healthy else "degraded",
        "configured": configured,
        "api_connection": api_healthy,
        "active_sessions": len(active_sessions),
        "services": {
            "daily": configured,
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "deepgram": bool(os.getenv("DEEPGRAM_API_KEY")),
            "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
            "sarvam": bool(os.getenv("SARVAM_API_KEY"))
        }
    }

# Cleanup function for app shutdown
async def cleanup_sessions():
    """Clean up active sessions on shutdown"""
    active_sessions.clear()
    logger.info("Cleaned up all voice sessions")