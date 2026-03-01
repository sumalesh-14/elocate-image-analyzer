"""
Test connection using psycopg2 (synchronous).
Sometimes works better on Windows.
"""
import psycopg2
import sys

def test_connection():
    """Test with psycopg2."""
    
    print("Testing with psycopg2 (synchronous driver)...")
    print("=" * 60)
    
    try:
        # Connect
        print("Connecting...")
        conn = psycopg2.connect(
            host='db.qnnkizacregmdsfgqrsw.supabase.co',
            port=5432,
            database='postgres',
            user='postgres.qnnkizacregmdsfgqrsw',
            password='AL+4kWTv%A+k9DK',
            sslmode='require',
            connect_timeout=60
        )
        
        print("✓ Connection successful!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        print(f"✓ Query successful: {result[0]}")
        
        # Get version
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL version: {version[:50]}...")
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"\n✓ Found {len(tables)} tables in database:")
        for table in tables[:10]:  # Show first 10
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n✗ Connection failed: {str(e)}")
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nTesting database connection with psycopg2...\n")
    success = test_connection()
    
    if success:
        print("\n✓ Database is accessible!")
        sys.exit(0)
    else:
        print("\n✗ Cannot connect from this network.")
        sys.exit(1)
