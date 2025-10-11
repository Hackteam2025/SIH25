#!/usr/bin/env python3
"""
Vector Database Loader for Argo Metadata
Loads metadata into Supabase/PostgreSQL with pgvector for semantic search
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings("ignore")

import asyncpg
from mistralai import Mistral
from datetime import datetime

# Import metadata extractor
try:
    from metadata_extractor import ArgoMetadataExtractor
except ImportError:
    from .metadata_extractor import ArgoMetadataExtractor


class MetadataVectorDBLoader:
    """Load Argo metadata into vector database with embeddings"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        mistral_api_key: Optional[str] = None
    ):
        """
        Initialize vector DB loader

        Args:
            database_url: PostgreSQL connection string
            mistral_api_key: Mistral API key for embeddings
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.mistral_api_key = mistral_api_key or os.getenv('MISTRAL_API_KEY')

        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided or set in environment")

        if not self.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY must be provided or set in environment")

        self.mistral_client = Mistral(api_key=self.mistral_api_key)
        self.extractor = ArgoMetadataExtractor()
        self.embedding_model = "mistral-embed"
        self.embedding_dim = 1024  # Mistral embeddings dimension

    async def create_vector_table(self, conn: asyncpg.Connection):
        """Create the metadata vector table with pgvector extension"""

        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Create metadata table
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS argo_metadata_vectors (
            id SERIAL PRIMARY KEY,
            platform_number VARCHAR(255) NOT NULL,
            source_file VARCHAR(500) NOT NULL,
            metadata JSONB NOT NULL,
            searchable_text TEXT NOT NULL,
            embedding vector({self.embedding_dim}),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        await conn.execute(create_table_query)

        # Create indexes for better performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_argo_metadata_platform
            ON argo_metadata_vectors(platform_number);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_argo_metadata_embedding
            ON argo_metadata_vectors USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_argo_metadata_text
            ON argo_metadata_vectors USING gin(to_tsvector('english', searchable_text));
        """)

        print("✓ Vector table created successfully with indexes")

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Mistral API

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        try:
            response = self.mistral_client.embeddings.create(
                model=self.embedding_model,
                inputs=[text]
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise

    async def load_metadata_file(
        self,
        nc_file_path: str,
        conn: asyncpg.Connection,
        upsert: bool = True
    ) -> Dict[str, Any]:
        """
        Load a single metadata file into the vector database

        Args:
            nc_file_path: Path to .nc metadata file
            conn: Database connection
            upsert: Whether to update if exists

        Returns:
            Dictionary with loading results
        """
        print(f"\n📄 Processing: {nc_file_path}")

        # Extract metadata
        metadata = self.extractor.extract_metadata(nc_file_path)
        searchable_text = self.extractor.create_searchable_text(metadata)

        # Generate embedding
        print("  ⚙️  Generating embedding...")
        embedding = await self.generate_embedding(searchable_text)

        # Get platform number
        platform_number = metadata.get('float_identification', {}).get('platform_number', 'UNKNOWN')
        source_file = metadata.get('source_file', Path(nc_file_path).name)

        # Insert or update in database
        if upsert:
            query = """
            INSERT INTO argo_metadata_vectors (platform_number, source_file, metadata, searchable_text, embedding)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (platform_number) DO UPDATE SET
                source_file = EXCLUDED.source_file,
                metadata = EXCLUDED.metadata,
                searchable_text = EXCLUDED.searchable_text,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            RETURNING id;
            """
        else:
            # Check if exists
            existing = await conn.fetchrow(
                "SELECT id FROM argo_metadata_vectors WHERE platform_number = $1",
                platform_number
            )
            if existing:
                print(f"  ⚠️  Platform {platform_number} already exists. Skipping.")
                return {
                    'status': 'skipped',
                    'platform_number': platform_number,
                    'reason': 'already_exists'
                }

            query = """
            INSERT INTO argo_metadata_vectors (platform_number, source_file, metadata, searchable_text, embedding)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id;
            """

        try:
            result = await conn.fetchrow(
                query,
                platform_number,
                source_file,
                json.dumps(metadata),
                searchable_text,
                embedding
            )

            print(f"  ✓ Loaded platform {platform_number} (ID: {result['id']})")

            return {
                'status': 'success',
                'id': result['id'],
                'platform_number': platform_number,
                'source_file': source_file,
                'text_length': len(searchable_text),
                'embedding_dim': len(embedding)
            }

        except Exception as e:
            print(f"  ✗ Error loading metadata: {e}")
            return {
                'status': 'error',
                'platform_number': platform_number,
                'error': str(e)
            }

    async def load_metadata_directory(
        self,
        directory: str,
        pattern: str = "*_meta.nc",
        upsert: bool = True
    ) -> Dict[str, Any]:
        """
        Load all metadata files from a directory

        Args:
            directory: Directory containing .nc metadata files
            pattern: Glob pattern for files
            upsert: Whether to update existing entries

        Returns:
            Summary of loading results
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        metadata_files = list(dir_path.glob(pattern))

        if not metadata_files:
            print(f"⚠️  No metadata files found matching pattern: {pattern}")
            return {
                'status': 'no_files',
                'directory': str(directory),
                'pattern': pattern
            }

        print(f"📁 Found {len(metadata_files)} metadata files")

        results = {
            'total_files': len(metadata_files),
            'successful': 0,
            'skipped': 0,
            'errors': 0,
            'details': []
        }

        # Create connection pool
        pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=5)

        try:
            async with pool.acquire() as conn:
                # Ensure table exists
                await self.create_vector_table(conn)

                # Process each file
                for nc_file in metadata_files:
                    result = await self.load_metadata_file(str(nc_file), conn, upsert)
                    results['details'].append(result)

                    if result['status'] == 'success':
                        results['successful'] += 1
                    elif result['status'] == 'skipped':
                        results['skipped'] += 1
                    elif result['status'] == 'error':
                        results['errors'] += 1

        finally:
            await pool.close()

        print("\n" + "="*80)
        print(f"✓ Loading complete!")
        print(f"  - Total files: {results['total_files']}")
        print(f"  - Successful: {results['successful']}")
        print(f"  - Skipped: {results['skipped']}")
        print(f"  - Errors: {results['errors']}")
        print("="*80)

        return results

    async def search_similar_metadata(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar metadata using vector similarity

        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of matching metadata entries with similarity scores
        """
        print(f"\n🔍 Searching for: {query}")

        # Generate query embedding
        query_embedding = await self.generate_embedding(query)

        # Create connection
        pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=2)

        try:
            async with pool.acquire() as conn:
                # Perform vector similarity search
                search_query = """
                SELECT
                    platform_number,
                    source_file,
                    metadata,
                    searchable_text,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM argo_metadata_vectors
                WHERE 1 - (embedding <=> $1::vector) > $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3;
                """

                results = await conn.fetch(
                    search_query,
                    query_embedding,
                    similarity_threshold,
                    limit
                )

                # Format results
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'platform_number': row['platform_number'],
                        'source_file': row['source_file'],
                        'metadata': json.loads(row['metadata']),
                        'searchable_text': row['searchable_text'],
                        'similarity_score': float(row['similarity'])
                    })

                print(f"  ✓ Found {len(formatted_results)} similar entries")
                return formatted_results

        finally:
            await pool.close()


