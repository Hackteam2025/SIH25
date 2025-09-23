#!/usr/bin/env python3
"""
Test script for FloatChatAgent

Tests the AGNO-based AI agent functionality including:
- Agent initialization
- Natural language query processing
- MCP tool integration
- Conversation memory
- Scientific context
"""

import asyncio
import logging
import os
from typing import Dict, Any

from sih25.AGENT.float_chat_agent import FloatChatAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_agent_initialization():
    """Test agent initialization."""
    print("🔧 Testing Agent Initialization...")

    agent = FloatChatAgent(
        mcp_server_url="http://localhost:8000",
        llm_provider="openai",  # Change to "anthropic" if using Claude
        model_name="gpt-4"
    )

    success = await agent.initialize()
    print(f"✅ Agent initialization: {'SUCCESS' if success else 'FAILED'}")

    return agent if success else None


async def test_natural_language_queries(agent: FloatChatAgent):
    """Test natural language query processing."""
    print("\n💬 Testing Natural Language Queries...")

    test_queries = [
        "Show me temperature profiles near the equator from last month",
        "Find ARGO floats within 100km of latitude 40, longitude -70",
        "What's the average salinity in the North Atlantic?",
        "Get me recent oxygen measurements in tropical waters"
    ]

    session_id = "test_session_001"

    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")

        try:
            response = await agent.process_query(
                user_message=query,
                session_id=session_id
            )

            print(f"✅ Success: {response.success}")
            print(f"📊 Response length: {len(response.response_text)} characters")
            print(f"🔧 Tools called: {len(response.tool_calls_made)}")
            print(f"💡 Insights: {len(response.scientific_insights)}")
            print(f"❓ Follow-ups: {len(response.follow_up_suggestions)}")

            if response.tool_calls_made:
                print("🛠️  Tool calls:")
                for tool_call in response.tool_calls_made:
                    print(f"   - {tool_call['tool_name']}: {tool_call['success']}")

            # Show first few lines of response
            response_preview = response.response_text[:200] + "..." if len(response.response_text) > 200 else response.response_text
            print(f"📄 Response preview: {response_preview}")

        except Exception as e:
            print(f"❌ Query failed: {e}")

    return session_id


async def test_conversation_memory(agent: FloatChatAgent, session_id: str):
    """Test conversation memory and context."""
    print("\n🧠 Testing Conversation Memory...")

    # Get session summary
    summary = await agent.get_session_summary(session_id)
    if summary:
        print(f"✅ Session summary retrieved")
        print(f"📊 Total turns: {summary.get('total_turns', 0)}")
        print(f"🛠️  Total tool calls: {summary.get('total_tool_calls', 0)}")
        print(f"⏱️  Session duration: {summary.get('session_duration_minutes', 0):.1f} minutes")
        print(f"🌍 Locations discussed: {summary.get('unique_locations_queried', [])}")
        print(f"📚 Topics discussed: {summary.get('unique_topics_discussed', [])}")
    else:
        print("❌ Failed to retrieve session summary")


async def test_scientific_context():
    """Test scientific context capabilities."""
    print("\n🔬 Testing Scientific Context...")

    from sih25.AGENT.scientific_context import ScientificContext

    context = ScientificContext()

    test_queries = [
        "Show me temperature and salinity profiles in the equatorial Pacific",
        "Find dissolved oxygen measurements in the Arctic Ocean",
        "Get chlorophyll data from the Mediterranean Sea last summer"
    ]

    for query in test_queries:
        interpretation = context.interpret_query(query)

        print(f"\n📝 Query: {query}")
        print(f"🔍 Analysis type: {interpretation['analysis_type']}")
        print(f"📊 Parameters: {[p['name'] for p in interpretation['parameters_of_interest']]}")
        print(f"🌍 Spatial context: {interpretation['spatial_context']}")
        print(f"⏰ Temporal context: {interpretation['temporal_context']}")
        print(f"🛠️  Suggested tools: {interpretation['suggested_tools']}")


async def test_mcp_integration():
    """Test MCP tool client integration."""
    print("\n🔗 Testing MCP Integration...")

    from sih25.AGENT.mcp_client import MCPToolClient

    client = MCPToolClient("http://localhost:8000")

    try:
        success = await client.initialize()
        print(f"✅ MCP client initialization: {'SUCCESS' if success else 'FAILED'}")

        if success:
            tools = client.get_tool_descriptions()
            print(f"🛠️  Available tools: {list(tools.keys())}")

            # Test a simple tool call
            test_params = {
                "lat_min": 0,
                "lat_max": 10,
                "lon_min": -10,
                "lon_max": 10,
                "max_results": 5
            }

            print(f"\n🧪 Testing list_profiles tool...")
            result = await client.call_tool("list_profiles", test_params)
            print(f"✅ Tool call success: {result.success}")

            if not result.success:
                print(f"❌ Tool errors: {result.errors}")

        await client.close()

    except Exception as e:
        print(f"❌ MCP integration test failed: {e}")


async def main():
    """Run all tests."""
    print("🧪 FloatChatAgent Test Suite")
    print("=" * 50)

    # Test 1: Agent initialization
    agent = await test_agent_initialization()
    if not agent:
        print("❌ Cannot proceed without agent initialization")
        return

    # Test 2: Scientific context (independent test)
    await test_scientific_context()

    # Test 3: MCP integration (independent test)
    await test_mcp_integration()

    # Test 4: Natural language queries
    session_id = await test_natural_language_queries(agent)

    # Test 5: Conversation memory
    await test_conversation_memory(agent, session_id)

    # Cleanup
    await agent.close()

    print("\n🎉 Test suite completed!")


if __name__ == "__main__":
    # Check environment
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: No API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        print("Some tests may fail without proper API configuration.")
        print()

    asyncio.run(main())