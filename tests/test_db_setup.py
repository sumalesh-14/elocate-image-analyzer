"""
Test database setup utilities for integration tests.

Provides fixtures and utilities for setting up a test PostgreSQL database
with seed data for device_category, device_brand, category_brand, and device_model tables.
"""

import asyncpg
import pytest
from uuid import UUID
from typing import AsyncGenerator


# Test data UUIDs (fixed for consistent testing)
TEST_CATEGORY_MOBILE_ID = UUID('550e8400-e29b-41d4-a716-446655440001')
TEST_CATEGORY_LAPTOP_ID = UUID('550e8400-e29b-41d4-a716-446655440002')
TEST_CATEGORY_TABLET_ID = UUID('550e8400-e29b-41d4-a716-446655440003')

TEST_BRAND_APPLE_ID = UUID('660e8400-e29b-41d4-a716-446655440001')
TEST_BRAND_SAMSUNG_ID = UUID('660e8400-e29b-41d4-a716-446655440002')
TEST_BRAND_DELL_ID = UUID('660e8400-e29b-41d4-a716-446655440003')

TEST_MODEL_IPHONE_14_ID = UUID('770e8400-e29b-41d4-a716-446655440001')
TEST_MODEL_GALAXY_S23_ID = UUID('770e8400-e29b-41d4-a716-446655440002')
TEST_MODEL_XPS_15_ID = UUID('770e8400-e29b-41d4-a716-446655440003')
TEST_MODEL_IPAD_PRO_ID = UUID('770e8400-e29b-41d4-a716-446655440004')


async def create_test_tables(conn: asyncpg.Connection) -> None:
    """Create test database tables."""
    
    # Create device_category table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS device_category (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            code VARCHAR(50) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_category_name 
        ON device_category(name)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_category_code 
        ON device_category(code)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_category_active 
        ON device_category(is_active)
    """)
    
    # Create device_brand table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS device_brand (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            code VARCHAR(50) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_brand_name 
        ON device_brand(name)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_brand_code 
        ON device_brand(code)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_brand_active 
        ON device_brand(is_active)
    """)
    
    # Create category_brand junction table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS category_brand (
            category_id UUID REFERENCES device_category(id),
            brand_id UUID REFERENCES device_brand(id),
            PRIMARY KEY (category_id, brand_id)
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_category_brand_category 
        ON category_brand(category_id)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_category_brand_brand 
        ON category_brand(brand_id)
    """)
    
    # Create device_model table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS device_model (
            id UUID PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            code VARCHAR(100) UNIQUE NOT NULL,
            category_id UUID REFERENCES device_category(id),
            brand_id UUID REFERENCES device_brand(id),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_model_name 
        ON device_model(name)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_model_code 
        ON device_model(code)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_model_category 
        ON device_model(category_id)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_model_brand 
        ON device_model(brand_id)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_device_model_active 
        ON device_model(is_active)
    """)


