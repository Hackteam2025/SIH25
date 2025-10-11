# Argo Metadata Vector Database & AI Agent

Complete system for extracting, storing, and querying Argo float metadata using vector embeddings and AI.

## Overview

This system:
1. **Extracts** metadata from Argo NetCDF metadata files
2. **Embeds** metadata using Mistral embeddings
3. **Stores** embeddings in PostgreSQL with pgvector
4. **Queries** using semantic search and AI agent

## Components

### 1. `metadata_extractor.py`
Extracts structured metadata from Argo `.nc` metadata files.

```bash
# Extract metadata from a single file
python metadata_extractor.py data/1900121_meta.nc

# Save to JSON
python metadata_extractor.py data/1900121_meta.nc output.json
```

### 2. `vector_db_loader.py`
Loads metadata into PostgreSQL vector database with embeddings.

```bash
# Create vector table
python vector_db_loader.py create-table

# Load a single metadata file
python vector_db_loader.py load-file data/1900121_meta.nc

# Load all metadata files from directory
python vector_db_loader.py load-dir data/ --pattern "*_meta.nc"

# Search for similar metadata
python vector_db_loader.py search --query "CTD sensor specifications"
```

### 3. `ai_agent.py`
AI agent that queries metadata using semantic search.

```bash
# Query with context retrieval
python ai_agent.py query --question "What sensors does platform 1900121 have?"

# Interactive session
python ai_agent.py interactive

# Run test queries
python ai_agent.py test --output test_results.json
```

## Quick Start

### Prerequisites

```bash
# Install required packages
pip install asyncpg mistralai xarray netCDF4 numpy
```

### Environment Variables

Make sure these are set in your `.env`:

```bash
DATABASE_URL=postgresql://...
MISTRAL_API_KEY=your_mistral_key
```

### Step-by-Step Usage

#### Step 1: Create Vector Table

```bash
cd sih25/DATAOPS/METADATA
python vector_db_loader.py create-table
```

#### Step 2: Load Metadata

```bash
# Load specific file
python vector_db_loader.py load-file ../PROFILES/data/1900121_meta.nc

# Or load all metadata files
python vector_db_loader.py load-dir ../PROFILES/data/ --pattern "*_meta.nc"
```

#### Step 3: Query with AI Agent

```bash
# Single query
python ai_agent.py query --question "Tell me about float 1900121's deployment"

# Interactive mode
python ai_agent.py interactive
```

#### Step 4: Test Queries

```bash
python ai_agent.py test
```

## Complete Example

```bash
#!/bin/bash

# 1. Setup
cd /Users/prada/Desktop/coding/SIH25/sih25/DATAOPS/METADATA

# 2. Create table
echo "Creating vector table..."
python vector_db_loader.py create-table

# 3. Load metadata
echo "Loading metadata from 1900121_meta.nc..."
python vector_db_loader.py load-file ../PROFILES/data/1900121_meta.nc

# 4. Test search
echo "Testing semantic search..."
python vector_db_loader.py search --query "CTD sensor information" --limit 3

# 5. Query with AI agent
echo "Querying AI agent..."
python ai_agent.py query --question "What sensors does platform 1900121 have?"

# 6. Run comprehensive tests
echo "Running test suite..."
python ai_agent.py test --output test_results.json

echo "✓ Complete! Check test_results.json for outputs"
```

## Database Schema

The system creates this table:

```sql
CREATE TABLE argo_metadata_vectors (
    id SERIAL PRIMARY KEY,
    platform_number VARCHAR(255) NOT NULL UNIQUE,
    source_file VARCHAR(500) NOT NULL,
    metadata JSONB NOT NULL,
    searchable_text TEXT NOT NULL,
    embedding vector(1024),  -- Mistral embedding dimension
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

With indexes:
- B-tree index on `platform_number`
- IVFFlat index on `embedding` for fast vector search
- GIN index on `searchable_text` for full-text search

## API Examples

### Python API

```python
from vector_db_loader import MetadataVectorDBLoader
from ai_agent import ArgoMetadataAgent
import asyncio

async def main():
    # Load metadata
    loader = MetadataVectorDBLoader()
    await loader.load_metadata_directory("data/", pattern="*_meta.nc")

    # Query with agent
    agent = ArgoMetadataAgent()
    result = await agent.query("What is the deployment location of float 1900121?")
    print(result['answer'])

asyncio.run(main())
```

### Verify Vector DB is Being Used

The AI agent will clearly show:
1. 🔍 When it searches the vector database
2. ✓ How many relevant entries it found
3. The similarity scores for each match
4. Whether context was used in the response

Example output:
```
🔍 Retrieving context for: 'What sensors does platform 1900121 have?'
  ✓ Found 3 similar entries

🤖 Generating response...

ANSWER:
--------------------------------------------------------------------------------
Platform 1900121 is equipped with the following sensors:
1. CTD sensor (SBE41) - manufactured by SBE, serial number 805
   - Measures: Temperature, Conductivity, Pressure
...
```

## Troubleshooting

### Issue: "Table already exists"
```bash
# Drop and recreate if needed
psql $DATABASE_URL -c "DROP TABLE IF EXISTS argo_metadata_vectors CASCADE;"
python vector_db_loader.py create-table
```

### Issue: "No context found"
- Check that metadata files were loaded: `SELECT COUNT(*) FROM argo_metadata_vectors;`
- Lower similarity threshold: `--similarity-threshold 0.3`

### Issue: "Mistral API error"
- Verify `MISTRAL_API_KEY` is set correctly
- Check API quota/limits

## Performance

- **Embedding generation**: ~1-2 seconds per file
- **Vector search**: <100ms for typical queries
- **End-to-end query**: ~2-3 seconds (including LLM response)

## Advanced Usage

### Custom Similarity Threshold

```bash
python ai_agent.py query \
    --question "Float specifications" \
    --top-k 5 \
    --similarity-threshold 0.3
```

### Batch Processing

```python
import asyncio
from vector_db_loader import MetadataVectorDBLoader

async def batch_load():
    loader = MetadataVectorDBLoader()

    # Load multiple directories
    directories = ["data1/", "data2/", "data3/"]

    for directory in directories:
        result = await loader.load_metadata_directory(directory)
        print(f"Loaded {result['successful']} files from {directory}")

asyncio.run(batch_load())
```

## Architecture

```
┌─────────────────┐
│  NetCDF Files   │
│  (*_meta.nc)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Metadata Extractor  │  ← Decodes NetCDF, structures data
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Mistral Embeddings │  ← Generates vector embeddings
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   PostgreSQL +      │
│    pgvector         │  ← Stores embeddings + metadata
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Semantic Search    │  ← Vector similarity search
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│    AI Agent         │  ← Mistral LLM with context
│  (Mistral Large)    │
└─────────────────────┘
```

## License

Part of SIH25 project.
