#!/usr/bin/env python3
"""
FloatChatAgent Startup Script

Simple script to start the AGNO-based AI agent for development and testing.
"""

import asyncio
import logging
import os
from typing import Optional

from sih25.AGENT.float_chat_agent import FloatChatAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def interactive_chat():
    """Start an interactive chat session with the agent."""
    print("🌊 FloatChat Agent - Interactive Session")
    print("=" * 50)
    print("Ask me about ARGO oceanographic data!")
    print("Type 'quit' to exit, 'help' for examples")
    print()

    # Initialize agent
    print("🔧 Initializing agent...")
    agent = FloatChatAgent(
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8000"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        model_name=os.getenv("MODEL_NAME", "gpt-4"),
        api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    )

    success = await agent.initialize()
    if not success:
        print("❌ Failed to initialize agent")
        return

    print("✅ Agent ready!")
    print()

    session_id = "interactive_session"

    try:
        while True:
            user_input = input("🤔 You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
            elif user_input.lower() == 'help':
                show_help()
                continue
            elif user_input.lower() == 'summary':
                summary = await agent.get_session_summary(session_id)
                if summary:
                    print(f"📊 Session Summary:")
                    print(f"   Turns: {summary.get('total_turns', 0)}")
                    print(f"   Duration: {summary.get('session_duration_minutes', 0):.1f} min")
                    print(f"   Topics: {', '.join(summary.get('unique_topics_discussed', []))}")
                else:
                    print("No session data yet")
                continue
            elif not user_input:
                continue

            print("🤖 Agent: Processing your query...")

            try:
                response = await agent.process_query(
                    user_message=user_input,
                    session_id=session_id
                )

                if response.success:
                    print(f"🌊 Agent: {response.response_text}")

                    if response.scientific_insights:
                        print(f"\n💡 Scientific Insights:")
                        for insight in response.scientific_insights:
                            print(f"   • {insight}")

                    if response.follow_up_suggestions:
                        print(f"\n❓ Follow-up Questions:")
                        for suggestion in response.follow_up_suggestions:
                            print(f"   • {suggestion}")

                    if response.tool_calls_made:
                        print(f"\n🛠️  Data sources: {len(response.tool_calls_made)} tools used")

                else:
                    print(f"❌ Agent: {response.response_text}")

            except Exception as e:
                print(f"❌ Error: {e}")

            print()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

    finally:
        await agent.close()


def show_help():
    """Show help information."""
    print("\n📚 Example Queries:")
    print("• 'Show me temperature profiles near the equator'")
    print("• 'Find ARGO floats within 100km of latitude 40, longitude -70'")
    print("• 'What's the average salinity in recent measurements?'")
    print("• 'Get dissolved oxygen data from the North Atlantic'")
    print("• 'Show me chlorophyll measurements in tropical waters'")
    print("\n🎮 Commands:")
    print("• 'help' - Show this help")
    print("• 'summary' - Show session summary")
    print("• 'quit' - Exit the session")
    print()


async def demo_queries():
    """Run demo queries for testing."""
    print("🎬 FloatChat Agent - Demo Mode")
    print("=" * 50)

    agent = FloatChatAgent()
    success = await agent.initialize()

    if not success:
        print("❌ Failed to initialize agent")
        return

    demo_queries = [
        "Show me recent temperature profiles in the equatorial Pacific",
        "Find ARGO floats near the coordinates 35°N, 140°E",
        "What can you tell me about salinity measurements in the Mediterranean?",
        "Get me some dissolved oxygen data from the Arctic Ocean"
    ]

    session_id = "demo_session"

    for i, query in enumerate(demo_queries, 1):
        print(f"\n🎯 Demo Query {i}: {query}")
        print("-" * 40)

        try:
            response = await agent.process_query(query, session_id)

            if response.success:
                print(f"🌊 Response: {response.response_text[:300]}...")

                if response.tool_calls_made:
                    print(f"🛠️  Tools used: {[tc['tool_name'] for tc in response.tool_calls_made]}")

                if response.scientific_insights:
                    print(f"💡 Key insight: {response.scientific_insights[0]}")

            else:
                print(f"❌ Failed: {response.response_text}")

        except Exception as e:
            print(f"❌ Error: {e}")

        # Small delay between queries
        await asyncio.sleep(1)

    await agent.close()
    print("\n🎉 Demo completed!")


async def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        await demo_queries()
    else:
        await interactive_chat()


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: No API keys found!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-key-here'")
        print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")