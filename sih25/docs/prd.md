# Product Requirements Document: FloatChat

## Executive Summary

FloatChat is an AI-powered conversational interface designed to democratize access to ARGO ocean data for oceanographers, researchers, and decision-makers. The system transforms complex NetCDF oceanographic datasets into an intuitive chat-based discovery and visualization platform, enabling natural language queries like "Show me salinity profiles near the equator in March 2023" to generate instant insights and interactive visualizations.

Built for the Smart India Hackathon 2025, FloatChat addresses the critical challenge identified by the Ministry of Earth Sciences (MoES) and Indian National Centre for Ocean Information Services (INCOIS): making vast, heterogeneous oceanographic data accessible to non-technical users while maintaining scientific accuracy and supporting advanced analytics.

The solution combines modern data engineering (NetCDF → PostgreSQL pipeline), AI agents (AGNO framework with MCP servers), vector-based retrieval (ChromaDB), and real-time visualization (Plotly Dash) into a unified platform that bridges the gap between raw ocean data and actionable insights.

## Problem Statement

### Current State Challenges

Oceanographic data from the ARGO program generates extensive datasets containing temperature, salinity, and biogeochemical measurements from autonomous profiling floats across global oceans. However, accessing and analyzing this data presents significant barriers:

- **Technical Complexity**: NetCDF format requires specialized domain knowledge and programming skills
- **Data Heterogeneity**: Multiple file types (profile, metadata, trajectory), real-time vs delayed-mode data, and varying quality control standards
- **Query Complexity**: Spatial-temporal queries require understanding of oceanographic principles, data structures, and quality flags
- **Visualization Barriers**: Creating meaningful plots requires knowledge of oceanographic visualization best practices
- **Non-Technical User Exclusion**: Decision-makers and domain experts without programming skills cannot independently explore data

### Opportunity

With advances in Large Language Models, vector databases, and modern visualization frameworks, it's now feasible to create intelligent systems that understand natural language queries about oceanographic data and generate appropriate analyses and visualizations automatically.

## Goals & Success Metrics

### Primary Goals

1. **Democratize Ocean Data Access**: Enable non-technical users to query and visualize ARGO data using natural language
2. **Maintain Scientific Integrity**: Ensure all data processing follows official ARGO protocols for quality control and variable selection
3. **Provide Comprehensive Discovery**: Support both casual exploration and detailed scientific analysis workflows
4. **Demonstrate AI-Native Approach**: Showcase conversational interfaces as the future of scientific data interaction

### Success Metrics

**User Experience Metrics**:
- Users can successfully query ocean data within 30 seconds of first interaction
- 90% of natural language queries return scientifically accurate results
- Average conversation length of 5+ exchanges indicating sustained engagement

**Technical Performance Metrics**:
- NetCDF file processing completed within 60 seconds for 50MB files
- Database queries return results within 3 seconds
- System supports 10+ concurrent users during demonstration

**Scientific Accuracy Metrics**:
- 100% compliance with ARGO data usage protocols (DATA_MODE, QC flags, adjusted variables)
- Zero incidents of displaying QC=4 (bad) data in user-facing results
- All visualizations include proper uncertainty estimates and data provenance

## Target Users

### Primary User Segment: Oceanographic Researchers
- **Profile**: PhD-level oceanographers, marine scientists, climate researchers
- **Current Workflow**: Manually download NetCDF files, write Python/MATLAB scripts for analysis
- **Pain Points**: Time-consuming data preparation, repetitive visualization coding
- **Goals**: Quick data exploration, hypothesis validation, comparative analysis
- **Success Definition**: Can generate publication-quality figures through conversation

### Secondary User Segment: Policy Makers & Decision Makers
- **Profile**: Government officials, environmental planners, maritime industry stakeholders
- **Current Workflow**: Request custom reports from technical teams
- **Pain Points**: Delayed access to insights, inability to ask follow-up questions
- **Goals**: Understand ocean trends for policy decisions, assess regional conditions
- **Success Definition**: Can independently answer questions about ocean conditions in their areas of responsibility

### Tertiary User Segment: Educational Users
- **Profile**: Graduate students, postdocs, early-career researchers
- **Current Workflow**: Learning oceanographic data analysis techniques
- **Pain Points**: Steep learning curve for data processing, limited access to mentorship
- **Goals**: Understand ocean data patterns, develop research questions
- **Success Definition**: Can explore data to generate thesis research directions

## Product Overview

### Core Value Proposition

FloatChat transforms the question "What does the ocean data tell us?" from a multi-day technical exercise into a natural conversation that generates immediate, scientifically accurate insights with supporting visualizations.

### Key Differentiators

