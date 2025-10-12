#!/bin/bash
# Quick Start Script for Argo Metadata Vector DB System

set -e  # Exit on error

echo "========================================="
echo "Argo Metadata Vector DB - Quick Start"
echo "========================================="
echo ""

# Check if metadata file is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_metadata_nc_file>"
    echo ""
    echo "Example:"
    echo "  $0 ../PROFILES/data/1900121_meta.nc"
    exit 1
fi

METADATA_FILE="$1"

# Check if file exists
if [ ! -f "$METADATA_FILE" ]; then
    echo "Error: Metadata file not found: $METADATA_FILE"
    exit 1
fi

echo "✓ Using metadata file: $METADATA_FILE"
echo ""

# Move to METADATA directory
cd "$(dirname "$0")"

# Step 1: Install dependencies (if needed)
echo "Step 1: Checking dependencies..."
if ! python -c "import asyncpg" 2>/dev/null; then
    echo "  Installing required packages..."
    pip install -r requirements.txt
else
    echo "  ✓ Dependencies already installed"
fi
echo ""

# Step 2: Create vector table
echo "Step 2: Creating vector table..."
python vector_db_loader.py create-table
echo ""

# Step 3: Load metadata
echo "Step 3: Loading metadata into vector database..."
python vector_db_loader.py load-file "$METADATA_FILE"
echo ""

# Step 4: Test search
echo "Step 4: Testing semantic search..."
python vector_db_loader.py search --query "CTD sensor specifications" --limit 3
echo ""

# Step 5: Query with AI agent
echo "Step 5: Querying AI agent..."
python ai_agent.py query --question "What sensors are installed on this float?" --top-k 3
echo ""

# Step 6: Run comprehensive tests
echo "Step 6: Running comprehensive test suite..."
python test_runner.py "$METADATA_FILE" --output test_results.json
echo ""

echo "========================================="
echo "✓ Quick Start Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Check test_results.json for detailed results"
echo "  2. Try interactive mode: python ai_agent.py interactive"
echo "  3. Load more metadata: python vector_db_loader.py load-dir <directory>"
echo ""
echo "For more information, see README.md"
