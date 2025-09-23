"""
Agent API Module

FastAPI endpoints for the AGNO-based FloatChatAgent.
Provides conversational interface to oceanographic data.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from sih25.AGENT.float_chat_agent import FloatChatAgent, AgentResponse

logger = logging.getLogger(__name__)

# Global agent instance
agent: Optional[FloatChatAgent] = None

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
router = APIRouter(prefix="/agent", tags=["AI Agent"])


async def get_agent() -> FloatChatAgent:
    """Dependency to get initialized agent instance."""
    global agent
    if agent is None:
        agent = FloatChatAgent()
        await agent.initialize()
    return agent


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    agent_instance: FloatChatAgent = Depends(get_agent)
) -> ChatResponse:
    """
    Chat with the FloatChatAgent about oceanographic data.

    Args:
        request: Chat request with message and optional session context

    Returns:
        Agent response with conversation and data insights
    """
    try:
        # Process the query
        agent_response = await agent_instance.process_query(
            user_message=request.message,
            session_id=request.session_id,
            context=request.context
        )

        # Convert to API response format
        return ChatResponse(
            success=agent_response.success,
            response=agent_response.response_text,
            session_id=agent_response.metadata.get("session_id", "unknown"),
            tool_calls=agent_response.tool_calls_made,
            visualization_data=agent_response.data_for_visualization,
            scientific_insights=agent_response.scientific_insights,
            follow_up_suggestions=agent_response.follow_up_suggestions,
            metadata=agent_response.metadata
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    agent_instance: FloatChatAgent = Depends(get_agent)
) -> Dict[str, Any]:
    """
    Get summary of a conversation session.

    Args:
        session_id: Session identifier

    Returns:
        Session summary with conversation metrics
    """
    try:
        summary = await agent_instance.get_session_summary(session_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health() -> Dict[str, str]:
    """Health check for the agent service."""
    global agent
    if agent is None:
        return {"status": "not_initialized"}
    return {"status": "healthy"}


@router.post("/initialize")
async def initialize_agent() -> Dict[str, str]:
    """Initialize or reinitialize the agent."""
    global agent
    try:
        agent = FloatChatAgent()
        success = await agent.initialize()
        if success:
            return {"status": "initialized"}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize agent")
    except Exception as e:
        logger.error(f"Agent initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))