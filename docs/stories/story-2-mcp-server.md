# Story: MCP Tool Server Implementation

<!-- Source: Brownfield PRD + Architecture documents -->
<!-- Context: Brownfield enhancement - FastAPI server for AI Agent tools -->

## Status: Draft

## Story

As an **AI system architect**,
I want **a secure MCP Tool Server that provides database access tools for the AI Agent**,
so that **the AI can safely query oceanographic data without direct database access**.

## Context Source

- Source Document: docs/prd.md + docs/architecture.md
- Enhancement Type: API layer with AI-safe database tools
- Existing System Impact: Reads from PostgreSQL populated by DATA LOADER

## Acceptance Criteria

1. **New functionality works as specified**:
   - FastAPI MCP server exposes secure, validated tools for AI Agent
   - Tools follow ARGO protocols (QC flags, data modes) automatically
   - Server-side query validation prevents malformed/unsafe database access
   - All responses include scientific context and data provenance

2. **Existing database integrity maintained**:
   - No direct database modifications by AI Agent
   - Read-only access through predefined, validated tools
   - ARGO data quality protocols enforced at tool level

3. **Integration with AI Agent framework**:
   - Compatible with AGNO framework MCP protocol
   - Tools return structured responses suitable for LLM processing
   - Conversation context maintained across tool calls

4. **Performance within bounds**:
   - P95 API response time under 3 seconds (per PRD NFR-02)
   - Supports 10+ concurrent users during demo (per PRD NFR-06)

## Dev Technical Guidance

### Existing System Context

**Database Schema (from DATA LOADER story):**
- `floats` table: Float metadata with `wmo_id` primary key
- `profiles` table: Measurement cycles with geospatial and temporal data
- `observations` table: Scientific measurements with QC flags

**ARGO Protocol Requirements:**
- Prioritize QC flags 1 (good) and 2 (probably good)
- Never return QC flag 4 (bad data) without explicit warning
- Prefer delayed-mode ('D') over real-time ('R') data
- Include data provenance in all responses

**Tech Stack Alignment:**
- Python 3.11 with existing uv environment
- Must integrate with Supabase PostgreSQL connection
- Follow async/await patterns from DATAOPS pipeline

### Integration Approach

**MCP Tools to Implement (from PRD Section 8.3):**

```python
# Core query tools
async def list_profiles(region: BoundingBox, time_start: datetime, time_end: datetime, has_bgc: bool = False) -> List[ProfileSummary]
async def get_profile_details(profile_id: str) -> ProfileDetail
async def search_floats_near(lon: float, lat: float, radius_km: float) -> List[FloatSummary]
async def get_profile_statistics(profile_id: str, variable: str) -> VariableStats

# Spatial and temporal helpers
async def search_by_region(region_name: str) -> List[ProfileSummary]  # e.g. "Arabian Sea"
async def get_seasonal_data(season: str, year: int) -> List[ProfileSummary]
async def compare_profiles(profile_ids: List[str], parameter: str) -> ComparisonResult
```

**FastAPI Structure:**
- `/health` - Server health check
- `/mcp/tools` - List available tools for AI Agent
- `/mcp/call/{tool_name}` - Execute specific tool with validation
- `/api/v1/*` - Future REST endpoints for Frontend

### Technical Constraints

- **Security**: All inputs validated with Pydantic models
- **AI Sandboxing**: No direct SQL access, only predefined tools
- **Scientific Accuracy**: 100% ARGO protocol compliance (per PRD NFR-06)
- **Error Handling**: Graceful failures with scientific context
- **Logging**: Full audit trail of AI tool usage

### Missing Information

❗ **User Input Needed:**
1. **AGNO Framework**: Do you have AGNO already set up, or should this story include AGNO installation?
2. **MCP Protocol**: Are you using a specific MCP library, or should we implement the protocol directly?
3. **Authentication**: Should the MCP server require API keys or run on localhost during development?

## Tasks / Subtasks

- [ ] **Task 1: Set up FastAPI MCP Server foundation**
  - [ ] Create `sih25/API/` directory structure
  - [ ] Implement `sih25/API/main.py` with FastAPI application
  - [ ] Add health check and basic MCP protocol endpoints
  - [ ] Configure async database connection using existing patterns

- [ ] **Task 2: Implement core MCP tools**
  - [ ] Create `sih25/API/tools/` directory for tool implementations
  - [ ] Implement `list_profiles()` with spatial/temporal filtering
  - [ ] Implement `get_profile_details()` with full scientific context
  - [ ] Implement `search_floats_near()` for geospatial queries
  - [ ] Add `get_profile_statistics()` for variable analysis

- [ ] **Task 3: Add ARGO protocol validation**
  - [ ] Create validation middleware that enforces QC flag filtering
  - [ ] Implement data mode preference logic (D > A > R)
  - [ ] Add automatic scientific unit conversion and labeling
  - [ ] Include data provenance in all tool responses

- [ ] **Task 4: Implement query safety and validation**
  - [ ] Add Pydantic models for all tool inputs/outputs
  - [ ] Implement query size limits to prevent performance issues
  - [ ] Add input sanitization to prevent injection attacks
  - [ ] Create error responses with scientific context

- [ ] **Task 5: Add MCP protocol compatibility**
  - [ ] Research AGNO framework MCP requirements
  - [ ] Implement tool discovery endpoint (`/mcp/tools`)
  - [ ] Add tool execution endpoint with proper error handling
  - [ ] Test integration with basic AI Agent calls

- [ ] **Task 6: Verify integration with existing database**
  - [ ] Test all tools against database populated by DATA LOADER
  - [ ] Verify ARGO protocol compliance in responses
  - [ ] Check performance with realistic query loads
  - [ ] Validate scientific accuracy of returned data

## Risk Assessment

### Implementation Risks

- **Primary Risk**: AI Agent generates invalid queries that bypass validation
- **Mitigation**: Comprehensive input validation and query size limits
- **Verification**: Penetration testing with malformed inputs

- **Secondary Risk**: Performance degradation with complex spatial queries
- **Mitigation**: Database indexing and query optimization
- **Verification**: Load testing with concurrent requests

### Rollback Plan

- Disable MCP server endpoints in FastAPI configuration
- AI Agent falls back to error handling (no database access)
- Database remains unaffected by changes

### Safety Checks

- [ ] Database connection pool properly configured
- [ ] All tool inputs validated before execution
- [ ] Query timeouts prevent long-running operations
- [ ] Scientific data accuracy verified against known test data

## Definition of Done

- [ ] FastAPI MCP server runs and responds to health checks
- [ ] All core tools implemented and tested with real database data
- [ ] ARGO protocol compliance verified in tool responses
- [ ] Input validation prevents malformed queries
- [ ] Performance meets 3-second response time requirement
- [ ] Integration tested with AI Agent framework (AGNO)
- [ ] Error handling provides meaningful scientific context