1. **Scientific Compliance**: Built-in adherence to ARGO data protocols ensures research-grade accuracy
2. **Conversational Discovery**: Natural language interface eliminates programming barriers
3. **Contextual Intelligence**: AI agent remembers conversation context and suggests follow-up analyses
4. **Voice Integration**: Hands-free interaction for accessibility and mobile use cases
5. **Real-time Processing**: Live NetCDF ingestion enables analysis of newly available data

### User Experience Flow

1. **Data Upload/Discovery**: Users upload NetCDF files or system accesses pre-loaded Indian Ocean dataset
2. **Intelligent Parsing**: System automatically processes files according to ARGO protocols
3. **Conversational Query**: Users ask questions in natural language via text or voice
4. **Contextual Response**: AI agent generates appropriate database queries and visualizations
5. **Interactive Exploration**: Users refine queries, compare results, and export findings
6. **Knowledge Retention**: System learns from interactions to improve future responses

## Technical Architecture

### System Architecture Overview

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Data Ingestion    │    │    AI Agent Layer    │    │   User Interface    │
│                     │    │                      │    │                     │
│ • NetCDF Parser     │───▶│ • AGNO Agent         │───▶│ • Plotly Dash       │
│ • Schema Validator  │    │ • MCP Servers        │    │ • Chat Interface    │
│ • Quality Control   │    │ • RAG Pipeline       │    │ • Voice (Pipecat)   │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
            │                          │                          │
            ▼                          ▼                          │
┌─────────────────────┐    ┌──────────────────────┐              │
│   Data Storage      │    │   Vector Database    │              │
│                     │    │                      │              │
│ • PostgreSQL        │    │ • ChromaDB           │              │
│ • Supabase          │    │ • Embeddings         │              │
│ • PostGIS (future)  │    │ • Metadata Index     │              │
└─────────────────────┘    └──────────────────────┘              │
            │                                                     │
            └─────────────────────────────────────────────────────┘
