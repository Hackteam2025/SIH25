# Story: Vector Database Integration with ChromaDB

<!-- Source: Brownfield PRD + Architecture documents -->
<!-- Context: Brownfield enhancement - Semantic search for oceanographic data -->

## Status: Draft

## Story

As a **conversational AI system**,
I want **semantic search capabilities through ChromaDB vector embeddings**,
so that **users can find relevant oceanographic data through natural language descriptions and contextual queries**.

## Context Source

- Source Document: docs/prd.md + docs/architecture.md
- Enhancement Type: Semantic search and retrieval system
- Existing System Impact: Extends DATA LOADER to generate embeddings; enhances MCP Tool Server

## Acceptance Criteria

1. **New functionality works as specified**:
   - ChromaDB vector database stores embeddings of profile summaries and float metadata
   - Semantic search returns relevant profiles based on natural language descriptions
   - Vector search integrates with existing MCP tools for hybrid retrieval
   - Embeddings automatically generated during DATA LOADER processing

2. **Integration with existing components**:
   - DATA LOADER extended to create and store vector embeddings
   - MCP Tool Server includes vector search tools alongside SQL queries
   - AI Agent can combine semantic search with structured queries
   - No disruption to existing database schema or workflows

3. **Retrieval-Augmented Generation (RAG) capability**:
   - Natural language queries like "warm water profiles in tropical regions"
   - Semantic similarity matching for oceanographic concepts
   - Context-aware search that understands scientific terminology
   - Ranked results based on relevance and data quality

4. **Performance and accuracy**:
   - Vector search completes within API response time limits
   - Semantically similar profiles ranked appropriately
   - Integration with existing query validation and QC filtering

## Dev Technical Guidance

### Existing System Context

**Integration Points:**
- DATA LOADER (Story 1): Extend to generate embeddings during PostgreSQL loading
- MCP Tool Server (Story 2): Add vector search tools alongside existing database tools
- AI Agent (Story 3): Use vector search for better query understanding

**Current Database Schema:**
- `profiles` table contains metadata suitable for embedding generation
- `observations` table has scientific measurements for context
- Quality reports and processing logs provide additional context

**Embedding Content Strategy:**
```python
# Profile embedding content
profile_summary = f"""
Float {float_id} profile from {timestamp}
Location: {latitude}, {longitude}
Depth range: {min_depth}m to {max_depth}m
Parameters: {available_parameters}
Data quality: {qc_summary}
Seasonal context: {season_info}
Regional context: {ocean_region}
"""
```

### Integration Approach

**ChromaDB Setup:**
- Local ChromaDB instance for development
- Collections organized by data type (profiles, floats, regions)
- Metadata filtering combined with vector similarity search
- Persistent storage aligned with existing database location

**Vector Search Tools for MCP Server:**
```python
# New tools to add to existing MCP server
async def semantic_search_profiles(query: str, limit: int = 10) -> List[ProfileMatch]
async def find_similar_profiles(profile_id: str, similarity_threshold: float = 0.8) -> List[ProfileMatch]
async def search_by_description(description: str, region: Optional[BoundingBox] = None) -> List[ProfileMatch]
async def get_profile_context(profile_id: str) -> ProfileContext
```

**Embedding Model Selection:**
- Use sentence-transformers for oceanographic text
- Consider domain-specific models if available
- Fallback to OpenAI embeddings if model performance insufficient

### Technical Constraints

- **Data Privacy**: Embeddings stored locally, no external API dependencies for search
- **Scientific Accuracy**: Vector results must still respect QC filtering
- **Performance**: Embedding generation shouldn't significantly slow DATA LOADER
- **Storage**: Vector database size should be reasonable for demo environment
- **Integration**: Minimal changes to existing working components

### Missing Information

❗ **User Input Needed:**
1. **Embedding Model**: Should we use sentence-transformers, OpenAI embeddings, or domain-specific models?
2. **ChromaDB Location**: Should vector database be co-located with PostgreSQL or separate service?
3. **Update Strategy**: How should embeddings be updated when new data is processed?
4. **Search Weighting**: How should vector similarity be balanced with structured query results?

## Tasks / Subtasks

- [ ] **Task 1: Set up ChromaDB environment**
  - [ ] Install ChromaDB in existing uv environment
  - [ ] Create `sih25/VECTOR/` directory for vector database operations
  - [ ] Configure persistent storage location for ChromaDB collections
  - [ ] Test basic embedding storage and retrieval functionality

- [ ] **Task 2: Extend DATA LOADER with embedding generation**
  - [ ] Modify `sih25/LOADER/data_loader.py` to generate profile embeddings
  - [ ] Create embedding generation pipeline for profile summaries and metadata
  - [ ] Add ChromaDB collection management and batch insertion
  - [ ] Ensure embedding generation doesn't break existing PostgreSQL loading

- [ ] **Task 3: Implement vector search tools**
  - [ ] Add vector search functions to `sih25/API/tools/vector_search.py`
  - [ ] Implement semantic search with metadata filtering
  - [ ] Create hybrid search combining vector similarity and structured filters
  - [ ] Add profile similarity and contextual search capabilities

- [ ] **Task 4: Integrate with MCP Tool Server**
  - [ ] Add vector search endpoints to existing FastAPI MCP server
  - [ ] Implement tool registration for vector search capabilities
  - [ ] Add proper input validation and error handling for vector queries
  - [ ] Test integration with existing database tools for hybrid retrieval

- [ ] **Task 5: Enhance AI Agent with semantic capabilities**
  - [ ] Update AI Agent to use vector search for better query understanding
  - [ ] Implement query routing between structured and semantic search
  - [ ] Add context enhancement using similar profile retrieval
  - [ ] Test natural language query improvements with vector search

- [ ] **Task 6: Verify integration and performance**
  - [ ] Test complete pipeline: DATA LOADER → embeddings → vector search
  - [ ] Validate search quality with oceanographic test queries
  - [ ] Check performance impact on existing workflows
  - [ ] Verify QC filtering still applies to vector search results

## Risk Assessment

### Implementation Risks

- **Primary Risk**: Vector search returns irrelevant results due to poor embeddings
- **Mitigation**: Careful prompt engineering for embedding content and evaluation with domain experts
- **Verification**: A/B testing of search results with and without vector enhancement

- **Secondary Risk**: ChromaDB integration causes performance degradation
- **Mitigation**: Asynchronous embedding generation and search result caching
- **Verification**: Load testing of complete system with vector search enabled

### Rollback Plan

- Disable vector search endpoints in MCP server configuration
- DATA LOADER skips embedding generation if ChromaDB unavailable
- AI Agent falls back to structured database queries only
- No impact on core database functionality

### Safety Checks

- [ ] Vector search results still respect ARGO QC filtering
- [ ] Embedding generation doesn't corrupt PostgreSQL data loading
- [ ] ChromaDB failures don't break existing API functionality
- [ ] Vector search respects same access patterns as database queries

## Definition of Done

- [ ] ChromaDB successfully stores embeddings of profile summaries and metadata
- [ ] Vector search tools integrated into MCP Tool Server
- [ ] AI Agent demonstrates improved query understanding with semantic search
- [ ] Hybrid queries combine vector similarity with structured filters
- [ ] Performance remains within acceptable bounds for demo
- [ ] Search quality validated with realistic oceanographic queries
- [ ] Integration maintains all existing functionality and scientific accuracy