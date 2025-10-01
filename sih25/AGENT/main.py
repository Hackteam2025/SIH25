#!/usr/bin/env python3
"""
FastAPI Agent Server for SIH25
This server provides the AI ocean agent with direct Supabase connection.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from sih25.AGENT.api import router as agent_router
from sih25.VOICE_AI.api import router as voice_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for agent initialization"""
    logger.info("Starting Agent Server...")

    # The Ocean Agent is initialized on-demand within the API endpoints
    logger.info("Ocean Agent will initialize on first request")

    yield

    # Cleanup
    logger.info("Shutting down Agent Server...")


# Create FastAPI application
app = FastAPI(
    title="SIH25 Agent Server",
    description="Provides AI ocean agent with direct Supabase access for oceanographic data exploration.",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for the agent server"""
    return {"status": "healthy", "service": "Agent Server"}


# Include API routers
app.include_router(agent_router)
app.include_router(voice_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_API_PORT", "8001"))
    host = os.getenv("API_HOST", "0.0.0.0")

    logger.info(f"Starting Agent Server on {host}:{port}")
    uvicorn.run(
        "sih25.AGENT.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
