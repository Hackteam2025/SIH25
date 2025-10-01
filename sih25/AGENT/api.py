"""
Agent API Module

FastAPI endpoints for the FloatChat Agent.
Provides natural conversational interface to oceanographic data.

This uses FloatChatAgent which properly orchestrates tool calls
BEFORE the LLM generates responses, preventing hallucination.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from sih25.AGENT.float_chat_agent import FloatChatAgent, AgentResponse

logger = logging.getLogger(__name__)

# Global FloatChat agent instance
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
router = APIRouter(prefix="/agent", tags=["FloatChat Agent"])


async def get_agent_instance() -> FloatChatAgent:
    """Dependency to get initialized FloatChat Agent instance."""
    global agent
    if agent is None:
        try:
            agent = FloatChatAgent()
            success = await agent.initialize()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to initialize FloatChat Agent")
            logger.info("FloatChat Agent online and ready")
        except Exception as e:
            logger.error(f"Failed to initialize FloatChat Agent: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize agent: {str(e)}")
    return agent


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    agent_instance: FloatChatAgent = Depends(get_agent_instance)
) -> ChatResponse:
    """
    Chat with the FloatChat Agent about oceanographic data.

    This agent properly orchestrates tool calls BEFORE generating responses,
    ensuring all data is fetched from the database (no hallucination).

    Args:
        request: Chat request with message and optional session context

    Returns:
        Agent response with conversation and real data
    """
    try:
        # Process the query with FloatChat Agent
        agent_response: AgentResponse = await agent_instance.process_query(
            user_message=request.message,
            session_id=request.session_id,
            context=request.context or {}
        )

        # Convert to API response format
        return ChatResponse(
            success=agent_response.success,
            response=agent_response.response_text,
            session_id=agent_response.metadata.get("session_id", "default"),
            tool_calls=[tc["tool_name"] for tc in agent_response.tool_calls_made],
            visualization_data=agent_response.data_for_visualization,
            scientific_insights=agent_response.scientific_insights,
            follow_up_suggestions=agent_response.follow_up_suggestions,
            metadata=agent_response.metadata
        )

    except Exception as e:
        logger.error(f"FloatChat Agent chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health() -> Dict[str, str]:
    """Health check for FloatChat Agent service."""
    global agent
    if agent is None:
        return {"status": "offline", "agent": "FloatChat Agent"}
    return {"status": "online", "agent": "FloatChat Agent", "message": "Ready to assist with ocean data queries"}


@router.post("/initialize")
async def initialize_agent() -> Dict[str, str]:
    """Initialize or reinitialize FloatChat Agent."""
    global agent
    try:
        agent = FloatChatAgent()
        success = await agent.initialize()
        if success:
            return {"status": "initialized", "agent": "FloatChat Agent", "message": "Systems online. Ready for oceanographic queries."}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize FloatChat Agent")
    except Exception as e:
        logger.error(f"FloatChat Agent initialization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
