"""
SIH25 - FloatChat: AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization

A comprehensive data pipeline and AI-powered chatbot for processing, analyzing, and visualizing 
ARGO oceanographic float data through natural language conversations.

Main components:
- DATAOPS: Complete NetCDF to Parquet/SQL data processing pipeline
- API: FastAPI backend for data access and LLM integration
- Database: Supabase/PostgreSQL integration with vector embeddings
- UI: Interactive dashboard and chat interface
- Voice: Pipecat-powered voice conversation capabilities
"""

__version__ = "0.1.0"
__author__ = "Hackteam2025"
__description__ = "FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization"

# Make main components easily importable
try:
    from . import DATAOPS
except ImportError:
    # Handle missing optional dependencies gracefully
    pass

__all__ = [
    "__version__",
    "__author__", 
    "__description__",
    "DATAOPS",
]