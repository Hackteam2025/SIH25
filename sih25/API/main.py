#!/usr/bin/env python3
"""
FastAPI MCP Tool Server for ARGO Oceanographic Data
Provides secure, validated database access tools for AI agents
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

# Import database manager from existing LOADER
from sih25.LOADER.database import get_db_manager, close_db_manager

# Import models, tools, safety, and MCP protocol
from sih25.API.models import (
    BoundingBox, ProfileQuery, FloatSearchQuery, VariableStatsQuery,
    ToolResponse
)
from sih25.API.tools.core_tools import argo_tools
from sih25.API.tools.vector_search import vector_search_tools
from sih25.API.safety import query_safety
from sih25.API.mcp_protocol import mcp_handler

# Import metadata processing
from sih25.METADATA.processor import get_metadata_processor

# Import AI Agent API
from sih25.AGENT.api import router as agent_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for database connections"""
    logger.info("Starting MCP Tool Server...")

    # Initialize database connection
    try:
        db_manager = await get_db_manager()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down MCP Tool Server...")
    await close_db_manager()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="SIH25 MCP Tool Server",
    description="Secure MCP Tool Server for ARGO Oceanographic Data Access",
    version="1.0.0",
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
    """Health check endpoint"""
    try:
        db_manager = await get_db_manager()
        db_healthy = await db_manager.health_check()

        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "service": "MCP Tool Server",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


# MCP Protocol Endpoints
@app.get("/mcp/tools/descriptions")
async def get_tool_descriptions():
    """Get comprehensive tool descriptions for MCP clients and AI agents"""
    return {
        "tools": mcp_handler.generate_tool_descriptions(),
        "server_info": {
            "name": "ARGO Data MCP Server",
            "version": "1.0.0",
            "description": "AI tools for querying ARGO oceanographic data with scientific validation",
            "capabilities": [
                "Geographic and temporal data queries",
                "Quality control filtering",
                "Scientific unit conversion",
                "Data provenance tracking",
                "Statistical analysis",
                "Input validation and safety"
            ],
            "data_standards": "ARGO Data Management Team protocols",
            "coverage": "Global ocean, 1999-present"
        }
    }


@app.get("/mcp/status")
async def get_mcp_status():
    """Get MCP server status and capabilities"""
    try:
        db_manager = await get_db_manager()
        db_healthy = await db_manager.health_check()

        return {
            "status": "operational",
            "database_connected": db_healthy,
            "tools_available": 8,
            "last_updated": datetime.utcnow().isoformat(),
            "protocol_version": "MCP 1.0",
            "safety_features": [
                "Input validation",
                "Query size limits",
                "SQL injection prevention",
                "ARGO QC compliance"
            ]
        }
    except Exception as e:
        logger.error(f"MCP status check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "database_connected": False
        }


# MCP Tool Endpoints
@app.post("/tools/list_profiles",
          summary="List ARGO profiles in region and time range",
          description="Query ARGO profiles within geographic bounds and time window with QC filtering")
async def list_profiles_tool(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    time_start: datetime,
    time_end: datetime,
    has_bgc: bool = False,
    max_results: int = 100
) -> ToolResponse:
    """List profiles within a geographic region and time range"""

    # Safety validation
    query_params = {
        'min_lat': min_lat, 'max_lat': max_lat,
        'min_lon': min_lon, 'max_lon': max_lon,
        'time_start': time_start, 'time_end': time_end,
        'max_results': max_results
    }

    is_safe, safety_errors, safety_metadata = query_safety.validate_query_safety(
        "list_profiles", query_params
    )

    if not is_safe:
        return ToolResponse(
            success=False,
            errors=[{"error": "validation_error", "message": "; ".join(safety_errors)}],
            metadata=safety_metadata
        )

    region = BoundingBox(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon
    )

    response = await argo_tools._execute_with_timing(
        argo_tools.list_profiles,
        region, time_start, time_end, has_bgc, max_results
    )

    # Add safety metadata
    response.metadata.update(safety_metadata)
    return response


@app.post("/tools/get_profile_details",
          summary="Get detailed profile information",
          description="Retrieve comprehensive data about a specific ARGO profile")
async def get_profile_details_tool(profile_id: str) -> ToolResponse:
    """Get detailed information about a specific profile"""

    # Safety validation
    query_params = {'profile_id': profile_id}
    is_safe, safety_errors, safety_metadata = query_safety.validate_query_safety(
        "get_profile_details", query_params
    )

    if not is_safe:
        return ToolResponse(
            success=False,
            errors=[{"error": "validation_error", "message": "; ".join(safety_errors)}],
            metadata=safety_metadata
        )

    response = await argo_tools._execute_with_timing(
        argo_tools.get_profile_details,
        profile_id
    )

    # Add safety metadata
    response.metadata.update(safety_metadata)
    return response


@app.post("/tools/search_floats_near",
          summary="Find floats near a location",
          description="Search for ARGO floats within specified radius of coordinates")
async def search_floats_near_tool(
    lon: float,
    lat: float,
    radius_km: float,
    max_results: int = 50
) -> ToolResponse:
    """Search for floats within a specified radius of a point"""

    # Safety validation
    query_params = {
        'lat': lat, 'lon': lon,
        'radius_km': radius_km, 'max_results': max_results
    }
    is_safe, safety_errors, safety_metadata = query_safety.validate_query_safety(
        "search_floats_near", query_params
    )

    if not is_safe:
        return ToolResponse(
            success=False,
            errors=[{"error": "validation_error", "message": "; ".join(safety_errors)}],
            metadata=safety_metadata
        )

    response = await argo_tools._execute_with_timing(
        argo_tools.search_floats_near,
        lon, lat, radius_km, max_results
    )

    # Add safety metadata
    response.metadata.update(safety_metadata)
    return response


