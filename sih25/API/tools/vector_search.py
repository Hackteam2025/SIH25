"""
Vector Search Tools for MCP Integration
Provides semantic search capabilities for the ARGO AI agent
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from pydantic import BaseModel, Field

from sih25.DATAOPS.METADATA.vector_store import get_vector_store
from sih25.API.models import ToolResponse

logger = logging.getLogger(__name__)


class VectorSearchQuery(BaseModel):
    """Vector search query parameters"""
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(10, description="Maximum number of results")
    similarity_threshold: float = Field(0.5, description="Minimum similarity score")
    region_filter: Optional[str] = Field(None, description="Filter by ocean region")
    time_filter: Optional[str] = Field(None, description="Filter by time period")


class ProfileMatch(BaseModel):
    """Vector search result"""
    profile_id: str
    similarity_score: float
    metadata: Dict[str, Any]
    summary: str
    match_reason: str


class VectorSearchTools:
    """Vector search tools for AI agent"""

    def __init__(self):
        self.vector_store = None

    async def _ensure_vector_store(self):
        """Ensure vector store is initialized"""
        if self.vector_store is None:
            self.vector_store = await get_vector_store()

    async def semantic_search_profiles(
        self,
        query: str,
        limit: int = 10,
        region_filter: Optional[str] = None,
        similarity_threshold: float = 0.5
    ) -> ToolResponse:
        """
        Perform semantic search on ARGO profile metadata

        Args:
            query: Natural language description (e.g., "warm water profiles in tropical regions")
            limit: Maximum number of results to return
            region_filter: Optional filter by region (tropical, temperate, polar)
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            ToolResponse with matching profiles and similarity scores
        """
        try:
            await self._ensure_vector_store()

            # Build ChromaDB where filters
            where_filters = {}
            if region_filter:
                where_filters["region"] = region_filter.lower()

            # Perform semantic search
            matches = await self.vector_store.semantic_search(
                query=query,
                limit=limit,
                where_filters=where_filters if where_filters else None
            )

            # Filter by similarity threshold
            filtered_matches = [
                match for match in matches
                if match["similarity"] >= similarity_threshold
            ]

            # Format results for AI agent
            results = []
            for match in filtered_matches:
                profile_data = {
                    "profile_id": match["profile_id"],
                    "similarity_score": round(match["similarity"], 3),
                    "float_id": match["metadata"].get("float_id", "unknown"),
                    "location": {
                        "latitude": match["metadata"].get("latitude", 0.0),
                        "longitude": match["metadata"].get("longitude", 0.0)
                    },
                    "timestamp": match["metadata"].get("timestamp", ""),
                    "region": match["metadata"].get("region", "unknown"),
                    "parameters": __import__('json').loads(match["metadata"].get("parameters", "[]")),
                    "summary": match["summary"][:200] + "..." if len(match["summary"]) > 200 else match["summary"],
                    "match_reason": f"Semantic similarity: {match['similarity']:.1%}"
                }
                results.append(profile_data)

            return ToolResponse(
                success=True,
                data={
                    "query": query,
                    "total_matches": len(results),
                    "search_type": "semantic",
                    "profiles": results
                },
                metadata={
                    "tool": "semantic_search_profiles",
                    "search_time": datetime.now().isoformat(),
                    "filters_applied": where_filters,
                    "similarity_threshold": similarity_threshold
                }
            )

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return ToolResponse(
                success=False,
                errors=[{"error": "search_failed", "message": str(e)}],
                metadata={"tool": "semantic_search_profiles"}
            )

    async def find_similar_profiles(
        self,
        profile_id: str,
        similarity_threshold: float = 0.7,
        limit: int = 10
    ) -> ToolResponse:
        """
        Find profiles similar to a given profile

        Args:
            profile_id: ID of the reference profile
            similarity_threshold: Minimum similarity score
            limit: Maximum number of similar profiles to return

        Returns:
            ToolResponse with similar profiles
        """
        try:
            await self._ensure_vector_store()

            # Find similar profiles
            matches = await self.vector_store.find_similar_profiles(
                profile_id=profile_id,
                similarity_threshold=similarity_threshold,
                limit=limit
            )

            # Format results (exclude the original profile)
            results = []
            for match in matches:
                if match["profile_id"] != profile_id:
                    profile_data = {
                        "profile_id": match["profile_id"],
                        "similarity_score": round(match["similarity"], 3),
                        "float_id": match["metadata"].get("float_id", "unknown"),
                        "location": {
                            "latitude": match["metadata"].get("latitude", 0.0),
                            "longitude": match["metadata"].get("longitude", 0.0)
                        },
                        "timestamp": match["metadata"].get("timestamp", ""),
                        "region": match["metadata"].get("region", "unknown"),
                        "match_reason": f"Profile similarity: {match['similarity']:.1%}"
                    }
                    results.append(profile_data)

            return ToolResponse(
                success=True,
                data={
                    "reference_profile": profile_id,
                    "total_similar": len(results),
                    "search_type": "similarity",
                    "similar_profiles": results
                },
                metadata={
                    "tool": "find_similar_profiles",
                    "search_time": datetime.now().isoformat(),
                    "similarity_threshold": similarity_threshold
                }
            )

        except Exception as e:
            logger.error(f"Similar profile search failed: {e}")
            return ToolResponse(
                success=False,
                errors=[{"error": "similarity_search_failed", "message": str(e)}],
                metadata={"tool": "find_similar_profiles"}
            )

    async def search_by_description(
        self,
        description: str,
        region: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 10
    ) -> ToolResponse:
        """
        Search profiles by natural language description with optional filters

        Args:
            description: Natural language description of desired profiles
            region: Optional region filter (tropical, temperate, polar)
            season: Optional season filter (winter, spring, summer, autumn)
            limit: Maximum number of results

        Returns:
            ToolResponse with matching profiles
        """
        try:
            await self._ensure_vector_store()

            # Build comprehensive search query
            enhanced_query = description
            if region:
                enhanced_query += f" in {region} region"
            if season:
                enhanced_query += f" during {season}"

            # Build metadata filters
            where_filters = {}
            if region:
                where_filters["region"] = region.lower()
            if season:
                where_filters["season"] = season.lower()

            # Perform search
            matches = await self.vector_store.semantic_search(
                query=enhanced_query,
                limit=limit,
                where_filters=where_filters if where_filters else None
            )

            # Format results with enhanced context
            results = []
            for match in matches:
                metadata = match["metadata"]
                profile_data = {
                    "profile_id": match["profile_id"],
                    "similarity_score": round(match["similarity"], 3),
                    "float_id": metadata.get("float_id", "unknown"),
                    "location": {
                        "latitude": metadata.get("latitude", 0.0),
                        "longitude": metadata.get("longitude", 0.0)
                    },
                    "timestamp": metadata.get("timestamp", ""),
                    "region": metadata.get("region", "unknown"),
                    "season": metadata.get("season", "unknown"),
                    "summary": match["summary"][:150] + "..." if len(match["summary"]) > 150 else match["summary"],
                    "context_match": {
                        "description_relevance": match["similarity"],
                        "region_match": region.lower() == metadata.get("region", "").lower() if region else None,
                        "season_match": season == metadata.get("season") if season else None
                    }
                }
                results.append(profile_data)

            return ToolResponse(
                success=True,
                data={
                    "description": description,
                    "enhanced_query": enhanced_query,
                    "total_matches": len(results),
                    "search_type": "description_based",
                    "profiles": results
                },
                metadata={
                    "tool": "search_by_description",
                    "search_time": datetime.now().isoformat(),
                    "filters": {"region": region, "season": season}
                }
            )

        except Exception as e:
            logger.error(f"Description-based search failed: {e}")
            return ToolResponse(
                success=False,
                errors=[{"error": "description_search_failed", "message": str(e)}],
                metadata={"tool": "search_by_description"}
            )

    async def hybrid_search(
        self,
        query: str,
        lat_range: Optional[tuple] = None,
        lon_range: Optional[tuple] = None,
        time_range: Optional[tuple] = None,
        parameters: Optional[List[str]] = None,
        limit: int = 10,
        vector_weight: float = 0.7
    ) -> ToolResponse:
        """
        Perform hybrid search combining vector similarity and structured filters

        Args:
            query: Natural language query
            lat_range: (min_lat, max_lat) tuple for geographic filtering
            lon_range: (min_lon, max_lon) tuple for geographic filtering
            time_range: (start_time, end_time) tuple for temporal filtering
            parameters: List of required parameters
            limit: Maximum results
            vector_weight: Weight for vector similarity (0.0-1.0)

        Returns:
            ToolResponse with hybrid search results
        """
        try:
            await self._ensure_vector_store()
            # Get semantic matches first
            semantic_matches = await self.vector_store.semantic_search(
                query=query,
                limit=limit * 2  # Get more candidates for filtering
            )

            # Apply structured filters
            filtered_results = []
            for match in semantic_matches:
                metadata = match["metadata"]

                # Apply geographic filters
                if lat_range:
                    lat = metadata.get("latitude", 0.0)
                    if not (lat_range[0] <= lat <= lat_range[1]):
                        continue

                if lon_range:
                    lon = metadata.get("longitude", 0.0)
                    if not (lon_range[0] <= lon <= lon_range[1]):
                        continue

                # Apply parameter filter
                if parameters:
                    profile_params = json.loads(metadata.get("parameters", "[]"))
                    if not all(param in profile_params for param in parameters):
                        continue

                # Calculate hybrid score
                semantic_score = match["similarity"]

                # Add structured relevance bonuses
                structured_score = 0.0
                if lat_range or lon_range:
                    # Geographic relevance bonus
                    structured_score += 0.1
                if parameters:
                    # Parameter match bonus
                    structured_score += 0.1

                # Combine scores
                hybrid_score = (vector_weight * semantic_score +
                              (1 - vector_weight) * structured_score)

                match["hybrid_score"] = hybrid_score
                filtered_results.append(match)

            # Sort by hybrid score and limit results
            filtered_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
            final_results = filtered_results[:limit]

            # Format for response
            results = []
            for match in final_results:
                metadata = match["metadata"]
                profile_data = {
                    "profile_id": match["profile_id"],
                    "hybrid_score": round(match["hybrid_score"], 3),
                    "semantic_score": round(match["similarity"], 3),
                    "float_id": metadata.get("float_id", "unknown"),
                    "location": {
                        "latitude": metadata.get("latitude", 0.0),
                        "longitude": metadata.get("longitude", 0.0)
                    },
                    "parameters": json.loads(metadata.get("parameters", "[]")),
                    "region": metadata.get("region", "unknown"),
                    "summary": match["summary"][:120] + "..." if len(match["summary"]) > 120 else match["summary"]}
                results.append(profile_data)

            return ToolResponse(
                success=True,
                data={
                    "query": query,
                    "search_type": "hybrid",
                    "total_matches": len(results),
                    "vector_weight": vector_weight,
                    "profiles": results
                },
                metadata={
                    "tool": "hybrid_search",
                    "search_time": datetime.now().isoformat(),
                    "filters": {
                        "lat_range": lat_range,
                        "lon_range": lon_range,
                        "time_range": time_range,
                        "parameters": parameters
                    }
                }
            )

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return ToolResponse(
                success=False,
                errors=[{"error": "hybrid_search_failed", "message": str(e)}],
                metadata={"tool": "hybrid_search"}
            )

    async def get_vector_store_stats(self) -> ToolResponse:
        """Get vector store statistics and health"""
        try:
            await self._ensure_vector_store()
            stats = await self.vector_store.get_stats()

            return ToolResponse(
                success=True,
                data=stats,
                metadata={
                    "tool": "get_vector_store_stats",
                    "retrieved_at": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return ToolResponse(
                success=False,
                errors=[{"error": "stats_failed", "message": str(e)}],
                metadata={"tool": "get_vector_store_stats"}
            )


# Global vector search tools instance
vector_search_tools = VectorSearchTools()