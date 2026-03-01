"""
Property-based tests for query cache behavior.

Tests universal properties that should hold for the query caching mechanism
used in database matching integration.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from hypothesis import given, strategies as st, settings

from app.services.database_matcher import DatabaseMatcher, CategoryMatch
from app.services.query_cache import QueryCache


# Feature: database-matching-integration, Property 21: Query Result Caching
@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=' '
    ))
)
@settings(max_examples=20)
@pytest.mark.property_test
@pytest.mark.asyncio
async def test_query_result_caching(category_text: str):
    """
    **Validates: Requirements 7.5**
    
    For any database query with identical input text and context, if executed 
    twice within 5 minutes, the second execution should return cached results 
    without querying the database.
    """
    # Create a fresh DatabaseMatcher instance for this test
    matcher = DatabaseMatcher()
    
    # Create a mock database result
    mock_category_id = UUID('550e8400-e29b-41d4-a716-446655440001')
    
    # Mock the database manager to be available
    with patch('app.services.database_matcher.db_manager') as mock_db_manager, \
         patch('app.services.database_matcher.FuzzyMatcher') as mock_fuzzy:
        
        mock_db_manager.is_available.return_value = True
        
        # Create mock connection and pool
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        
        # Set up the async context manager properly
        mock_acquire = AsyncMock()
        mock_acquire.__aenter__.return_value = mock_conn
        mock_acquire.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_acquire
        
        mock_db_manager.pool = mock_pool
        
        # Mock the database fetch to return a result
        mock_conn.fetch.return_value = [
            {'id': mock_category_id, 'name': 'Test Category'}
        ]
        
        # Mock fuzzy matcher to always return a match above threshold
        mock_fuzzy.normalize.return_value = category_text.lower().strip()
        mock_fuzzy.find_best_match.return_value = (
            {'id': mock_category_id, 'name': 'Test Category'},
            0.95
        )
        
        # First query - should hit the database
        result1 = await matcher.match_category(category_text)
        
        # Verify database was queried (fetch was called)
        assert mock_conn.fetch.call_count == 1, \
            "First query should hit the database"
        
        # Verify result is correct
        assert result1 is not None, \
            f"First query should return a result for '{category_text}'"
        
        # Second query with identical input - should use cache
        result2 = await matcher.match_category(category_text)
        
        # Verify database was NOT queried again (fetch still called only once)
        assert mock_conn.fetch.call_count == 1, \
            "Second query with identical input should use cache, not query database"
        
        # Verify both results are the same
        if result1 and result2:
            assert result1.id == result2.id, \
                "Cached result should have same ID as original"
            assert result1.name == result2.name, \
                "Cached result should have same name as original"
            assert result1.similarity_score == result2.similarity_score, \
                "Cached result should have same similarity score as original"


@pytest.mark.property_test
@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """
    **Validates: Requirements 7.5**
    
    Verify that cache entries expire after TTL and subsequent queries hit the database.
    This test uses a short TTL to verify expiration behavior.
    """
    # Create a cache with very short TTL (1 second) for testing
    cache = QueryCache(max_size=100, ttl=1)
    
    # Store a value
    test_key = "category:test_device:"
    test_value = CategoryMatch(
        id=UUID('550e8400-e29b-41d4-a716-446655440001'),
        name="Test Category",
        similarity_score=0.90
    )
    
    cache.set(test_key, test_value)
    
    # Immediately retrieve - should be cached
    cached_value = cache.get(test_key)
    assert cached_value is not None, \
        "Value should be cached immediately after setting"
    assert cached_value.id == test_value.id, \
        "Cached value should match original"
    
    # Wait for TTL to expire (1 second + small buffer)
    await asyncio.sleep(1.2)
    
    # Try to retrieve after TTL - should be None (expired)
    expired_value = cache.get(test_key)
    assert expired_value is None, \
        "Value should be None after TTL expiration"


@given(
    num_entries=st.integers(min_value=5, max_value=20)
)
@settings(max_examples=50)
@pytest.mark.property_test
def test_cache_size_limit(num_entries: int):
    """
    **Validates: Requirements 7.5**
    
    Verify that cache respects max size limit and evicts entries when full.
    """
    # Create a cache with small max size
    max_size = 10
    cache = QueryCache(max_size=max_size, ttl=300)
    
    # Add entries up to or beyond max size
    for i in range(num_entries):
        key = f"category:device_{i}:"
        value = CategoryMatch(
            id=UUID(f'550e8400-e29b-41d4-a716-44665544{i:04d}'),
            name=f"Category {i}",
            similarity_score=0.85
        )
        cache.set(key, value)
    
    # Cache size should never exceed max_size
    current_size = cache.size()
    assert current_size <= max_size, \
        f"Cache size {current_size} should not exceed max_size {max_size}"
    
    # If we added more than max_size entries, size should be exactly max_size
    if num_entries > max_size:
        assert current_size == max_size, \
            f"Cache should be at max_size {max_size} after adding {num_entries} entries"


@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=' '
    )),
    brand_text=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=' '
    ))
)
@settings(max_examples=50)
@pytest.mark.property_test
@pytest.mark.asyncio
async def test_cache_context_isolation(category_text: str, brand_text: str):
    """
    **Validates: Requirements 7.5**
    
    Verify that cache correctly isolates entries by context (e.g., brand queries 
    with different category_ids are cached separately).
    """
    matcher = DatabaseMatcher()
    
    # Two different category IDs for context
    category_id_1 = UUID('550e8400-e29b-41d4-a716-446655440001')
    category_id_2 = UUID('550e8400-e29b-41d4-a716-446655440002')
    
    # Mock the database manager
    with patch('app.services.database_matcher.db_manager') as mock_db_manager, \
         patch('app.services.database_matcher.FuzzyMatcher') as mock_fuzzy:
        
        mock_db_manager.is_available.return_value = True
        
        # Create mock connection and pool
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        
        # Set up the async context manager properly
        mock_acquire = AsyncMock()
        mock_acquire.__aenter__.return_value = mock_conn
        mock_acquire.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_acquire
        
        mock_db_manager.pool = mock_pool
        
        # Mock fuzzy matcher
        mock_fuzzy.normalize.return_value = brand_text.lower().strip()
        
        # Mock different results for different contexts
        brand_id_1 = UUID('660e8400-e29b-41d4-a716-446655440001')
        brand_id_2 = UUID('660e8400-e29b-41d4-a716-446655440002')
        
        # First query with category_id_1
        mock_conn.fetch.return_value = [
            {'id': brand_id_1, 'name': 'Brand 1'}
        ]
        mock_fuzzy.find_best_match.return_value = (
            {'id': brand_id_1, 'name': 'Brand 1'},
            0.90
        )
        result1 = await matcher.match_brand(brand_text, category_id_1)
        first_call_count = mock_conn.fetch.call_count
        
        # Second query with category_id_2 (different context)
        mock_conn.fetch.return_value = [
            {'id': brand_id_2, 'name': 'Brand 2'}
        ]
        mock_fuzzy.find_best_match.return_value = (
            {'id': brand_id_2, 'name': 'Brand 2'},
            0.90
        )
        result2 = await matcher.match_brand(brand_text, category_id_2)
        second_call_count = mock_conn.fetch.call_count
        
        # Both queries should hit the database because contexts are different
        assert second_call_count > first_call_count, \
            "Query with different context should hit database, not use cache from different context"
        
        # Third query with category_id_1 again (same as first)
        result3 = await matcher.match_brand(brand_text, category_id_1)
        third_call_count = mock_conn.fetch.call_count
        
        # Third query should use cache (same context as first)
        assert third_call_count == second_call_count, \
            "Query with same context as earlier query should use cache"

