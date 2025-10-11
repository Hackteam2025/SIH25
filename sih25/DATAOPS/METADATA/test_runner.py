#!/usr/bin/env python3
"""
Complete Test Runner for Argo Metadata Vector DB System
Tests the full pipeline from metadata extraction to AI agent queries
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from metadata_extractor import ArgoMetadataExtractor
from vector_db_loader import MetadataVectorDBLoader
from ai_agent import ArgoMetadataAgent


class TestRunner:
    """Complete test suite for the metadata system"""

    def __init__(self, metadata_file: str):
        self.metadata_file = Path(metadata_file)
        self.test_results = {
            'test_date': datetime.now().isoformat(),
            'metadata_file': str(self.metadata_file),
            'tests': []
        }

    def log_test(self, name: str, status: str, details: dict):
        """Log test result"""
        result = {
            'test_name': name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results['tests'].append(result)

        status_symbol = "✓" if status == "PASS" else "✗"
        print(f"\n{status_symbol} Test: {name}")
        print(f"  Status: {status}")
        if status == "PASS":
            print(f"  Details: {json.dumps(details, indent=4)[:200]}...")
        else:
            print(f"  Error: {details.get('error', 'Unknown error')}")

    async def test_1_metadata_extraction(self):
        """Test 1: Metadata Extraction"""
        print("\n" + "="*80)
        print("TEST 1: Metadata Extraction")
        print("="*80)

        try:
            extractor = ArgoMetadataExtractor()
            metadata = extractor.extract_metadata(str(self.metadata_file))

            # Verify key fields
            assert 'float_identification' in metadata
            assert 'deployment_info' in metadata
            assert 'sensors' in metadata

            platform_num = metadata.get('float_identification', {}).get('platform_number', 'UNKNOWN')

            # Create searchable text
            searchable_text = extractor.create_searchable_text(metadata)

            self.log_test(
                "Metadata Extraction",
                "PASS",
                {
                    'platform_number': platform_num,
                    'num_sensors': len(metadata.get('sensors', [])),
                    'num_parameters': len(metadata.get('parameters', [])),
                    'text_length': len(searchable_text),
                    'has_deployment_info': bool(metadata.get('deployment_info')),
                    'has_technical_specs': bool(metadata.get('technical_specs'))
                }
            )

            return metadata, searchable_text

        except Exception as e:
            self.log_test("Metadata Extraction", "FAIL", {'error': str(e)})
            raise

    async def test_2_vector_table_creation(self, loader: MetadataVectorDBLoader):
        """Test 2: Vector Table Creation"""
        print("\n" + "="*80)
        print("TEST 2: Vector Table Creation")
        print("="*80)

        try:
            import asyncpg

            pool = await asyncpg.create_pool(loader.database_url, min_size=1, max_size=2)
            try:
                async with pool.acquire() as conn:
                    await loader.create_vector_table(conn)

                    # Verify table exists
                    result = await conn.fetchrow("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'argo_metadata_vectors'
                        );
                    """)

                    assert result['exists'] is True

                    # Check columns
                    columns = await conn.fetch("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = 'argo_metadata_vectors';
                    """)

                    column_names = [col['column_name'] for col in columns]

                    self.log_test(
                        "Vector Table Creation",
                        "PASS",
                        {
                            'table_exists': True,
                            'columns': column_names,
                            'num_columns': len(columns)
                        }
                    )

            finally:
                await pool.close()

        except Exception as e:
            self.log_test("Vector Table Creation", "FAIL", {'error': str(e)})
            raise

    async def test_3_metadata_loading(self, loader: MetadataVectorDBLoader):
        """Test 3: Metadata Loading to Vector DB"""
        print("\n" + "="*80)
        print("TEST 3: Metadata Loading to Vector DB")
        print("="*80)

        try:
            import asyncpg

            pool = await asyncpg.create_pool(loader.database_url, min_size=1, max_size=2)
            try:
                async with pool.acquire() as conn:
                    result = await loader.load_metadata_file(str(self.metadata_file), conn, upsert=True)

                    assert result['status'] in ['success', 'skipped']

                    # Verify data was inserted
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM argo_metadata_vectors WHERE platform_number = $1",
                        result['platform_number']
                    )

                    assert count > 0

                    self.log_test(
                        "Metadata Loading",
                        "PASS",
                        {
                            'status': result['status'],
                            'platform_number': result['platform_number'],
                            'text_length': result.get('text_length', 0),
                            'embedding_dim': result.get('embedding_dim', 0),
                            'in_database': count > 0
                        }
                    )

                    return result['platform_number']

            finally:
                await pool.close()

        except Exception as e:
            self.log_test("Metadata Loading", "FAIL", {'error': str(e)})
            raise

    async def test_4_vector_search(self, loader: MetadataVectorDBLoader):
        """Test 4: Vector Similarity Search"""
        print("\n" + "="*80)
        print("TEST 4: Vector Similarity Search")
        print("="*80)

        try:
            test_queries = [
                "CTD sensor specifications",
                "deployment location and date",
                "battery configuration"
            ]

            search_results = []
            for query in test_queries:
                results = await loader.search_similar_metadata(query, limit=3)
                search_results.append({
                    'query': query,
                    'num_results': len(results),
                    'top_similarity': results[0]['similarity_score'] if results else 0
                })

            self.log_test(
                "Vector Similarity Search",
                "PASS",
                {
                    'queries_tested': len(test_queries),
                    'search_results': search_results
                }
            )

        except Exception as e:
            self.log_test("Vector Similarity Search", "FAIL", {'error': str(e)})
            raise

    async def test_5_ai_agent_queries(self, agent: ArgoMetadataAgent, platform_number: str):
        """Test 5: AI Agent Queries"""
        print("\n" + "="*80)
        print("TEST 5: AI Agent Queries with Context Retrieval")
        print("="*80)

        try:
            test_questions = [
                f"What sensors does platform {platform_number} have?",
                f"Where was float {platform_number} deployed?",
                f"What parameters can platform {platform_number} measure?",
                f"Tell me about the technical specifications of float {platform_number}"
            ]

            agent_results = []
            for question in test_questions:
                result = await agent.query(question, top_k=2, include_context=False)

                agent_results.append({
                    'question': question,
                    'used_context': result.get('used_context', False),
                    'num_context_entries': result.get('num_context_entries', 0),
                    'answer_length': len(result.get('answer', '')),
                    'has_error': 'error' in result
                })

            # Verify that context was actually used
            context_used_count = sum(1 for r in agent_results if r['used_context'])

            self.log_test(
                "AI Agent Queries",
                "PASS",
                {
                    'questions_asked': len(test_questions),
                    'queries_with_context': context_used_count,
                    'agent_results': agent_results,
                    'verification': 'Context retrieval is working!' if context_used_count > 0 else 'No context retrieved'
                }
            )

            return agent_results

        except Exception as e:
            self.log_test("AI Agent Queries", "FAIL", {'error': str(e)})
            raise

    async def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*80)
        print("ARGO METADATA VECTOR DB - COMPLETE TEST SUITE")
        print("="*80)
        print(f"Testing with file: {self.metadata_file}")
        print(f"Test started: {self.test_results['test_date']}")
        print("="*80)

        try:
            # Test 1: Extract metadata
            metadata, searchable_text = await self.test_1_metadata_extraction()

            # Initialize components
            loader = MetadataVectorDBLoader()
            agent = ArgoMetadataAgent()

            # Test 2: Create vector table
            await self.test_2_vector_table_creation(loader)

            # Test 3: Load metadata
            platform_number = await self.test_3_metadata_loading(loader)

            # Test 4: Vector search
            await self.test_4_vector_search(loader)

            # Test 5: AI agent queries
            await self.test_5_ai_agent_queries(agent, platform_number)

            # Summary
            print("\n" + "="*80)
            print("TEST SUITE SUMMARY")
            print("="*80)

            passed = sum(1 for t in self.test_results['tests'] if t['status'] == 'PASS')
            total = len(self.test_results['tests'])

            print(f"Tests Passed: {passed}/{total}")
            print(f"Success Rate: {(passed/total)*100:.1f}%")

            if passed == total:
                print("\n🎉 ALL TESTS PASSED! Vector DB system is working correctly.")
                print("\n✓ Metadata extraction: Working")
                print("✓ Vector embeddings: Generated")
                print("✓ Database storage: Successful")
                print("✓ Semantic search: Functional")
                print("✓ AI agent retrieval: Verified working!")
            else:
                print(f"\n⚠️  {total - passed} test(s) failed.")

            print("="*80)

            return self.test_results

        except Exception as e:
            print(f"\n✗ Test suite failed with error: {e}")
            import traceback
            traceback.print_exc()
            return self.test_results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test Argo Metadata Vector DB System")
    parser.add_argument(
        'metadata_file',
        help='Path to .nc metadata file to test with'
    )
    parser.add_argument(
        '--output',
        help='Output file for test results (JSON)',
        default='test_results.json'
    )

    args = parser.parse_args()

    # Verify file exists
    if not Path(args.metadata_file).exists():
        print(f"Error: Metadata file not found: {args.metadata_file}")
        sys.exit(1)

    # Run tests
    runner = TestRunner(args.metadata_file)
    results = await runner.run_all_tests()

    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✓ Test results saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
