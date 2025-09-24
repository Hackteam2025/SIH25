"""
Agent API Module

FastAPI endpoints for the JARVIS Ocean Agent.
Provides natural conversational interface to oceanographic data.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from sih25.AGENT.jarvis_ocean_agent import JarvisOceanAgent, JarvisResponse

logger = logging.getLogger(__name__)

# Global JARVIS agent instance
agent: Optional[JarvisOceanAgent] = None

# API Models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    success: bool
    response: str
    session_id: str
    tool_calls: list = []
    visualization_data: Optional[Dict[str, Any]] = None
    scientific_insights: list = []
    follow_up_suggestions: list = []
    metadata: Dict[str, Any] = {}


# Router
router = APIRouter(prefix="/agent", tags=["JARVIS Ocean Agent"])


async def get_agent() -> JarvisOceanAgent:
    """Dependency to get initialized JARVIS agent instance."""
    global agent
    if agent is None:
        agent = JarvisOceanAgent()
        if not await agent.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize JARVIS")
        logger.info("JARVIS Ocean Agent online")
    return agent


@router.post("/chat", response_model=ChatResponse)
async def chat_with_jarvis(
    request: ChatRequest,
    agent_instance: JarvisOceanAgent = Depends(get_agent)
) -> ChatResponse:
    """
    Chat with JARVIS about oceanographic data.

    Args:
        request: Chat request with message and optional session context

    Returns:
        JARVIS response with conversation and data insights
    """
    try:
        # Process the query with JARVIS
        jarvis_response = await agent_instance.process_query(
            message=request.message,
            session_id=request.session_id,
            voice_input=request.context.get("voice_input", False) if request.context else False,
            context=request.context
        )

        # Convert to API response format
        return ChatResponse(
            success=True,
            response=jarvis_response.response_text,
            session_id=request.session_id or "jarvis_default",
            tool_calls=jarvis_response.tools_used,
            visualization_data=jarvis_response.data_retrieved,
            scientific_insights=[],
            follow_up_suggestions=jarvis_response.proactive_suggestions,
            metadata={
                "voice_compatible": jarvis_response.voice_compatible,
                "visualization_needed": jarvis_response.visualization_needed,
                "personality": "JARVIS Ocean Agent"
            }
        )

    except Exception as e:
        logger.error(f"JARVIS chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    agent_instance: JarvisOceanAgent = Depends(get_agent)
) -> Dict[str, Any]:
    """
    Get summary of a JARVIS conversation session.

    Args:
        session_id: Session identifier

    Returns:
        Session summary with conversation history
    """
    try:
        summary = agent_instance.get_session_summary(session_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Session not found in JARVIS memory")
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JARVIS session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def jarvis_health() -> Dict[str, str]:
    """Health check for JARVIS Ocean Agent service."""
    global agent
    if agent is None:
        return {"status": "offline", "agent": "JARVIS"}
    return {"status": "online", "agent": "JARVIS Ocean Agent", "personality": "Ready to assist"}


@router.post("/initialize")
async def initialize_jarvis() -> Dict[str, str]:
    """Initialize or reinitialize JARVIS Ocean Agent."""
    global agent
    try:
        agent = JarvisOceanAgent()
        success = await agent.initialize()
        if success:
            return {"status": "initialized", "agent": "JARVIS Ocean Agent", "message": "Systems online. How may I assist you?"}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize JARVIS systems")
    except Exception as e:
        logger.error(f"JARVIS initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))