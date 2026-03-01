"""
Direct connection test with extended timeout.
"""
import asyncio
import asyncpg
import sys

async def test_direct():
    """Test with very long timeout."""
    
    print("Testing DIRECT connection with 120 second timeout...")
    print("=" * 60)
    
    try:
        # Try direct connection with very long timeout
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host='db.qnnkizacregmdsfgqrsw.supabase.co',
                port=5432,
                database='postgres',
                user='postgres.qnnkizacregmdsfgqrsw',
                password='AL+4kWTv%A+k9DK',
                ssl='require',
                statement_cache_size=0,
                timeout=120  # 2 minutes
            ),
            timeout=120.0
        )
        
        print("✓ Connection successful!")
        
        # Test query
        result = await conn.fetchval('SELECT 1')
        print(f"✓ Query successful: {result}")
        
        # Get version
        version = await conn.fetchval('SELECT version()')
        print(f"✓ PostgreSQL version: {version[:50]}...")
        
        await conn.close()
        print("\n✓ ALL TESTS PASSED!")
        return True
        
    except asyncio.TimeoutError:
        print("\n✗ Connection timed out after 120 seconds")
        print("This is a network connectivity issue.")
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nStarting extended timeout test...\n")
    success = asyncio.run(test_direct())
    
    if success:
        print("\n✓ Database connection works!")
        sys.exit(0)
    else:
        print("\n✗ Cannot connect from this network.")
        print("\nPossible solutions:")
        print("1. Try from a different network (mobile hotspot)")
        print("2. Check if VPN is blocking the connection")
        print("3. Deploy to cloud (Railway/Render) where it will work")
        sys.exit(1)
