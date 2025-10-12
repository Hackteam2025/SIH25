#!/usr/bin/env python3
"""
AI Agent with Vector DB Retrieval
Queries Argo metadata using semantic search and provides contextual responses
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings("ignore")

from mistralai import Mistral

# Import vector DB loader
try:
    from vector_db_loader import MetadataVectorDBLoader
except ImportError:
    from .vector_db_loader import MetadataVectorDBLoader


class ArgoMetadataAgent:
    """AI Agent that retrieves and queries Argo float metadata"""

    def __init__(
        self,
        mistral_api_key: Optional[str] = None,
        database_url: Optional[str] = None,
        model_name: str = "mistral-large-latest"
    ):
        """
        Initialize AI agent

        Args:
            mistral_api_key: Mistral API key
            database_url: PostgreSQL connection string
            model_name: Mistral model to use for chat
        """
        self.mistral_api_key = mistral_api_key or os.getenv('MISTRAL_API_KEY')
        self.database_url = database_url or os.getenv('DATABASE_URL')

        if not self.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY must be provided or set in environment")

        self.mistral_client = Mistral(api_key=self.mistral_api_key)
        self.vector_loader = MetadataVectorDBLoader(
            database_url=self.database_url,
            mistral_api_key=self.mistral_api_key
        )
        self.model_name = model_name

        self.system_prompt = """You are an expert assistant for Argo oceanographic float data.
You have access to detailed metadata about Argo floats including their deployment information,
technical specifications, sensors, and mission details.

When answering questions:
1. Use the retrieved metadata context to provide accurate, detailed information
2. If specific information is not in the context, clearly state that
3. Explain technical terms for clarity
4. Provide platform numbers when referencing specific floats
5. Be precise about dates, locations, and technical specifications

Always cite the platform number when providing information about specific floats."""

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 3,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant metadata context for a query

        Args:
            query: User query
            top_k: Number of results to retrieve
            similarity_threshold: Minimum similarity score

        Returns:
            Dictionary with retrieved context and metadata
        """
        print(f"🔍 Retrieving context for: '{query}'")

        # Search vector database
        results = await self.vector_loader.search_similar_metadata(
            query=query,
            limit=top_k,
            similarity_threshold=similarity_threshold
        )

        if not results:
            return {
                'found_context': False,
                'context_text': "",
                'results': []
            }

        # Format context for LLM
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"=== Float {i}: Platform {result['platform_number']} ===")
            context_parts.append(f"Similarity Score: {result['similarity_score']:.3f}")
            context_parts.append("")
            context_parts.append(result['searchable_text'])
            context_parts.append("")

        context_text = "\n".join(context_parts)

        print(f"✓ Retrieved {len(results)} relevant context entries")

        return {
            'found_context': True,
            'context_text': context_text,
            'results': results,
            'num_results': len(results)
        }

    async def query(
        self,
        question: str,
        top_k: int = 3,
        similarity_threshold: float = 0.5,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Query the AI agent with context retrieval

        Args:
            question: User question
            top_k: Number of context entries to retrieve
            similarity_threshold: Minimum similarity for context
            include_context: Whether to include retrieved context in response

        Returns:
            Dictionary with answer and metadata
        """
        print("\n" + "="*80)
        print("ARGO METADATA AGENT")
        print("="*80)
        print(f"Question: {question}\n")

        # Retrieve context
        context_data = await self.retrieve_context(
            query=question,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        # Construct messages
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        if context_data['found_context']:
            user_message = f"""Context from Argo Float Metadata Database:

{context_data['context_text']}

---

User Question: {question}

Please answer the question based on the provided context. If the context doesn't contain
enough information to fully answer the question, clearly state what information is missing."""
        else:
            user_message = f"""No specific float metadata was found matching the query.

User Question: {question}

Please provide a general answer based on your knowledge of Argo floats, but note that
specific metadata from the database was not available."""

        messages.append({"role": "user", "content": user_message})

        # Get response from LLM
        print("🤖 Generating response...")
        try:
            response = self.mistral_client.chat.complete(
                model=self.model_name,
                messages=messages
            )

            answer = response.choices[0].message.content

            print("\n" + "-"*80)
            print("ANSWER:")
            print("-"*80)
            print(answer)
            print("="*80)

            result = {
                'question': question,
                'answer': answer,
                'used_context': context_data['found_context'],
                'num_context_entries': context_data.get('num_results', 0),
                'model': self.model_name
            }

            if include_context:
                result['context_results'] = context_data.get('results', [])

            return result

        except Exception as e:
            print(f"✗ Error generating response: {e}")
            return {
                'question': question,
                'error': str(e),
                'used_context': False
            }

    async def interactive_session(self):
        """Run an interactive query session"""
        print("\n" + "="*80)
        print("ARGO METADATA AGENT - Interactive Session")
        print("="*80)
        print("Ask questions about Argo floats. Type 'exit' or 'quit' to end.\n")

        while True:
            try:
                question = input("You: ").strip()

                if question.lower() in ['exit', 'quit', 'q']:
                    print("\nGoodbye!")
                    break

                if not question:
                    continue

                await self.query(question, include_context=False)
                print()

            except KeyboardInterrupt:
                print("\n\nSession interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")


async def main():
    """Main function for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Query Argo metadata using AI agent")
    parser.add_argument(
        'command',
        choices=['query', 'interactive', 'test'],
        help='Command to execute'
    )
    parser.add_argument(
        '--question',
        help='Question to ask (for query command)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=3,
        help='Number of context entries to retrieve'
    )
    parser.add_argument(
        '--model',
        default='mistral-large-latest',
        help='Mistral model to use'
    )
    parser.add_argument(
        '--output',
        help='Output file for results (JSON format)'
    )

    args = parser.parse_args()

    # Initialize agent
    print("Initializing Argo Metadata Agent...")
    agent = ArgoMetadataAgent(model_name=args.model)

    if args.command == 'query':
        if not args.question:
            print("Error: --question argument required for query command")
            return

        result = await agent.query(args.question, top_k=args.top_k)

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, indent=2, fp=f, default=str)
            print(f"\n✓ Results saved to: {args.output}")

    elif args.command == 'interactive':
        await agent.interactive_session()

    elif args.command == 'test':
        print("\n" + "="*80)
        print("RUNNING TEST QUERIES")
        print("="*80)

        test_questions = [
            "What sensors does platform 1900121 have?",
            "Tell me about the deployment location of float 1900121",
            "What parameters can float 1900121 measure?",
            "What is the firmware version of the float?"
        ]

        results = []
        for question in test_questions:
            result = await agent.query(question, top_k=2, include_context=False)
            results.append(result)
            print("\n")

        # Save test results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, indent=2, fp=f, default=str)
            print(f"✓ Test results saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
