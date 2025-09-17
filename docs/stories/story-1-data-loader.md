# Story: Data Loader Integration

<!-- Source: Brownfield PRD + Architecture documents -->
<!-- Context: Brownfield enhancement to existing DATAOPS pipeline -->

## Status: Draft

## Story

As a **data engineer**,
I want **a DATA LOADER that reads Parquet files from the DATAOPS pipeline and loads them into PostgreSQL**,
so that **the processed oceanographic data becomes queryable via SQL for the AI Agent and visualization dashboard**.

## Context Source

- Source Document: docs/prd.md + docs/architecture.md
- Enhancement Type: Database integration layer
- Existing System Impact: No changes to DATAOPS pipeline; reads its output files

## Acceptance Criteria

1. **New functionality works as specified**:
   - DATA LOADER successfully reads Parquet files from `sih25/DATAOPS/preprocessed_data/`
   - Data is correctly inserted into PostgreSQL following the three-table schema (`floats`, `profiles`, `observations`)
   - Processing metadata and quality reports are preserved

2. **Existing DATAOPS pipeline continues to work unchanged**:
   - No modifications to existing DATAOPS code
   - DATAOPS can still run independently
   - Original Parquet output format is preserved

3. **Integration maintains current behavior**:
   - DATAOPS → Parquet files → DATA LOADER → PostgreSQL chain works seamlessly
   - No data loss during the transformation process

4. **Performance remains within acceptable bounds**:
   - 50MB NetCDF files processed and loaded within 60 seconds (per PRD NFR-01)
   - Database loading completes within reasonable time after DATAOPS finishes

## Dev Technical Guidance

### Existing System Context

**Current DATAOPS Pipeline Output:**
- `{filename}_data.parquet` - Main processed data
- `{filename}_profiles.parquet` - Profile-level summaries
- `{filename}_quality_report.json` - QC assessment
- `{filename}_processing_log.json` - Processing metadata

**Current Tech Stack:**
- Python 3.11 with uv environment management
- Prefect for workflow orchestration
- Pydantic for data validation
- Async/await patterns throughout

**ARGO Protocol Compliance:**
- Quality Control flags: 1 (good), 2 (probably good) prioritized
- Data mode preference: 'D' (delayed) > 'A' (adjusted) > 'R' (real-time)
- Required variables: JULD, LATITUDE, LONGITUDE, PRES + scientific measurements

### Integration Approach

**Database Schema (from Architecture doc):**
```sql
-- floats: Metadata for each unique ARGO float
CREATE TABLE floats (
    wmo_id VARCHAR PRIMARY KEY,
    deployment_info JSONB,
    pi_details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- profiles: Each measurement cycle
CREATE TABLE profiles (
    profile_id VARCHAR PRIMARY KEY,
    float_wmo_id VARCHAR REFERENCES floats(wmo_id),
    timestamp TIMESTAMP,
    latitude FLOAT,
    longitude FLOAT,
    position_qc INTEGER,
    data_mode CHAR(1),
    created_at TIMESTAMP DEFAULT NOW()
);

-- observations: Scientific measurements
CREATE TABLE observations (
    observation_id SERIAL PRIMARY KEY,
    profile_id VARCHAR REFERENCES profiles(profile_id),
    depth FLOAT,
    parameter VARCHAR,
    value FLOAT,
    qc_flag INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Connection Strategy:**
- Use Supabase PostgreSQL (as specified in Architecture)
- Connection via environment variables
- Database URL: `DATABASE_URL` environment variable

### Technical Constraints

- **Database Integration**: Must work with Supabase PostgreSQL
- **Data Integrity**: All ARGO QC protocols must be maintained
- **Error Handling**: Graceful failure if database unavailable
- **Concurrent Access**: Support multiple users during demo (NFR per PRD)
- **Environment**: Must integrate with existing uv + Prefect setup

### Missing Information

❗ **User Input Needed:**
1. **Supabase Connection Details**: What's your Supabase project URL and service key?
2. **Table Creation**: Should the DATA LOADER create tables or assume they exist?
3. **Data Deduplication**: How should duplicate profiles be handled (upsert vs ignore)?
4. **Vector Embeddings**: Should this story include ChromaDB integration or separate story?

## Tasks / Subtasks

- [ ] **Task 1: Analyze existing Parquet schema structure**
  - [ ] Read `sih25/DATAOPS/preprocessed_data/*.parquet` files to understand data structure
  - [ ] Map Parquet columns to PostgreSQL schema (`floats`, `profiles`, `observations`)
  - [ ] Document any schema mismatches or transformations needed

- [ ] **Task 2: Implement DATABASE connection module**
  - [ ] Create `sih25/LOADER/database.py` for Supabase PostgreSQL connection
  - [ ] Add environment variable configuration (`DATABASE_URL`, connection pooling)
  - [ ] Include connection health checks and retry logic
  - [ ] Follow existing async/await patterns from DATAOPS

- [ ] **Task 3: Implement DATA LOADER core functionality**
  - [ ] Create `sih25/LOADER/data_loader.py` with Parquet → PostgreSQL logic
  - [ ] Implement three-table insertion logic (floats → profiles → observations)
  - [ ] Add deduplication strategy for existing profiles
  - [ ] Preserve ARGO QC compliance and data mode preferences

- [ ] **Task 4: Create orchestration integration**
  - [ ] Add DATA LOADER as downstream task in `main_orchestrator.py`
  - [ ] Ensure DATA LOADER runs automatically after DATAOPS export completes
  - [ ] Include error handling that doesn't break existing pipeline

- [ ] **Task 5: Verify existing DATAOPS functionality**
  - [ ] Run existing DATAOPS pipeline to confirm no regressions
  - [ ] Verify Parquet files are still generated correctly
  - [ ] Test that processing metadata/logs are preserved

- [ ] **Task 6: Add comprehensive tests**
  - [ ] Unit tests for database connection and insertion logic
  - [ ] Integration test for full DATAOPS → DATA LOADER flow
  - [ ] Test error scenarios (DB unavailable, malformed Parquet files)

## Risk Assessment

### Implementation Risks

- **Primary Risk**: Database schema mismatch between Parquet data and PostgreSQL tables
- **Mitigation**: Thorough analysis of existing Parquet structure before implementation
- **Verification**: Schema validation tests and sample data loading

### Rollback Plan

- Remove DATA LOADER task from `main_orchestrator.py`
- DATAOPS pipeline continues working independently with Parquet output
- No database dependencies in existing code

### Safety Checks

- [ ] Existing DATAOPS pipeline tested before any changes
- [ ] DATA LOADER can be disabled via environment variable
- [ ] Database operations are transactional (rollback on failure)

## Definition of Done

- [ ] DATA LOADER successfully processes existing test Parquet files
- [ ] PostgreSQL contains correctly structured data following schema
- [ ] DATAOPS pipeline integration works end-to-end
- [ ] All tests pass including regression tests for existing DATAOPS
- [ ] Error handling gracefully manages database connectivity issues
- [ ] Performance meets 60-second processing requirement from PRD