#!/usr/bin/env python3
"""
Database Connection Module for Supabase PostgreSQL
Handles connection pooling, health checks, and retry logic
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator
from urllib.parse import urlparse
from pathlib import Path

import asyncpg
from prefect import get_run_logger

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env file in project root and parent directories
    env_file = None
    current_dir = Path(__file__).parent

    # Go up to find the project root (look for .env file)
    for i in range(5):  # Search up to 5 levels up
        potential_env = current_dir / '.env'
        if potential_env.exists():
            env_file = potential_env
            break
        current_dir = current_dir.parent

    if env_file:
        load_dotenv(env_file)
        print(f"Loaded environment variables from: {env_file}")
    else:
        print("No .env file found, using system environment variables")
except ImportError:
    print("python-dotenv not available, using system environment variables")


class DatabaseConfig:
    """Database configuration from environment variables"""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Parse URL components for connection pool
        parsed = urlparse(self.database_url)
        self.host = parsed.hostname
        self.port = parsed.port or 5432
        self.database = parsed.path.lstrip('/')
        self.user = parsed.username
        self.password = parsed.password

        # Connection pool settings
        self.min_connections = int(os.getenv("DB_MIN_CONNECTIONS", "2"))
        self.max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "10"))
        self.max_inactive_connection_lifetime = float(os.getenv("DB_MAX_INACTIVE_LIFETIME", "300.0"))


class DatabaseManager:
    """Manages PostgreSQL database connections and operations"""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._pool: Optional[asyncpg.Pool] = None
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            try:
                self._logger = get_run_logger()
            except:
                self._logger = logging.getLogger(__name__)
        return self._logger

    async def initialize(self) -> None:
        """Initialize database connection pool"""
        try:
            self.logger.info("Initializing database connection pool...")

            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                max_inactive_connection_lifetime=self.config.max_inactive_connection_lifetime,
                command_timeout=60,
                server_settings={
                    'jit': 'off'  # Disable JIT for better connection stability
                }
            )

            # Test connection
            await self.health_check()
            self.logger.info(f"Database pool initialized with {self.config.min_connections}-{self.config.max_connections} connections")

        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {e}")
            raise

    async def close(self) -> None:
        """Close database connection pool"""
        if self._pool:
            self.logger.info("Closing database connection pool...")
            await self._pool.close()
            self._pool = None

    async def health_check(self) -> bool:
        """Check database connectivity"""
        if not self._pool:
            return False

        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection from the pool"""
        if not self._pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection with transaction"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

    async def execute_with_retry(self, query: str, *args, max_retries: int = 3) -> Any:
        """Execute query with retry logic"""
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with self.get_connection() as conn:
                    return await conn.execute(query, *args)
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Query execution attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff

        raise last_exception

    async def fetch_with_retry(self, query: str, *args, max_retries: int = 3) -> Any:
        """Fetch query results with retry logic"""
        last_exception = None

        for attempt in range(max_retries):
            try:
                async with self.get_connection() as conn:
                    return await conn.fetch(query, *args)
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Query fetch attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff

        raise last_exception

    async def create_tables_if_not_exist(self) -> None:
        """Create the three-table schema if it doesn't exist"""
        create_floats_table = """
        CREATE TABLE IF NOT EXISTS floats (
            wmo_id VARCHAR PRIMARY KEY,
            deployment_info JSONB,
            pi_details JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """

        create_profiles_table = """
        CREATE TABLE IF NOT EXISTS profiles (
            profile_id VARCHAR PRIMARY KEY,
            float_wmo_id VARCHAR REFERENCES floats(wmo_id),
            timestamp TIMESTAMP,
            latitude FLOAT,
            longitude FLOAT,
            position_qc INTEGER,
            data_mode CHAR(1),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """

        create_observations_table = """
        CREATE TABLE IF NOT EXISTS observations (
            observation_id SERIAL PRIMARY KEY,
            profile_id VARCHAR REFERENCES profiles(profile_id),
            depth FLOAT,
            parameter VARCHAR,
            value FLOAT,
            qc_flag INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """

        # Create indexes for better query performance
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_profiles_float_wmo_id ON profiles(float_wmo_id);",
            "CREATE INDEX IF NOT EXISTS idx_profiles_timestamp ON profiles(timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_observations_profile_id ON observations(profile_id);",
            "CREATE INDEX IF NOT EXISTS idx_observations_parameter ON observations(parameter);",
            "CREATE INDEX IF NOT EXISTS idx_observations_depth ON observations(depth);"
        ]

        try:
            async with self.get_transaction() as conn:
                self.logger.info("Creating database tables if they don't exist...")

                await conn.execute(create_floats_table)
                await conn.execute(create_profiles_table)
                await conn.execute(create_observations_table)

                for index_sql in create_indexes:
                    await conn.execute(index_sql)

                self.logger.info("Database schema creation completed")

        except Exception as e:
            self.logger.error(f"Failed to create database schema: {e}")
            raise


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance"""
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()

    return _db_manager


async def close_db_manager() -> None:
    """Close global database manager"""
    global _db_manager

    if _db_manager:
        await _db_manager.close()
        _db_manager = None


# Context manager for automatic initialization and cleanup
@asynccontextmanager
async def database_context() -> AsyncGenerator[DatabaseManager, None]:
    """Context manager for database operations"""
    manager = await get_db_manager()
    try:
        yield manager
    finally:
        # Don't close here as it might be used by other tasks
        pass