async def seed_test_data(conn: asyncpg.Connection) -> None:
    """Insert test seed data into database tables."""
    
    # Insert categories
    await conn.execute("""
        INSERT INTO device_category (id, name, code, is_active)
        VALUES 
            ($1, 'Mobile Phone', 'MOBILE', true),
            ($2, 'Laptop', 'LAPTOP', true),
            ($3, 'Tablet', 'TABLET', true)
        ON CONFLICT (id) DO NOTHING
    """, TEST_CATEGORY_MOBILE_ID, TEST_CATEGORY_LAPTOP_ID, TEST_CATEGORY_TABLET_ID)
    
    # Insert brands
    await conn.execute("""
        INSERT INTO device_brand (id, name, code, is_active)
        VALUES 
            ($1, 'Apple', 'APPLE', true),
            ($2, 'Samsung', 'SAMSUNG', true),
            ($3, 'Dell', 'DELL', true)
        ON CONFLICT (id) DO NOTHING
    """, TEST_BRAND_APPLE_ID, TEST_BRAND_SAMSUNG_ID, TEST_BRAND_DELL_ID)
    
    # Insert category-brand relationships
    await conn.execute("""
        INSERT INTO category_brand (category_id, brand_id)
        VALUES 
            ($1, $2),
            ($1, $3),
            ($4, $2),
            ($5, $6)
        ON CONFLICT DO NOTHING
    """, 
        TEST_CATEGORY_MOBILE_ID, TEST_BRAND_APPLE_ID,
        TEST_CATEGORY_MOBILE_ID, TEST_BRAND_SAMSUNG_ID,
        TEST_CATEGORY_TABLET_ID, TEST_BRAND_APPLE_ID,
        TEST_CATEGORY_LAPTOP_ID, TEST_BRAND_DELL_ID
    )
    
    # Insert models
    await conn.execute("""
        INSERT INTO device_model (id, name, code, category_id, brand_id, is_active)
        VALUES 
            ($1, 'iPhone 14 Pro', 'IPHONE_14_PRO', $2, $3, true),
            ($4, 'Galaxy S23', 'GALAXY_S23', $2, $5, true),
            ($6, 'XPS 15', 'XPS_15', $7, $8, true),
            ($9, 'iPad Pro', 'IPAD_PRO', $10, $3, true)
        ON CONFLICT (id) DO NOTHING
    """,
        TEST_MODEL_IPHONE_14_ID, TEST_CATEGORY_MOBILE_ID, TEST_BRAND_APPLE_ID,
        TEST_MODEL_GALAXY_S23_ID, TEST_BRAND_SAMSUNG_ID,
        TEST_MODEL_XPS_15_ID, TEST_CATEGORY_LAPTOP_ID, TEST_BRAND_DELL_ID,
        TEST_MODEL_IPAD_PRO_ID, TEST_CATEGORY_TABLET_ID
    )


async def cleanup_test_data(conn: asyncpg.Connection) -> None:
    """Clean up test data from database tables."""
    await conn.execute("DELETE FROM device_model")
    await conn.execute("DELETE FROM category_brand")
    await conn.execute("DELETE FROM device_brand")
    await conn.execute("DELETE FROM device_category")


async def drop_test_tables(conn: asyncpg.Connection) -> None:
    """Drop test database tables."""
    await conn.execute("DROP TABLE IF EXISTS device_model CASCADE")
    await conn.execute("DROP TABLE IF EXISTS category_brand CASCADE")
    await conn.execute("DROP TABLE IF EXISTS device_brand CASCADE")
    await conn.execute("DROP TABLE IF EXISTS device_category CASCADE")


@pytest.fixture
async def test_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Provide a test database connection with tables and seed data.
    
    This fixture:
    1. Creates a connection to the test database
    2. Creates all required tables
    3. Seeds test data
    4. Yields the connection for tests
    5. Cleans up data and drops tables after tests
    """
    # Use environment variable or default to local test database
    import os
    db_url = os.getenv(
        'TEST_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/elocate_test'
    )
    
    conn = await asyncpg.connect(db_url)
    
    try:
        # Setup
        await create_test_tables(conn)
        await seed_test_data(conn)
        
        yield conn
        
    finally:
        # Cleanup
        await cleanup_test_data(conn)
        await drop_test_tables(conn)
        await conn.close()


@pytest.fixture
async def test_db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """
    Provide a test database connection pool.
    
    This fixture creates a connection pool for performance testing
    and concurrent request handling tests.
    """
    import os
    db_url = os.getenv(
        'TEST_DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/elocate_test'
    )
    
    pool = await asyncpg.create_pool(
        db_url,
        min_size=5,
        max_size=20,
        command_timeout=10
    )
    
    try:
        # Setup tables and data
        async with pool.acquire() as conn:
            await create_test_tables(conn)
            await seed_test_data(conn)
        
        yield pool
        
    finally:
        # Cleanup
        async with pool.acquire() as conn:
            await cleanup_test_data(conn)
            await drop_test_tables(conn)
        
        await pool.close()
