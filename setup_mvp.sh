#!/bin/bash
# FloatChat MVP Quick Setup Script
# ================================

set -e  # Exit on any error

echo "🌊 FloatChat MVP - Quick Setup"
echo "=============================="

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
echo "✅ Python version: $python_version"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Python 3.8+ required. Current: $python_version"
    exit 1
fi

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
    echo "   Required: GROQ_API_KEY (or OPENAI_API_KEY)"
else
    echo "✅ .env file exists"
fi

# Install requirements if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    echo "📦 Installing dependencies..."
    if command -v uv &> /dev/null; then
        echo "🚀 Using uv for fast installation..."
        uv install
    elif command -v pip &> /dev/null; then
        echo "📦 Using pip..."
        pip install -e .
    else
        echo "❌ No package installer found (pip or uv required)"
        exit 1
    fi
else
    echo "⚠️  No pyproject.toml found, skipping dependency installation"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/argo
mkdir -p data/processed
mkdir -p chroma_db
mkdir -p sih25/DATAOPS/PROFILES/data
mkdir -p sih25/DATAOPS/PROFILES/output

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Run: python3 run_mvp.py"
echo "3. Open http://localhost:8050 in your browser"
echo ""
echo "🔑 Required API Keys:"
echo "   - Get GROQ_API_KEY from: https://console.groq.com/"
echo "   - Or OPENAI_API_KEY from: https://platform.openai.com/api-keys"
echo ""
echo "🎯 Features Ready:"
echo "   ✅ AI Agent with Voice (Story 3)"
echo "   ✅ MCP Tool Server (Story 2)"
echo "   ✅ Data Pipeline (Story 1)"
echo "   ✅ Interactive Frontend (Story 4)"
echo "   ✅ Vector Database (Story 5)"
echo ""