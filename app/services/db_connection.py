"""
Database connection manager for PostgreSQL using asyncpg.
Manages connection pool lifecycle, health checks, and retry logic.
"""

import asyncio
import logging
from typing import Optional
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Manages asyncpg connection pool with lifecycle management and retry logic.
    
    Responsibilities:
    - Initialize connection pool on startup
    - Manage pool lifecycle (startup, shutdown, health checks)
    - Implement retry logic with exponential backoff
    - Validate database connectivity
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self._pool: Optional[asyncpg.Pool] = None
        self._is_available: bool = False
        self._retry_delays = [0.5, 1.0, 2.0]  # 500ms, 1s, 2s
    
    async def initialize(self) -> None:
        """
        Initialize the connection pool with retry logic.
        
        Attempts to establish connection pool with exponential backoff.
        Logs all connection attempts and errors.
        
        Raises:
            Exception: If all connection attempts fail after retries
        """
        for attempt, delay in enumerate(self._retry_delays, start=1):
            try:
                if attempt > 1:
                    logger.info(f"Retrying database connection (attempt {attempt}/{len(self._retry_delays)}) after {delay*1000}ms delay")
                    await asyncio.sleep(delay)
                
                logger.info(f"Attempting to connect to database at {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
                
                # Use asyncio.wait_for to enforce timeout
                self._pool = await asyncio.wait_for(
                    asyncpg.create_pool(
                        host=settings.DB_HOST,
                        port=settings.DB_PORT,
                        database=settings.DB_NAME,
                        user=settings.DB_USER,
                        password=settings.DB_PASSWORD,
                        min_size=1,  # Start with 1 connection to speed up initialization
                        max_size=settings.DB_MAX_POOL_SIZE,
                        timeout=30,  # Pool acquisition timeout
                        command_timeout=settings.DB_QUERY_TIMEOUT / 1000,  # Convert ms to seconds
                        ssl='require' if settings.DB_SSL_MODE == 'require' else None,
                        statement_cache_size=0  # Required for pgbouncer compatibility
                    ),
                    timeout=30.0  # 30 second timeout for pool creation
                )
                
                # Test the connection
                async with self._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                
                self._is_available = True
                logger.info(f"Database connection pool initialized successfully (min=1, max={settings.DB_MAX_POOL_SIZE})")
                return
                
            except asyncio.TimeoutError:
                logger.error(f"Database connection attempt {attempt} failed: Connection timeout after 30 seconds")
                
                if attempt == len(self._retry_delays):
                    # All retries exhausted
                    self._is_available = False
                    logger.error("All database connection retries exhausted. Service will operate without database matching.")
                    # Don't raise - allow service to start without database
                    return
                    
            except (asyncpg.PostgresConnectionError, asyncpg.PostgresError, OSError) as e:
                logger.error(f"Database connection attempt {attempt} failed: {type(e).__name__}: {str(e)}")
                
                if attempt == len(self._retry_delays):
                    # All retries exhausted
                    self._is_available = False
                    logger.error("All database connection retries exhausted. Service will operate without database matching.")
                    # Don't raise - allow service to start without database
                    return
    
    async def close(self) -> None:
        """
        Close the connection pool and cleanup resources.
        """
        if self._pool:
            try:
                await self._pool.close()
                logger.info("Database connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connection pool: {e}")
            finally:
                self._pool = None
                self._is_available = False
    
    async def get_connection(self) -> asyncpg.Connection:
        """
        Acquire a connection from the pool.
        
        Returns:
            asyncpg.Connection: Database connection from the pool
            
        Raises:
            RuntimeError: If pool is not initialized or unavailable
        """
        if not self._pool or not self._is_available:
            raise RuntimeError("Database connection pool is not available")
        
        return await self._pool.acquire()
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the database connection.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        if not self._pool or not self._is_available:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if the database connection is available.
        
        Returns:
            bool: True if database is available, False otherwise
        """
        return self._is_available and self._pool is not None
    
    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        """
        Get the connection pool instance.
        
        Returns:
            Optional[asyncpg.Pool]: The connection pool or None if not initialized
        """
        return self._pool


# Global connection manager instance
db_manager = DatabaseConnectionManager()
