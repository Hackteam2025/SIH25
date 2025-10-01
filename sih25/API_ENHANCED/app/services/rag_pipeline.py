"""
RAG (Retrieval-Augmented Generation) Pipeline for ARGO Data
Integrates vector database, LLM, and SQL query generation
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import numpy as np
from dataclasses import dataclass

# Vector database imports
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False
    logging.warning("Vector database dependencies not available. Install with: pip install faiss-cpu sentence-transformers")

# LLM imports
try:
    from openai import OpenAI
    from langchain.llms import OpenAI as LangChainOpenAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("LLM dependencies not available. Install with: pip install openai langchain")

from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.profile import Profile, DataSummary
from ..database import get_db

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Result from RAG query processing"""
    sql_query: str
    natural_language_response: str
    data_results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    confidence_score: float

class VectorDatabase:
    """FAISS-based vector database for metadata and summaries"""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        if not VECTOR_DB_AVAILABLE:
            raise ImportError("Vector database dependencies not available")
        
        self.embedding_model = SentenceTransformer(embedding_model)
        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.metadata_store = []  # Store metadata for each vector
        
    def add_documents(self, texts: List[str], metadata: List[Dict[str, Any]]):
        """Add documents to vector database"""
        # Generate embeddings
        embeddings = self.embedding_model.encode(texts)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        self.index.add(embeddings.astype(np.float32))
        
        # Store metadata
        self.metadata_store.extend(metadata)
        
        logger.info(f"Added {len(texts)} documents to vector database")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar documents"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        # Return results with metadata
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.metadata_store):
                results.append((self.metadata_store[idx], float(score)))
        
        return results
    
    def save_index(self, filepath: str):
        """Save FAISS index to disk"""
        faiss.write_index(self.index, filepath)
        
        # Save metadata separately
        metadata_path = filepath.replace('.faiss', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata_store, f, default=str)
    
    def load_index(self, filepath: str):
        """Load FAISS index from disk"""
        self.index = faiss.read_index(filepath)
        
        # Load metadata
        metadata_path = filepath.replace('.faiss', '_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                self.metadata_store = json.load(f)

class SQLQueryGenerator:
    """Generate SQL queries from natural language using LLM"""
    
    def __init__(self, llm_model: str = None):
        if not LLM_AVAILABLE:
            raise ImportError("LLM dependencies not available")

        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("OPENAI_BASE_URL")

        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = OpenAI(
            api_key=openai_api_key,
            base_url=openai_base_url
        )
        self.model = llm_model or os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        
        # Database schema information
        self.schema_info = self._get_schema_info()
        
    def _get_schema_info(self) -> str:
        """Get database schema information for context"""
        return """
        Database Schema for ARGO Float Data:
        
        Table: profiles
        - id: Integer (Primary Key)
        - float_id: String (ARGO float identifier)
        - latitude: Float (-90 to 90)
        - longitude: Float (-180 to 180)
        - depth: Float (meters, positive values)
        - temperature: Float (Celsius)
        - salinity: Float (PSU - Practical Salinity Units)
        - pressure: Float (dbar)
        - month: Integer (1-12)
        - year: Integer
        - date: Date
        - cycle_number: Integer
        - oxygen: Float (μmol/kg, for BGC floats)
        - nitrate: Float (μmol/kg, for BGC floats)
        - ph: Float (for BGC floats)
        - chlorophyll: Float (mg/m³, for BGC floats)
        - temperature_qc: Integer (Quality control flag)
        - salinity_qc: Integer (Quality control flag)
        - data_mode: String ('R'=real-time, 'D'=delayed-mode)
        - institution: String
        - project_name: String
        
        Geographic Regions:
        - Equator: latitude between -5 and 5
        - Tropics: latitude between -23.5 and 23.5
        - Arctic: latitude > 66.5
        - Antarctic: latitude < -66.5
        - North Atlantic: latitude > 0, longitude between -80 and 0
        - South Atlantic: latitude < 0, longitude between -70 and 20
        - Pacific: longitude between -180 and -70 OR longitude between 120 and 180
        - Indian Ocean: latitude between -60 and 30, longitude between 20 and 120
        """
    
    def generate_sql_query(self, natural_language_query: str, context: List[Dict[str, Any]] = None) -> str:
        """Generate SQL query from natural language"""
        
        # Build context from retrieved documents
        context_text = ""
        if context:
            context_text = "\n\nRelevant Context:\n"
            for item in context[:3]:  # Use top 3 context items
                context_text += f"- {item.get('summary', '')}\n"
        
        prompt = f"""
        You are an expert SQL query generator for oceanographic ARGO float data.
        
        {self.schema_info}
        
        {context_text}
        
        Convert this natural language query to SQL:
        "{natural_language_query}"
        
        Guidelines:
        1. Use only the tables and columns defined in the schema
        2. For geographic queries, use appropriate latitude/longitude ranges
        3. For temporal queries, use month, year, or date columns
        4. For depth queries, use the depth column (positive values)
        5. Include appropriate WHERE clauses for data quality (temperature_qc <= 2, salinity_qc <= 2)
        6. Limit results to reasonable numbers (e.g., LIMIT 1000 for large queries)
        7. Use proper SQL syntax for PostgreSQL
        8. Return only the SQL query, no explanations
        
        Examples:
        - "salinity near equator" → SELECT * FROM profiles WHERE latitude BETWEEN -5 AND 5 AND salinity IS NOT NULL AND salinity_qc <= 2 LIMIT 1000;
        - "temperature profiles deeper than 500m" → SELECT * FROM profiles WHERE depth > 500 AND temperature IS NOT NULL AND temperature_qc <= 2 LIMIT 1000;
        - "data from March 2024" → SELECT * FROM profiles WHERE month = 3 AND year = 2024 LIMIT 1000;
        
        SQL Query:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SQL query generator for oceanographic data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up the SQL query
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            # Fallback to simple query
            return "SELECT * FROM profiles LIMIT 100;"
    
    def generate_response(self, query: str, data_results: List[Dict[str, Any]], context: List[Dict[str, Any]] = None) -> str:
        """Generate natural language response from query results"""
        
        if not data_results:
            return "No data found matching your query. Please try a different search or check your parameters."
        
        # Analyze results
        result_count = len(data_results)
        
        # Calculate basic statistics
        stats = {}
        if data_results:
            numeric_fields = ['temperature', 'salinity', 'depth', 'latitude', 'longitude']
            for field in numeric_fields:
                values = [r.get(field) for r in data_results if r.get(field) is not None]
                if values:
                    stats[field] = {
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'count': len(values)
                    }
        
        # Build context
        context_text = ""
        if context:
            context_text = f"\nContext: {context[0].get('summary', '')}" if context else ""
        
        prompt = f"""
        Generate a natural language response for this oceanographic data query.
        
        Original Query: "{query}"
        
        Results Summary:
        - Found {result_count} data points
        - Statistics: {json.dumps(stats, indent=2)}
        
        {context_text}
        
        Provide a clear, informative response that:
        1. Summarizes what was found
        2. Highlights key patterns or insights
        3. Mentions geographic and temporal coverage
        4. Uses appropriate oceanographic terminology
        5. Is accessible to both experts and general users
        
        Keep the response concise but informative (2-3 paragraphs maximum).
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert oceanographer providing insights on ARGO float data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Found {result_count} data points matching your query. The data shows temperature ranging from {stats.get('temperature', {}).get('min', 'N/A')} to {stats.get('temperature', {}).get('max', 'N/A')}°C and salinity from {stats.get('salinity', {}).get('min', 'N/A')} to {stats.get('salinity', {}).get('max', 'N/A')} PSU."

class RAGPipeline:
    """Complete RAG pipeline for ARGO data queries"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Initialize components if available
        self.vector_db = None
        self.sql_generator = None
        
        if VECTOR_DB_AVAILABLE:
            try:
                self.vector_db = VectorDatabase()
                self._initialize_vector_database()
            except Exception as e:
                logger.error(f"Failed to initialize vector database: {e}")
        
        if LLM_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.sql_generator = SQLQueryGenerator()
            except Exception as e:
                logger.error(f"Failed to initialize SQL generator: {e}")
    
    def _initialize_vector_database(self):
        """Initialize vector database with existing summaries"""
        if not self.vector_db:
            return
        
        # Load existing summaries from database
        summaries = self.db.query(DataSummary).all()
        
        if summaries:
            texts = [s.summary_text for s in summaries if s.summary_text]
            metadata = [
                {
                    'id': s.id,
                    'region': s.region_name,
                    'summary': s.summary_text,
                    'profile_count': s.profile_count,
                    'date_range': f"{s.start_date} to {s.end_date}",
                    'keywords': s.keywords
                }
                for s in summaries if s.summary_text
            ]
            
            if texts:
                self.vector_db.add_documents(texts, metadata)
                logger.info(f"Initialized vector database with {len(texts)} summaries")
    
    def process_query(self, query: str) -> QueryResult:
        """Process natural language query through complete RAG pipeline"""
        
        # Step 1: Retrieve relevant context
        context = []
        if self.vector_db:
            try:
                search_results = self.vector_db.search(query, k=5)
                context = [result[0] for result in search_results if result[1] > 0.3]  # Similarity threshold
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
        
        # Step 2: Generate SQL query
        sql_query = "SELECT * FROM profiles LIMIT 100;"  # Default fallback
        if self.sql_generator:
            try:
                sql_query = self.sql_generator.generate_sql_query(query, context)
            except Exception as e:
                logger.error(f"SQL generation failed: {e}")
        
        # Step 3: Execute query
        data_results = []
        try:
            result = self.db.execute(text(sql_query))
            columns = result.keys()
            data_results = [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            # Fallback to simple query
            profiles = self.db.query(Profile).limit(10).all()
            data_results = [p.to_dict() for p in profiles]
        
        # Step 4: Generate natural language response
        natural_response = f"Found {len(data_results)} data points."
        if self.sql_generator:
            try:
                natural_response = self.sql_generator.generate_response(query, data_results, context)
            except Exception as e:
                logger.error(f"Response generation failed: {e}")
        
        # Step 5: Calculate confidence score
        confidence_score = 0.8 if self.sql_generator and self.vector_db else 0.5
        if not data_results:
            confidence_score *= 0.5
        
        return QueryResult(
            sql_query=sql_query,
            natural_language_response=natural_response,
            data_results=data_results,
            metadata={
                'context_used': len(context),
                'execution_time': datetime.now().isoformat(),
                'result_count': len(data_results)
            },
            confidence_score=confidence_score
        )
    
    def add_data_summary(self, region_name: str, summary_text: str, **kwargs):
        """Add a new data summary to the vector database"""
        
        # Create database entry
        summary = DataSummary(
            region_name=region_name,
            summary_text=summary_text,
            **kwargs
        )
        self.db.add(summary)
        self.db.commit()
        
        # Add to vector database
        if self.vector_db:
            metadata = {
                'id': summary.id,
                'region': region_name,
                'summary': summary_text,
                'profile_count': kwargs.get('profile_count', 0)
            }
            self.vector_db.add_documents([summary_text], [metadata])

# Convenience functions
def create_rag_pipeline(db: Session) -> RAGPipeline:
    """Create RAG pipeline instance"""
    return RAGPipeline(db)

def process_natural_language_query(query: str, db: Session) -> QueryResult:
    """Process a natural language query"""
    pipeline = RAGPipeline(db)
    return pipeline.process_query(query)
