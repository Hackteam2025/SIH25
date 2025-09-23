# FloatChat Agent Usage Guide

## Quick Start

### 1. Set Environment Variables
```bash
# For OpenAI (default)
export OPENAI_API_KEY="your-openai-api-key"

# OR for Anthropic Claude
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export LLM_PROVIDER="anthropic"
export MODEL_NAME="claude-3-5-sonnet-20241022"
```

### 2. Start the MCP Tool Server
```bash
# In one terminal
source .venv/bin/activate
python sih25/API/main.py
```

### 3. Interactive Chat Session
```bash
# In another terminal
source .venv/bin/activate
python sih25/AGENT/start_agent.py
```

### 4. API Usage
```bash
# Start the full API server with agent endpoints
curl -X POST "http://localhost:8000/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me temperature profiles near the equator"}'
```

## Example Queries

### Spatial Queries
- "Show me temperature profiles near the equator"
- "Find ARGO floats within 100km of latitude 40, longitude -70"
- "Get measurements from the North Atlantic"

### Parameter-Specific Queries
- "What's the average salinity in recent measurements?"
- "Show me dissolved oxygen data from tropical waters"
- "Get chlorophyll measurements from the Mediterranean"

### Temporal Queries
- "Find recent temperature data"
- "Show me measurements from last winter"
- "Get data from March 2023"

### Analysis Queries
- "Calculate statistics for temperature profiles"
- "Compare salinity between different regions"
- "Show me quality control information"

## API Endpoints

### Agent Chat
```
POST /agent/chat
{
  "message": "Your natural language query",
  "session_id": "optional-session-id",
  "context": {"optional": "context"}
}
```

### Session Summary
```
GET /agent/session/{session_id}/summary
```

### Health Check
```
GET /agent/health
```

## Features

✅ **Natural Language Processing**: Understands oceanographic queries in plain English
✅ **Multi-turn Conversations**: Maintains context across multiple exchanges
✅ **Scientific Accuracy**: Provides ARGO-compliant data with quality control
✅ **Visualization Ready**: Returns data formatted for charts and maps
✅ **Follow-up Suggestions**: Guides users to explore related data
✅ **Error Handling**: Graceful degradation with helpful error messages

## Architecture

- **FloatChatAgent**: Main AGNO-based conversational interface
- **MCPToolClient**: Integration with MCP Tool Server for database access
- **ConversationMemory**: Session management and context tracking
- **ScientificContext**: Oceanographic domain knowledge and validation
- **FastAPI Integration**: RESTful API endpoints for web interfaces