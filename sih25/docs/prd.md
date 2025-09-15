# FloatChat Product Requirements Document (PRD)

## Goals and Background Context

### Goals
- Democratize access to ARGO oceanographic data through natural language conversations
- Enable non-technical users to query, explore, and visualize complex ocean data effortlessly  
- Deliver real-time data ingestion pipeline with intelligent preprocessing and validation
- Create interactive geospatial visualizations for ocean profiles, trajectories, and BGC parameters
- Demonstrate scalable PoC with Indian Ocean ARGO data within 10-day hackathon timeline

### Background Context

Oceanographic data represents one of the most complex and underutilized scientific datasets globally. With 95% of our oceans unmapped while we've fully mapped the Moon and Mars, accessing ARGO float data requires deep domain expertise and technical skills. The ARGO program generates extensive NetCDF datasets containing temperature, salinity, and biogeochemical measurements from autonomous floats worldwide.

Current barriers include complex NetCDF formats, quality control flag interpretation, and the need for specialized tools. FloatChat bridges this gap by combining AI conversational interfaces with modern data infrastructure, making ocean insights accessible to researchers, decision-makers, and the broader scientific community.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| September 15, 2025 | 1.0 | Initial PRD creation from brainstorming materials | PM Agent |

## Requirements


### Functional Requirements

**FR1**: The system shall ingest ARGO NetCDF profile files (both real-time "R" and delayed-mode "D" prefixed files) and automatically detect file types (Core, BGC, synthetic profiles)

**FR2**: The system shall parse NetCDF files using DATA_MODE and PARAMETER_DATA_MODE fields to correctly select adjusted vs raw variables according to official ARGO protocols

**FR3**: The system shall validate data quality using QC flags, prioritizing QC=1 (good data) and filtering out QC=4 (bad data) according to ARGO standards

**FR4**: The system shall convert parsed NetCDF data into structured SQL format and store in PostgreSQL database via Supabase

**FR5**: The system shall extract and store float metadata separately from profile measurements, including float ID, deployment details, PI information, and sensor capabilities

**FR6**: The system shall generate vector embeddings for profile summaries and metadata, storing them in ChromaDB for semantic retrieval

**FR7**: The system shall provide a conversational chat interface where users can ask natural language questions about ARGO data (e.g., "Show salinity profiles near equator in March 2023")

**FR8**: The system shall translate natural language queries to database operations using RAG pipeline with LLM integration via Model Context Protocol (MCP)

**FR9**: The system shall provide interactive dashboard with two-column layout: left column for Plotly Dash visualizations, right column for chat interface

**FR10**: The system shall generate geospatial visualizations including float trajectory maps, depth-time profiles, and BGC parameter comparisons

**FR11**: The system shall support voice interaction mode using Pipecat for real-time speech-to-text and text-to-speech conversion

**FR12**: The system shall provide intelligent data pipeline with auto-trigger functionality when vector store or SQL database is empty

**FR13**: The system shall include RESET functionality in UI (top-right, dark red button with white text, 3px rounded corners) to clear database and vector store data

**FR14**: The system shall focus on Indian Ocean ARGO data for proof-of-concept demonstration per INCOIS requirements

**FR15**: The system shall export visualization results and tabular data in multiple formats (CSV, NetCDF, ASCII)

### Non-Functional Requirements

**NFR1**: The system shall process and validate uploaded NetCDF files within 60 seconds for files up to 50MB using fail-fast validation approach

**NFR2**: The system shall maintain 99% uptime during demonstration period with proper error handling and graceful degradation

**NFR3**: The system shall support concurrent user sessions with response times under 3 seconds for database queries

**NFR4**: The system shall implement Pydantic-based data validation with comprehensive schema checking and range validation

**NFR5**: The system shall use efficient ETL pipeline with xarray/netCDF4 for parsing and pandas for data transformation

**NFR6**: The system shall maintain data scientific integrity by following official ARGO data usage guidelines and QC protocols

**NFR7**: The system shall be developed within 10-day hackathon timeline using Python with uv virtual environment management

**NFR8**: The system shall integrate AGNO agent framework with MCP server tools for reliable LLM interactions

**NFR9**: The system shall implement proper security measures for database access and API endpoints via Supabase authentication

**NFR10**: The system shall support extensibility for future integration with additional oceanographic datasets (BGC, glider, buoys, satellite data)


