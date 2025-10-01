"""
ChromaDB Vector Store Management
Handles embeddings generation and storage for semantic search
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import hashlib

import chromadb
from chromadb.config import Settings
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProfileSummary(BaseModel):
    """Profile summary for embedding generation"""
    profile_id: str
    float_id: str
    timestamp: str
    latitude: float
    longitude: float
    depth_range: str
    parameters: List[str]
    qc_summary: str
    season_info: str
    region_info: str
    data_quality: str


class VectorStore:
    """ChromaDB-based vector store for ARGO metadata"""

    def __init__(self, persist_directory: str = "sih25_vector_db"):
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None

        # Mistral API configuration
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        if not self.mistral_api_key:
            logger.warning("MISTRAL_API_KEY not found, falling back to sentence-transformers")
            self.use_mistral = False
        else:
            self.use_mistral = True

        self.mistral_url = "https://api.mistral.ai/v1/embeddings"

        # Fallback embedding model
        self._sentence_transformer = None

    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create persistent ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection for ARGO profiles
            self.collection = self.client.get_or_create_collection(
                name="argo_profiles",
                metadata={"description": "ARGO profile metadata and summaries"}
            )

            logger.info(f"ChromaDB initialized with {self.collection.count()} embeddings")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def _get_sentence_transformer(self):
        """Lazy load sentence transformer as fallback"""
        if self._sentence_transformer is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                logger.error("sentence-transformers not available")
                raise
        return self._sentence_transformer

    async def _get_mistral_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Mistral API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.mistral_url,
                    headers={
                        "Authorization": f"Bearer {self.mistral_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mistral-embed",
                        "input": texts
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return [item["embedding"] for item in result["data"]]
                else:
                    logger.error(f"Mistral API error: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Mistral embedding failed: {e}")
            return None

    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using Mistral API or fallback"""
        if self.use_mistral:
            embeddings = await self._get_mistral_embeddings(texts)
            if embeddings:
                return embeddings

        # Fallback to sentence transformers
        logger.info("Using sentence-transformers fallback")
        model = self._get_sentence_transformer()
        return model.encode(texts).tolist()

    def _create_profile_summary(self, profile_data: Dict[str, Any]) -> str:
        """Create comprehensive profile summary for embedding"""
        # Extract key information
        float_id = profile_data.get('float_id', 'unknown')
        timestamp = profile_data.get('timestamp', 'unknown')
        lat = profile_data.get('latitude', 0.0)
        lon = profile_data.get('longitude', 0.0)

        # Determine season and region
        month = datetime.fromisoformat(timestamp.replace('Z', '')).month if timestamp != 'unknown' else 1
        seasons = {1: "Winter", 4: "Spring", 7: "Summer", 10: "Autumn"}
        season = seasons.get(((month-1)//3)*3 + 1, "Unknown")

        # Determine ocean region (simplified)
        if -30 <= lat <= 30:
            region = "Tropical"
        elif lat > 60 or lat < -60:
            region = "Polar"
        else:
            region = "Temperate"

        # Build comprehensive summary
        summary = f"""
        ARGO Float {float_id} oceanographic profile from {timestamp}
        Location: {lat:.2f}°N, {lon:.2f}°E in the {region} ocean region
        Measurement depth range: {profile_data.get('min_depth', 0)}m to {profile_data.get('max_depth', 2000)}m
        Available parameters: {', '.join(profile_data.get('parameters', ['temperature', 'salinity']))}
        Data quality: {profile_data.get('qc_summary', 'good quality measurements')}
        Seasonal context: {season} season measurements
        Scientific significance: Ocean temperature and salinity profiles for climate research
        Regional characteristics: {region} ocean conditions with typical seasonal variations
        """

        return summary.strip()

    async def add_profiles(self, profiles: List[Dict[str, Any]]) -> bool:
        """Add profile embeddings to vector store"""
        if not self.collection:
            await self.initialize()

        try:
            # Create summaries and generate embeddings
            summaries = [self._create_profile_summary(profile) for profile in profiles]
            embeddings = await self._get_embeddings(summaries)

            # Prepare data for ChromaDB
            ids = []
            metadatas = []
            documents = []

            for i, profile in enumerate(profiles):
                profile_id = profile.get('profile_id', f"profile_{i}")
                ids.append(profile_id)

                # Metadata for filtering
                metadatas.append({
                    "profile_id": profile_id,
                    "float_id": profile.get('float_id', 'unknown'),
                    "timestamp": profile.get('timestamp', ''),
                    "latitude": float(profile.get('latitude', 0.0)),
                    "longitude": float(profile.get('longitude', 0.0)),
                    "region": profile.get('region', 'unknown'),
                    "season": profile.get('season', 'unknown'),
                    "parameters": json.dumps(profile.get('parameters', [])),
                    "added_at": datetime.now().isoformat()
                })

                documents.append(summaries[i])

            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(profiles)} profiles to vector store")
            return True

        except Exception as e:
            logger.error(f"Failed to add profiles to vector store: {e}")
            return False

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        where_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search with optional metadata filtering"""
        if not self.collection:
            await self.initialize()

        try:
            # Get query embedding
            query_embeddings = await self._get_embeddings([query])

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=limit,
                where=where_filters
            )

            # Format results
            matches = []
            for i in range(len(results['ids'][0])):
                matches.append({
                    "profile_id": results['ids'][0][i],
                    "similarity": 1 - results['distances'][0][i],  # Convert distance to similarity
                    "metadata": results['metadatas'][0][i],
                    "summary": results['documents'][0][i]
                })

            return matches

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def find_similar_profiles(
        self,
        profile_id: str,
        similarity_threshold: float = 0.7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find profiles similar to a given profile"""
        if not self.collection:
            await self.initialize()

        try:
            # Get the target profile's embedding
            result = self.collection.get(ids=[profile_id])
            if not result['documents']:
                return []

            # Use the profile's document text for similarity search
            return await self.semantic_search(
                query=result['documents'][0],
                limit=limit + 1  # +1 to exclude the original profile
            )

        except Exception as e:
            logger.error(f"Similar profile search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.collection:
            return {"status": "not_initialized"}

        try:
            count = self.collection.count()
            return {
                "status": "active",
                "total_embeddings": count,
                "collection_name": "argo_profiles",
                "embedding_model": "mistral-embed" if self.use_mistral else "sentence-transformers",
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def reset_collection(self) -> bool:
        """Reset the vector store collection"""
        try:
            if self.collection:
                self.client.delete_collection("argo_profiles")
                self.collection = self.client.create_collection(
                    name="argo_profiles",
                    metadata={"description": "ARGO profile metadata and summaries"}
                )
            logger.info("Vector store collection reset")
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False


# Global vector store instance
_vector_store = None


async def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        await _vector_store.initialize()
    return _vector_store