@app.post("/tools/get_profile_statistics",
          summary="Get variable statistics for profile",
          description="Calculate statistical summary of oceanographic variable in profile")
async def get_profile_statistics_tool(
    profile_id: str,
    variable: str
) -> ToolResponse:
    """Get statistical summary of a variable in a profile"""

    # Safety validation
    query_params = {'profile_id': profile_id, 'variable': variable}
    is_safe, safety_errors, safety_metadata = query_safety.validate_query_safety(
        "get_profile_statistics", query_params
    )

    if not is_safe:
        return ToolResponse(
            success=False,
            errors=[{"error": "validation_error", "message": "; ".join(safety_errors)}],
            metadata=safety_metadata
        )

    response = await argo_tools._execute_with_timing(
        argo_tools.get_profile_statistics,
        profile_id, variable
    )

    # Add safety metadata
    response.metadata.update(safety_metadata)
    return response


# Vector Search Tool Endpoints
@app.post("/tools/semantic_search",
          summary="Semantic search for ARGO profiles",
          description="Natural language search through ARGO profile metadata using vector embeddings")
async def semantic_search_tool(
    query: str,
    limit: int = 10,
    region_filter: Optional[str] = None,
    similarity_threshold: float = 0.5
) -> ToolResponse:
    """Perform semantic search on profile metadata"""
    return await vector_search_tools.semantic_search_profiles(
        query=query,
        limit=limit,
        region_filter=region_filter,
        similarity_threshold=similarity_threshold
    )


@app.post("/tools/find_similar_profiles",
          summary="Find profiles similar to a reference profile",
          description="Discover profiles with similar characteristics to a given profile")
async def find_similar_profiles_tool(
    profile_id: str,
    similarity_threshold: float = 0.7,
    limit: int = 10
) -> ToolResponse:
    """Find profiles similar to a given profile"""
    return await vector_search_tools.find_similar_profiles(
        profile_id=profile_id,
        similarity_threshold=similarity_threshold,
        limit=limit
    )


@app.post("/tools/search_by_description",
          summary="Search profiles by natural language description",
          description="Find profiles using detailed natural language descriptions with filters")
async def search_by_description_tool(
    description: str,
    region: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 10
) -> ToolResponse:
    """Search profiles by comprehensive description"""
    return await vector_search_tools.search_by_description(
        description=description,
        region=region,
        season=season,
        limit=limit
    )


@app.post("/tools/hybrid_search",
          summary="Hybrid vector and structured search",
          description="Combine semantic search with geographic and temporal filters")
async def hybrid_search_tool(
    query: str,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    parameters: Optional[List[str]] = None,
    limit: int = 10,
    vector_weight: float = 0.7
) -> ToolResponse:
    """Perform hybrid semantic and structured search"""
    lat_range = (min_lat, max_lat) if min_lat is not None and max_lat is not None else None
    lon_range = (min_lon, max_lon) if min_lon is not None and max_lon is not None else None

    return await vector_search_tools.hybrid_search(
        query=query,
        lat_range=lat_range,
        lon_range=lon_range,
        parameters=parameters,
        limit=limit,
        vector_weight=vector_weight
    )


# Metadata Processing Endpoints
@app.post("/metadata/upload",
          summary="Upload and process metadata files",
          description="Upload metadata files for vector database processing")
async def upload_metadata_file(file_path: str, filename: str):
    """Process uploaded metadata file"""
    processor = get_metadata_processor()
    result = await processor.process_uploaded_file(file_path, filename)

    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "processed_count": result["processed_count"],
            "file_info": result["file_info"]
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Processing failed: {result['error']}"
        )


@app.post("/metadata/create_sample",
          summary="Create sample metadata for testing",
          description="Generate sample metadata entries for demonstration")
async def create_sample_metadata():
    """Create sample metadata for testing"""
    processor = get_metadata_processor()
    sample_profiles = await processor.create_sample_metadata()

    # Store in vector database
    from sih25.METADATA.vector_store import get_vector_store
    vector_store = await get_vector_store()
    success = await vector_store.add_profiles(sample_profiles)

    if success:
        return {
            "success": True,
            "message": f"Created {len(sample_profiles)} sample metadata entries",
            "profiles_created": len(sample_profiles)
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to create sample metadata"
        )


@app.get("/metadata/stats",
        summary="Get metadata processing statistics",
        description="Retrieve statistics about the vector database")
async def get_metadata_stats():
    """Get processing and vector store statistics"""
    processor = get_metadata_processor()
    stats = await processor.get_processing_stats()
    return stats


@app.post("/admin/reset_vector_db",
          summary="Reset vector database",
          description="Clear all vector embeddings and reset the ChromaDB collection")
async def reset_vector_database():
    """Reset the vector database"""
    try:
        from sih25.METADATA.vector_store import get_vector_store
        vector_store = await get_vector_store()
        success = await vector_store.reset_collection()

        if success:
            return {
                "success": True,
                "message": "Vector database reset successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reset vector database"
            )
    except Exception as e:
        logger.error(f"Vector database reset failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reset failed: {str(e)}"
        )


# Create MCP server instance
mcp = FastApiMCP(
    app,
    name="ARGO Data MCP Server",
    description="AI tools for querying ARGO oceanographic data with scientific validation"
)

# Mount MCP server
mcp.mount_http()

# Include Agent API router
app.include_router(agent_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "sih25.API.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )