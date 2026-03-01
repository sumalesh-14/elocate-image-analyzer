"""
Simple database connection test script.
Tests connection to Supabase PostgreSQL database.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv()

async def test_connection():
    """Test database connection with provided credentials."""
    
    # Load environment variables
    load_dotenv()
    
    # Try to use DATABASE_URL first, then fall back to individual settings
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        print("Using DATABASE_URL from environment")
        # Parse JDBC URL
        if database_url.startswith('jdbc:postgresql://'):
            database_url = database_url.replace('jdbc:postgresql://', '')
        elif database_url.startswith('jdbc:'):
            database_url = database_url[5:]
        
        # Parse URL: postgresql://host:port/database?params or host:port/database?params
        from urllib.parse import urlparse, parse_qs
        
        if not database_url.startswith('postgresql://'):
            database_url = 'postgresql://' + database_url
        
        parsed = urlparse(database_url)
        
        db_host = parsed.hostname
        db_port = parsed.port or 5432
        db_name = parsed.path.lstrip('/').split('?')[0] if parsed.path else 'postgres'
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        # Parse query parameters for SSL mode
        if parsed.query:
            params = parse_qs(parsed.query)
            db_ssl_mode = params.get('sslmode', ['require'])[0]
        else:
            db_ssl_mode = 'require'
    else:
        # Use individual settings
        db_host = os.getenv('DB_HOST')
        db_port = int(os.getenv('DB_PORT', 5432))
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
    
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"SSL Mode: {db_ssl_mode}")
    print("=" * 60)
    
    try:
        print("\n[1/4] Attempting to connect to database...")
        
        # Create connection (disable prepared statements for pgbouncer)
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            ssl=db_ssl_mode,
            timeout=10,
            statement_cache_size=0  # Required for pgbouncer
        )
        
        print("✓ Connection successful!")
        
        # Test query
        print("\n[2/4] Testing basic query...")
        version = await conn.fetchval('SELECT version()')
        print(f"✓ PostgreSQL version: {version[:50]}...")
        
        # Check tables
        print("\n[3/4] Checking for device-related tables...")
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('device_categories', 'device_brands', 'device_models')
            ORDER BY table_name
        """
        tables = await conn.fetch(tables_query)
        
        if tables:
            print(f"✓ Found {len(tables)} device tables:")
            for table in tables:
                print(f"  - {table['table_name']}")
        else:
            print("⚠ No device tables found (device_categories, device_brands, device_models)")
        
        # Count records
        print("\n[4/4] Counting records in tables...")
        
        for table_name in ['device_categories', 'device_brands', 'device_models']:
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM {table_name}')
                print(f"✓ {table_name}: {count} records")
            except Exception as e:
                print(f"✗ {table_name}: Table not found or error - {str(e)}")
        
        # Close connection
        await conn.close()
        print("\n" + "=" * 60)
        print("✓ All tests passed! Database connection is working.")
        print("=" * 60)
        
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("\n✗ ERROR: Invalid password")
        print("Please check your DB_PASSWORD in .env file")
        return False
        
    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"\n✗ ERROR: Database '{db_name}' does not exist")
        print("Please check your DB_NAME in .env file")
        return False
        
    except asyncpg.exceptions.PostgresConnectionError as e:
        print(f"\n✗ ERROR: Cannot connect to PostgreSQL server")
        print(f"Details: {str(e)}")
        print("\nPossible issues:")
        print("- Check if DB_HOST and DB_PORT are correct")
        print("- Verify network connectivity")
        print("- Check if SSL mode is correct")
        return False
        
    except Exception as e:
        print(f"\n✗ ERROR: Unexpected error occurred")
        print(f"Type: {type(e).__name__}")
        print(f"Details: {str(e)}")
        return False


if __name__ == "__main__":
    print("\nStarting database connection test...\n")
    success = asyncio.run(test_connection())
    
    if success:
        print("\n✓ Database is ready for use!")
        exit(0)
    else:
        print("\n✗ Database connection failed. Please fix the issues above.")
        exit(1)