async def main():
    """Main function for CLI usage"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Load Argo metadata into vector database")
    parser.add_argument(
        'command',
        choices=['load-file', 'load-dir', 'search', 'create-table'],
        help='Command to execute'
    )
    parser.add_argument(
        'path',
        nargs='?',
        help='Path to file or directory'
    )
    parser.add_argument(
        '--query',
        help='Search query (for search command)'
    )
    parser.add_argument(
        '--pattern',
        default='*_meta.nc',
        help='File pattern for directory loading'
    )
    parser.add_argument(
        '--upsert',
        action='store_true',
        default=True,
        help='Update existing entries'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=5,
        help='Number of search results'
    )

    args = parser.parse_args()

    # Initialize loader
    loader = MetadataVectorDBLoader()

    if args.command == 'create-table':
        print("Creating vector table...")
        pool = await asyncpg.create_pool(loader.database_url, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await loader.create_vector_table(conn)
        finally:
            await pool.close()

    elif args.command == 'load-file':
        if not args.path:
            print("Error: path argument required for load-file command")
            sys.exit(1)

        pool = await asyncpg.create_pool(loader.database_url, min_size=1, max_size=2)
        try:
            async with pool.acquire() as conn:
                await loader.create_vector_table(conn)
                result = await loader.load_metadata_file(args.path, conn, args.upsert)
                print(json.dumps(result, indent=2))
        finally:
            await pool.close()

    elif args.command == 'load-dir':
        if not args.path:
            print("Error: path argument required for load-dir command")
            sys.exit(1)

        result = await loader.load_metadata_directory(args.path, args.pattern, args.upsert)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == 'search':
        if not args.query:
            print("Error: --query argument required for search command")
            sys.exit(1)

        results = await loader.search_similar_metadata(args.query, args.limit)

        print("\n" + "="*80)
        print("SEARCH RESULTS")
        print("="*80)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Platform: {result['platform_number']} (Similarity: {result['similarity_score']:.3f})")
            print(f"   Source: {result['source_file']}")
            print(f"\n   {result['searchable_text'][:300]}...")
            print("-"*80)


if __name__ == "__main__":
    asyncio.run(main())
