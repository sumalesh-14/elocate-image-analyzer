"""
Database connection manager for PostgreSQL using asyncpg with psycopg2 fallback.
Manages connection pool lifecycle, health checks, and retry logic.
"""

import asyncio
import logging
from typing import Optional
import asyncpg
import psycopg2
from psycopg2 import pool
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
        self._psycopg_pool: Optional[pool.ThreadedConnectionPool] = None
        self._use_psycopg = False
        self._is_available: bool = False
        self._retry_delays = [0.5, 1.0, 2.0]  # 500ms, 1s, 2s
    
    async def initialize(self) -> None:
        """
        Initialize the connection pool with retry logic.
        Tries asyncpg first, falls back to psycopg2 if network issues occur.
        
        Attempts to establish connection pool with exponential backoff.
        Logs all connection attempts and errors.
        
        Raises:
            Exception: If all connection attempts fail after retries
        """
        # First try asyncpg
        asyncpg_success = await self._try_asyncpg()
        
        if asyncpg_success:
            logger.info("Using asyncpg for database connections")
            return
        
        # If asyncpg fails with network error, try psycopg2
        logger.info("asyncpg failed, trying psycopg2 as fallback")
        psycopg_success = await self._try_psycopg()
        
        if psycopg_success:
            logger.info("Using psycopg2 for database connections")
            return
        
        # Both failed
        self._is_available = False
        logger.error("All database connection methods exhausted. Service will operate without database matching.")
    
    async def _try_asyncpg(self) -> bool:
        """Try to connect using asyncpg."""
        for attempt, delay in enumerate(self._retry_delays, start=1):
            try:
                if attempt > 1:
                    logger.info(f"Retrying database connection (attempt {attempt}/{len(self._retry_delays)}) after {delay*1000}ms delay")
                    await asyncio.sleep(delay)
                
                logger.info(f"Attempting to connect to database at {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
                
                # Connection parameters for asyncpg
                conn_params = {
                    'host': settings.DB_HOST,
                    'port': settings.DB_PORT,
                    'database': settings.DB_NAME,
                    'user': settings.DB_USER,
                    'password': settings.DB_PASSWORD,
                    'min_size': 1,
                    'max_size': settings.DB_MAX_POOL_SIZE,
                    'timeout': 30,
                    'command_timeout': settings.DB_QUERY_TIMEOUT / 1000,
                    'statement_cache_size': 0,  # Required for pgbouncer
                }
                
                # Add SSL if required
                if settings.DB_SSL_MODE == 'require':
                    import ssl
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    conn_params['ssl'] = ssl_context
                
                # Use asyncio.wait_for to enforce timeout
                self._pool = await asyncio.wait_for(
                    asyncpg.create_pool(**conn_params),
                    timeout=30.0  # 30 second timeout for pool creation
                )
                
                # Test the connection
                async with self._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                
                self._is_available = True
                self._use_psycopg = False
                logger.info(f"asyncpg connection pool initialized successfully (min=1, max={settings.DB_MAX_POOL_SIZE})")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"asyncpg connection attempt {attempt} failed: Connection timeout after 30 seconds")
                
                if attempt == len(self._retry_delays):
                    return False
                    
            except (asyncpg.PostgresConnectionError, asyncpg.PostgresError, OSError) as e:
                logger.error(f"asyncpg connection attempt {attempt} failed: {type(e).__name__}: {str(e)}")
                
                # If it's a network error, don't retry asyncpg
                if isinstance(e, OSError) and e.errno == 101:
                    logger.warning("Network unreachable error detected, will try psycopg2 fallback")
                    return False
                
                if attempt == len(self._retry_delays):
                    return False
        
        return False
    
    async def _try_psycopg(self) -> bool:
        """Try to connect using psycopg2 (sync driver with thread pool)."""
        try:
            logger.info(f"Attempting psycopg2 connection to {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
            
            # Build connection string
            conn_string = f"host={settings.DB_HOST} port={settings.DB_PORT} dbname={settings.DB_NAME} user={settings.DB_USER} password={settings.DB_PASSWORD}"
            
            if settings.DB_SSL_MODE == 'require':
                conn_string += " sslmode=require"
            
            # Create threaded connection pool
            self._psycopg_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=settings.DB_MAX_POOL_SIZE,
                dsn=conn_string
            )
            
            # Test the connection
            conn = self._psycopg_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
                if result[0] == 1:
                    self._is_available = True
                    self._use_psycopg = True
                    logger.info(f"psycopg2 connection pool initialized successfully (min=1, max={settings.DB_MAX_POOL_SIZE})")
                    return True
            finally:
                self._psycopg_pool.putconn(conn)
            
        except Exception as e:
            logger.error(f"psycopg2 connection failed: {type(e).__name__}: {str(e)}")
            if self._psycopg_pool:
                self._psycopg_pool.closeall()
                self._psycopg_pool = None
            return False
        
        return False
    
    async def close(self) -> None:
        """
        Close the connection pool and cleanup resources.
        """
        if self._pool:
            try:
                await self._pool.close()
                logger.info("asyncpg connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing asyncpg connection pool: {e}")
            finally:
                self._pool = None
        
        if self._psycopg_pool:
            try:
                self._psycopg_pool.closeall()
                logger.info("psycopg2 connection pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing psycopg2 connection pool: {e}")
            finally:
                self._psycopg_pool = None
        
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
        if not self._is_available:
            return False
        
        try:
            # Check asyncpg pool
            if self._pool and not self._use_psycopg:
                async with self._pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    return result == 1
            
            # Check psycopg2 pool
            elif self._psycopg_pool and self._use_psycopg:
                conn = self._psycopg_pool.getconn()
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    cursor.close()
                    return result[0] == 1
                finally:
                    self._psycopg_pool.putconn(conn)
            
            return False
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if the database connection is available.
        
        Returns:
            bool: True if database is available, False otherwise
        """
        return self._is_available and (self._pool is not None or self._psycopg_pool is not None)
    
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
