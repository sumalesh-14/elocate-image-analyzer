"""
Comprehensive local database connection test script.
Tests both asyncpg and psycopg2 connections with detailed diagnostics.
"""

import asyncio
import sys
import os
from datetime import datetime
import asyncpg
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{YELLOW}ℹ {text}{RESET}")


def get_db_config():
    """Extract database configuration from environment."""
    database_url = os.getenv('DATABASE_URL', '')
    
    # Parse DATABASE_URL if provided
    if database_url:
        # Handle postgresql:// format
        if database_url.startswith('postgresql://'):
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/') if parsed.path else 'postgres',
                'user': parsed.username,
                'password': parsed.password,
            }
    
    # Fallback to individual env vars
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'elocate'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
    }


async def test_asyncpg_connection(config: dict) -> bool:
    """Test asyncpg connection."""
    print_header("Testing asyncpg Connection")
    
    try:
        print_info(f"Connecting to: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # Create connection with timeout
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                timeout=10
            ),
            timeout=15.0
        )
        
        print_success("Connection established")
        
        # Test query
        result = await conn.fetchval("SELECT 1")
        if result == 1:
            print_success("Test query executed successfully")
        
        # Get PostgreSQL version
        version = await conn.fetchval("SELECT version()")
        print_info(f"PostgreSQL version: {version.split(',')[0]}")
        
        # Test table access
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
            LIMIT 5
        """
        tables = await conn.fetch(tables_query)
        print_success(f"Found {len(tables)} tables in public schema")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        # Close connection
        await conn.close()
        print_success("Connection closed cleanly")
        
        return True
        
    except asyncio.TimeoutError:
        print_error("Connection timeout (15 seconds)")
        return False
    except asyncpg.PostgresConnectionError as e:
        print_error(f"Connection error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {type(e).__name__}: {e}")
        return False


async def test_asyncpg_pool(config: dict) -> bool:
    """Test asyncpg connection pool."""
    print_header("Testing asyncpg Connection Pool")
    
    try:
        print_info("Creating connection pool (min=1, max=5)")
        
        pool = await asyncio.wait_for(
            asyncpg.create_pool(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                min_size=1,
                max_size=5,
                timeout=10,
                command_timeout=5,
                statement_cache_size=0  # Required for pgbouncer
            ),
            timeout=15.0
        )
        
        print_success("Connection pool created")
        
        # Test acquiring connection
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print_success("Pool connection acquired and tested")
        
        # Test concurrent connections
        print_info("Testing concurrent connections...")
        async def test_query(i):
            async with pool.acquire() as conn:
                await conn.fetchval(f"SELECT {i}")
        
        await asyncio.gather(*[test_query(i) for i in range(3)])
        print_success("Concurrent connections successful")
        
        # Close pool
        await pool.close()
        print_success("Connection pool closed cleanly")
        
        return True
        
    except asyncio.TimeoutError:
        print_error("Pool creation timeout")
        return False
    except Exception as e:
        print_error(f"Pool error: {type(e).__name__}: {e}")
        return False


def test_psycopg2_connection(config: dict) -> bool:
    """Test psycopg2 connection."""
    print_header("Testing psycopg2 Connection")
    
    try:
        print_info(f"Connecting to: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # Create connection
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            connect_timeout=10
        )
        
        print_success("Connection established")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result[0] == 1:
            print_success("Test query executed successfully")
        
        # Get PostgreSQL version
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print_info(f"PostgreSQL version: {version.split(',')[0]}")
        
        # Test table access
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
            LIMIT 5
        """)
        tables = cursor.fetchall()
        print_success(f"Found {len(tables)} tables in public schema")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        print_success("Connection closed cleanly")
        
        return True
        
    except psycopg2.OperationalError as e:
        print_error(f"Connection error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {type(e).__name__}: {e}")
        return False


def test_psycopg2_pool(config: dict) -> bool:
    """Test psycopg2 connection pool."""
    print_header("Testing psycopg2 Connection Pool")
    
    try:
        print_info("Creating threaded connection pool (min=1, max=5)")
        
        # Build connection string
        conn_string = f"host={config['host']} port={config['port']} dbname={config['database']} user={config['user']} password={config['password']}"
        
        # Create pool
        conn_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=conn_string
        )
        
        print_success("Connection pool created")
        
        # Test getting connection
        conn = conn_pool.getconn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result[0] == 1:
            print_success("Pool connection acquired and tested")
        
        cursor.close()
        conn_pool.putconn(conn)
        
        # Close pool
        conn_pool.closeall()
        print_success("Connection pool closed cleanly")
        
        return True
        
    except Exception as e:
        print_error(f"Pool error: {type(e).__name__}: {e}")
        return False


async def test_device_tables(config: dict) -> bool:
    """Test access to device-related tables."""
    print_header("Testing Device Tables Access")
    
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                timeout=10
            ),
            timeout=15.0
        )
        
        # Test device_category
        categories = await conn.fetch("SELECT id, name FROM device_category LIMIT 3")
        print_success(f"device_category: {len(categories)} rows")
        for cat in categories:
            print(f"  - {cat['name']}")
        
        # Test device_brand
        brands = await conn.fetch("SELECT id, name FROM device_brand LIMIT 3")
        print_success(f"device_brand: {len(brands)} rows")
        for brand in brands:
            print(f"  - {brand['name']}")
        
        # Test device_model (check columns first)
        model_columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'device_model' 
            ORDER BY ordinal_position
        """)
        print_info(f"device_model columns: {', '.join([c['column_name'] for c in model_columns])}")
        
        # Query with available columns
        models = await conn.fetch("SELECT * FROM device_model LIMIT 3")
        print_success(f"device_model: {len(models)} rows")
        for model in models:
            # Print first few columns
            print(f"  - {dict(model)}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print_error(f"Table access error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all database tests."""
    print(f"\n{BLUE}{'='*60}")
    print(f"  Database Connection Test Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}\n")
    
    # Get configuration
    config = get_db_config()
    print_info(f"Database: {config['database']}")
    print_info(f"Host: {config['host']}:{config['port']}")
    print_info(f"User: {config['user']}")
    
    results = {}
    
    # Run tests
    results['asyncpg_connection'] = await test_asyncpg_connection(config)
    results['asyncpg_pool'] = await test_asyncpg_pool(config)
    results['psycopg2_connection'] = test_psycopg2_connection(config)
    results['psycopg2_pool'] = test_psycopg2_pool(config)
    results['device_tables'] = await test_device_tables(config)
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}PASSED{RESET}" if result else f"{RED}FAILED{RESET}"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}✓ All tests passed! Database is ready for deployment.{RESET}\n")
        return 0
    else:
        print(f"\n{RED}✗ Some tests failed. Please review the errors above.{RESET}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
