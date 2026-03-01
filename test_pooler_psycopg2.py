"""
Test connection using transaction pooler with psycopg2.
IPv4 proxied - might work better!
"""
import psycopg2
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

def test_pooler_connection():
    """Test with transaction pooler."""
    
    print("Testing TRANSACTION POOLER (IPv4 proxied)...")
    print("=" * 60)
    
    # Pooler settings
    USER = "postgres.qnnkizacregmdsfgqrsw"
    PASSWORD = "AL+4kWTv%A+k9DK"
    HOST = "aws-1-ap-southeast-1.pooler.supabase.com"
    PORT = "6543"
    DBNAME = "postgres"
    
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Database: {DBNAME}")
    print(f"User: {USER}")
    print("=" * 60)
    
    try:
        # Connect
        print("\nConnecting...")
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME,
            sslmode='require',
            connect_timeout=30
        )
        
        print("✓ Connection successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        print("\nExecuting test query...")
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print(f"✓ Current Time: {result[0]}")
        
        # Get version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL version: {version[:50]}...")
        
        # Check tables
        print("\nChecking for device tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('device_categories', 'device_brands', 'device_models')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"✓ Found {len(tables)} device tables:")
            for table in tables:
                print(f"  - {table[0]}")
                
                # Count records
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"    ({count} records)")
        else:
            print("⚠ No device tables found")
        
        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("\n✓ Connection closed.")
        
        print("\n" + "=" * 60)
        print("✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print("=" * 60)
        print("\nDatabase connection is WORKING!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n✗ Connection failed: {str(e)}")
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING SUPABASE TRANSACTION POOLER")
    print("=" * 60 + "\n")
    
    success = test_pooler_connection()
    
    if success:
        print("\n🎉 SUCCESS! Database is accessible via pooler!")
        print("\nNow updating your app configuration...")
        sys.exit(0)
    else:
        print("\n✗ Pooler connection also failed.")
        print("Network is blocking both direct and pooler connections.")
        sys.exit(1)
