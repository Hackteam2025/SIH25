#!/bin/bash
# Quick restart script for all services after fixes

echo "🔄 Restarting all JARVIS FloatChat services..."
echo "=================================="

# Kill existing services
echo "⏹️  Stopping existing services..."
pkill -f "sih25/API/main.py" 2>/dev/null
pkill -f "sih25/AGENT/api.py" 2>/dev/null
pkill -f "sih25/FRONTEND/app.py" 2>/dev/null
sleep 2

# Start services in background
echo "▶️  Starting MCP Tool Server..."
uv run sih25/API/main.py > /tmp/mcp_server.log 2>&1 &
sleep 3

echo "▶️  Starting JARVIS Agent Server..."
uv run sih25/AGENT/api.py > /tmp/agent_server.log 2>&1 &
sleep 3

echo "▶️  Starting Frontend Dashboard..."
uv run sih25/FRONTEND/app.py > /tmp/frontend.log 2>&1 &
sleep 3

echo ""
echo "✅ All services restarted!"
echo ""
echo "📊 Service Status:"
echo "  • MCP Server: http://localhost:8000/health"
echo "  • Agent API: http://localhost:8001/health"
echo "  • Frontend: http://localhost:8050"
echo ""
echo "📝 Logs available at:"
echo "  • /tmp/mcp_server.log"
echo "  • /tmp/agent_server.log"
echo "  • /tmp/frontend.log"
echo ""
echo "🧪 Run test: uv run test_integration_fix.py"