```

### Data Pipeline Architecture

**Stage 1: Ingestion & Validation**
- NetCDF file upload via web interface
- xarray-based parsing with schema exploration
- Pydantic validation for required fields (lat, lon, time, pressure)
- ARGO protocol compliance checking (DATA_MODE, PARAMETER_DATA_MODE, QC flags)

**Stage 2: Processing & Transformation**
- Variable selection following ARGO best practices (prefer delayed-mode, adjusted variables, QC=1)
- Normalization into tabular format with proper scientific units
- Profile-level statistics computation (min/max/mean per parameter)
- Metadata extraction from file headers and attributes

**Stage 3: Storage & Indexing**
- Structured data storage in PostgreSQL via Supabase
- Vector embedding generation for profile summaries and metadata
- ChromaDB indexing for semantic retrieval
- Automatic relationship mapping between floats, profiles, and observations

**Stage 4: Query & Retrieval**
- Natural language processing via RAG pipeline
- MCP server-mediated database queries
- Vector similarity search for contextual information
- Result synthesis and visualization generation

### Database Schema Design

**Core Tables**:
- `floats`: Float metadata (WMO ID, deployment info, PI details, sensor capabilities)
- `profiles`: Individual measurement cycles (float_id, timestamp, position, QC summary)
- `observations`: Vertical measurements (profile_id, depth, parameter, value, qc_flag, error)
- `float_metadata`: Extended metadata for semantic search

**Vector Storage**:
- Profile summaries: Location, time, parameter ranges, quality indicators
- Float descriptions: Technical specifications, deployment context, operational status
- Query history: Previous successful natural language → SQL mappings

### AI Agent Architecture

**AGNO Agent Framework**:
- Memory: Conversation context and user preferences
- Tools: MCP servers for database access, data processing, and visualization
- Knowledge Base: ARGO data protocols, oceanographic domain knowledge
- Reasoning: Multi-step query decomposition and result synthesis

**MCP Server Tools**:
- `supabase_query`: Parameterized database queries with safety constraints
- `data_validator`: Real-time data quality assessment
- `viz_generator`: Plotly figure generation with oceanographic best practices
- `reset_system`: Database and vector store cleanup with confirmation
- `profile_analyzer`: Statistical analysis of ocean profiles

## Functional Requirements

### Data Ingestion & Processing

**FR1**: The system shall accept NetCDF profile files via web upload with support for files up to 100MB
**FR2**: The system shall automatically detect file types (Core, BGC, synthetic) and apply appropriate parsing logic
**FR3**: The system shall validate data according to ARGO protocols, prioritizing delayed-mode data with QC=1
**FR4**: The system shall extract both measurement data and comprehensive metadata from uploaded files
**FR5**: The system shall convert parsed data to structured SQL format and store in Supabase PostgreSQL
**FR6**: The system shall generate vector embeddings for all profile summaries and metadata

### Conversational Interface

**FR7**: The system shall provide a chat interface accepting natural language queries about ocean data
**FR8**: The system shall support voice input/output via Pipecat with real-time speech processing
**FR9**: The system shall maintain conversation context and suggest relevant follow-up questions
**FR10**: The system shall translate natural language to appropriate database queries using RAG pipeline
**FR11**: The system shall provide explanatory responses with scientific context and uncertainty estimates
**FR12**: The system shall handle multi-turn conversations with query refinement and comparison requests

### Data Visualization

**FR13**: The system shall generate interactive maps showing float trajectories and measurement locations
**FR14**: The system shall create depth-profile plots for temperature, salinity, and BGC parameters
**FR15**: The system shall support time-series visualization for temporal analysis
**FR16**: The system shall provide comparative visualizations for multi-float or multi-parameter analysis
**FR17**: The system shall include proper scientific labeling, units, and uncertainty indicators
**FR18**: The system shall enable export of visualizations in multiple formats (PNG, SVG, PDF)

### Data Query & Analysis

**FR19**: The system shall support spatial queries (bounding box, radius, named regions)
**FR20**: The system shall support temporal queries (date ranges, seasonal analysis)
**FR21**: The system shall enable parameter-specific filtering (temperature, salinity, BGC variables)
**FR22**: The system shall provide statistical analysis capabilities (mean, trends, anomalies)
**FR23**: The system shall support quality control filtering with user-specified QC thresholds
**FR24**: The system shall maintain data provenance for all generated results

### System Administration

**FR25**: The system shall provide a RESET function to clear database and vector store
**FR26**: The system shall automatically trigger data processing pipeline when stores are empty
**FR27**: The system shall log all user interactions and system responses for debugging
**FR28**: The system shall provide system health monitoring and status reporting
**FR29**: The system shall support bulk data loading for demonstration dataset preparation

## Non-Functional Requirements

### Performance Requirements

**NFR1**: NetCDF files up to 50MB shall be processed and available for querying within 60 seconds
**NFR2**: Database queries shall return results within 3 seconds for typical user requests
**NFR3**: The system shall support 10 concurrent users during demonstration period
**NFR4**: Vector similarity searches shall complete within 1 second for context retrieval
**NFR5**: Voice interaction latency shall not exceed 2 seconds for speech-to-text processing

### Reliability & Availability

**NFR6**: The system shall maintain 99% uptime during hackathon demonstration period
**NFR7**: All data processing shall include error handling with graceful degradation
**NFR8**: Failed NetCDF processing shall not affect other system components
**NFR9**: The system shall automatically recover from temporary database connection losses
**NFR10**: All user data shall be persisted with automatic backup mechanisms

### Scientific Accuracy & Compliance

**NFR11**: All data processing shall follow official ARGO data usage protocols
**NFR12**: The system shall never display QC=4 (bad) data without explicit user override
**NFR13**: Variable selection shall prioritize adjusted values when available per ARGO guidelines
**NFR14**: All visualizations shall include appropriate uncertainty estimates and data quality indicators
**NFR15**: The system shall maintain full traceability from source NetCDF to displayed results

### Usability & Accessibility

**NFR16**: New users shall be able to execute their first successful query within 30 seconds
**NFR17**: The system shall provide helpful error messages with suggested corrections
**NFR18**: Voice interface shall be accessible to users with visual impairments
**NFR19**: All visualizations shall follow colorblind-friendly design principles
**NFR20**: The system shall provide contextual help and example queries

### Development & Deployment

**NFR21**: The complete system shall be developed and demonstrated within 10 days
**NFR22**: All code shall be developed using Python with uv environment management
**NFR23**: The system shall be deployable on standard cloud infrastructure (Supabase, hosting platforms)
**NFR24**: All dependencies shall be clearly documented with version specifications
**NFR25**: The system shall include automated testing for core data processing functions

## MVP Scope & Feature Prioritization

### Core MVP Features (Must Have)

**Data Foundation**:
- NetCDF upload and processing pipeline with ARGO protocol compliance
- PostgreSQL storage with basic schema (floats, profiles, observations)
- Vector embedding generation and ChromaDB integration

**Basic AI Interface**:
- Text-based chat interface with natural language processing
- AGNO agent with MCP server integration for database queries
- Basic RAG pipeline for query translation and response generation

**Essential Visualizations**:
- Interactive map with float locations and trajectories
- Temperature/salinity depth profiles for individual floats
- Simple time-series plots for selected parameters

**Core User Workflows**:
- Upload NetCDF file → automatic processing → chat-based query → visualization
- Support for basic queries: "Show profiles near [location]", "Compare temperature at [depth]"

### Extended MVP Features (Should Have)

**Enhanced Interface**:
- Voice input/output via Pipecat integration
- Two-column dashboard layout (visualizations left, chat right)
- RESET functionality with confirmation dialog

**Advanced Visualizations**:
- BGC parameter visualization for biogeochemical floats
- Multi-float comparison plots
- Statistical analysis results (means, trends, anomalies)

**Improved AI Capabilities**:
- Conversation memory and context awareness
- Suggested follow-up queries
- Multi-turn query refinement

### Future Features (Nice to Have)

**Advanced Analytics**:
- Automated anomaly detection
- Seasonal analysis and climatology comparison
- Integration with satellite data

**Enhanced User Experience**:
- User authentication and saved sessions
- Export capabilities for results and visualizations
- Mobile-responsive interface design

**Extended Data Support**:
- Real-time data feeds from ARGO GDACs
- Integration with other oceanographic datasets (CTD, glider data)
- Support for custom user datasets

## Implementation Timeline (10-Day Sprint)

### Day 1-2: Foundation & Data Pipeline
- **Day 1**: Project setup, environment configuration, basic NetCDF parsing
- **Day 2**: Database schema implementation, Supabase integration, data validation framework

### Day 3-4: Core Processing & Storage
- **Day 3**: Complete data processing pipeline with ARGO protocol compliance
- **Day 4**: Vector embedding generation, ChromaDB integration, basic query testing

### Day 5-6: AI Agent & Interface
- **Day 5**: AGNO agent setup, MCP server integration, basic RAG pipeline
- **Day 6**: Chat interface implementation, natural language query processing

### Day 7-8: Visualization & Integration
- **Day 7**: Plotly Dash dashboard, basic map and profile visualizations
- **Day 8**: Two-column layout, voice integration via Pipecat

### Day 9-10: Polish & Demonstration
- **Day 9**: Error handling, UI polish, system testing with sample data
- **Day 10**: Final integration testing, documentation, demonstration preparation

## Risk Assessment & Mitigation

### Technical Risks

**High Risk: NetCDF Processing Complexity**
- *Risk*: ARGO data format variations may cause parsing failures
- *Mitigation*: Implement robust error handling, comprehensive test suite with various file types
- *Contingency*: Manual data preprocessing scripts for problematic files

**Medium Risk: AI Query Accuracy**
- *Risk*: Natural language queries may generate incorrect SQL or misleading results
- *Mitigation*: Implement query validation, result sanity checking, user confirmation for destructive operations
- *Contingency*: Fallback to template-based queries for common use cases

**Medium Risk: Performance with Large Datasets**
- *Risk*: System may be slow with large NetCDF files or complex queries
- *Mitigation*: Implement data pagination, query optimization, progress indicators
- *Contingency*: Sample data limitation for demonstration environment

### Timeline Risks

**High Risk: Integration Complexity**
- *Risk*: Connecting all components (AGNO, MCP, Pipecat, Dash) may take longer than expected
- *Mitigation*: Start with simple integrations, build incrementally, maintain working versions
- *Contingency*: Reduce scope to core chat interface if voice integration fails

**Medium Risk: Voice Integration Challenges**
- *Risk*: Pipecat voice processing may have latency or quality issues
- *Mitigation*: Test voice components early, optimize for demonstration environment
- *Contingency*: Focus on text-based interface if voice proves problematic

### Domain Risks

**Medium Risk: Scientific Accuracy Validation**
- *Risk*: Incorrect interpretation of ARGO data protocols may compromise scientific validity
- *Mitigation*: Thorough review of ARGO documentation, validation against known results
- *Contingency*: Conservative approach with explicit uncertainty statements

## Success Criteria & Validation

### Technical Validation

**Data Processing Accuracy**:
- Successfully parse 100% of test NetCDF files from Indian Ocean dataset
- Correctly identify and apply DATA_MODE/PARAMETER_DATA_MODE logic
- Generate valid SQL records matching source data statistical properties

**Query Performance**:
- Process typical user queries within 3-second response time
- Handle edge cases gracefully with informative error messages
- Maintain conversation context across multi-turn interactions

**Scientific Compliance**:
- Zero instances of displaying QC=4 data without explicit warnings
- All visualizations include proper units, uncertainty estimates, and data provenance
- Results reproducible across multiple query formulations

### User Experience Validation

**Usability Testing**:
- New users successfully complete sample queries within 30 seconds
- Voice interface recognized and processed correctly in quiet environment
- Dashboard layout intuitive for both technical and non-technical users

**Functionality Demonstration**:
- Successfully answer all example queries from problem statement
- Generate publication-quality visualizations for temperature and salinity profiles
- Demonstrate comparative analysis between different ocean regions or time periods

### Business Impact Validation

**Hackathon Success Metrics**:
- Complete working demonstration within 10-day development window
- Positive feedback from INCOIS evaluators on scientific accuracy and usability
- Clear demonstration of AI-native approach to oceanographic data interaction

**Future Viability Indicators**:
- Extensible architecture capable of supporting additional data sources
- Scalable design suitable for production deployment with larger datasets
- Interest from oceanographic community for continued development
