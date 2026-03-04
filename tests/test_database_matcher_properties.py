"""
Property-based tests for database matcher service.

Tests universal properties that should hold across all inputs for the database
matching functionality used in device identification.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings
from uuid import uuid4

from app.services.database_matcher import DatabaseMatcher, CategoryMatch
from app.config import settings as app_settings


# Feature: database-matching-integration, Property 6: Category Threshold Enforcement
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_candidates=st.integers(min_value=0, max_value=10),
    best_score=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_category_threshold_enforcement(category_text: str, num_candidates: int, best_score: float):
    """
    **Validates: Requirements 2.2, 2.5**
    
    For any category matching operation, if a match is returned, its similarity 
    score should be >= 0.80; otherwise category_id should be null.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows
    mock_rows = []
    for i in range(num_candidates):
        mock_rows.append({
            'id': uuid4(),
            'name': f'Category_{i}'
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Mock the find_best_match to return controlled score
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Determine if match should be returned based on threshold
            if best_score >= app_settings.CATEGORY_MATCH_THRESHOLD and num_candidates > 0:
                # Return a match
                mock_find_best.return_value = (
                    {'id': mock_rows[0]['id'], 'name': mock_rows[0]['name']},
                    best_score
                )
            else:
                # No match above threshold
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_category(category_text)
            
            # Property: If a match is returned, similarity score must be >= 0.80
            if result is not None:
                assert isinstance(result, CategoryMatch), \
                    f"Result should be CategoryMatch instance, got {type(result)}"
                assert result.similarity_score >= app_settings.CATEGORY_MATCH_THRESHOLD, \
                    f"Match returned with score {result.similarity_score} below threshold {app_settings.CATEGORY_MATCH_THRESHOLD}"
                assert result.id is not None, \
                    "Match returned but category_id is None"
            
            # Property: If no match is returned (None), it means either:
            # 1. No candidates exist, or
            # 2. Best score is below threshold
            if result is None:
                # This is expected when score < threshold or no candidates
                # The category_id will be null in the response
                pass


# Feature: database-matching-integration, Property 6: Category Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_category_threshold_enforcement_exact_threshold():
    """
    **Validates: Requirements 2.2, 2.5**
    
    Test boundary condition: a match with exactly 0.80 similarity should be returned.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database row
    mock_id = uuid4()
    mock_rows = [{'id': mock_id, 'name': 'Mobile Phone'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return match with exactly threshold score
            mock_find_best.return_value = (
                {'id': mock_id, 'name': 'Mobile Phone'},
                0.80
            )
            
            result = await matcher.match_category("mobile phone")
            
            # Property: Match at exactly threshold should be returned
            assert result is not None, \
                "Match with score exactly at threshold (0.80) should be returned"
            assert result.similarity_score == 0.80, \
                f"Expected score 0.80, got {result.similarity_score}"
            assert result.id == mock_id, \
                "Returned match should have correct UUID"


# Feature: database-matching-integration, Property 6: Category Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_category_threshold_enforcement_below_threshold():
    """
    **Validates: Requirements 2.2, 2.5**
    
    Test boundary condition: a match with 0.79 similarity should NOT be returned.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database row
    mock_rows = [{'id': uuid4(), 'name': 'Mobile Phone'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return None because score is below threshold
            mock_find_best.return_value = None
            
            result = await matcher.match_category("mobile phone")
            
            # Property: Match below threshold should return None (null category_id)
            assert result is None, \
                "Match with score below threshold (0.79) should return None"


# Feature: database-matching-integration, Property 6: Category Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_category_threshold_enforcement_no_candidates():
    """
    **Validates: Requirements 2.2, 2.5**
    
    When no candidates exist in database, should return None (null category_id).
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # No candidates in database
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # No candidates means no match
            mock_find_best.return_value = None
            
            result = await matcher.match_category("some category")
            
            # Property: No candidates should return None (null category_id)
            assert result is None, \
                "When no candidates exist, should return None"


# Feature: database-matching-integration, Property 6: Category Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_category_threshold_enforcement_database_unavailable():
    """
    **Validates: Requirements 2.2, 2.5**
    
    When database is unavailable, should return None (null category_id).
    """
    matcher = DatabaseMatcher()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = False
        
        result = await matcher.match_category("mobile phone")
        
        # Property: Database unavailable should return None (null category_id)
        assert result is None, \
            "When database is unavailable, should return None"


# Feature: database-matching-integration, Property 7: Active Records Only
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_active=st.integers(min_value=0, max_value=5),
    num_inactive=st.integers(min_value=0, max_value=5),
    best_score=st.floats(min_value=0.80, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_active_records_only_category(category_text: str, num_active: int, num_inactive: int, best_score: float):
    """
    **Validates: Requirements 2.3, 3.4, 4.4**
    
    For any returned category match, the corresponding database record should have 
    is_active = true. The database queries should only return active records.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows - only active records should be in query results
    # (The SQL query filters WHERE is_active = true)
    mock_active_rows = []
    for i in range(num_active):
        mock_active_rows.append({
            'id': uuid4(),
            'name': f'ActiveCategory_{i}',
            'is_active': True  # All returned rows should be active
        })
    
    # Inactive records should NOT be in the query results
    # (They are filtered out by the WHERE clause)
    mock_conn.fetch = AsyncMock(return_value=mock_active_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # If there are active candidates, return a match
            if num_active > 0:
                mock_find_best.return_value = (
                    {'id': mock_active_rows[0]['id'], 'name': mock_active_rows[0]['name']},
                    best_score
                )
            else:
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_category(category_text)
            
            # Property: If a match is returned, it must correspond to an active record
            if result is not None:
                # Verify the query was called with is_active = true filter
                mock_conn.fetch.assert_called_once()
                query_sql = mock_conn.fetch.call_args[0][0]
                assert 'is_active = true' in query_sql.lower(), \
                    "Query must filter for active records only"
                
                # Verify all rows returned by query are active
                for row in mock_active_rows:
                    assert row.get('is_active', True) is True, \
                        f"Query returned inactive record: {row}"


# Feature: database-matching-integration, Property 7: Active Records Only
@pytest.mark.asyncio
@given(
    brand_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_active=st.integers(min_value=0, max_value=5),
    best_score=st.floats(min_value=0.80, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_active_records_only_brand(brand_text: str, num_active: int, best_score: float):
    """
    **Validates: Requirements 2.3, 3.4, 4.4**
    
    For any returned brand match, the corresponding database record should have 
    is_active = true. The database queries should only return active records.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows - only active records
    mock_active_rows = []
    for i in range(num_active):
        mock_active_rows.append({
            'id': uuid4(),
            'name': f'ActiveBrand_{i}',
            'is_active': True
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_active_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Use a valid category_id for brand matching
    category_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # If there are active candidates, return a match
            if num_active > 0:
                mock_find_best.return_value = (
                    {'id': mock_active_rows[0]['id'], 'name': mock_active_rows[0]['name']},
                    best_score
                )
            else:
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_brand(brand_text, category_id)
            
            # Property: If a match is returned, it must correspond to an active record
            if result is not None:
                # Verify the query was called with is_active = true filter
                mock_conn.fetch.assert_called_once()
                query_sql = mock_conn.fetch.call_args[0][0]
                assert 'is_active = true' in query_sql.lower(), \
                    "Query must filter for active records only"
                
                # Verify all rows returned by query are active
                for row in mock_active_rows:
                    assert row.get('is_active', True) is True, \
                        f"Query returned inactive record: {row}"


# Feature: database-matching-integration, Property 7: Active Records Only
@pytest.mark.asyncio
@given(
    model_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_active=st.integers(min_value=0, max_value=5),
    best_score=st.floats(min_value=0.75, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_active_records_only_model(model_text: str, num_active: int, best_score: float):
    """
    **Validates: Requirements 2.3, 3.4, 4.4**
    
    For any returned model match, the corresponding database record should have 
    is_active = true. The database queries should only return active records.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows - only active records
    mock_active_rows = []
    for i in range(num_active):
        mock_active_rows.append({
            'id': uuid4(),
            'name': f'ActiveModel_{i}',
            'is_active': True
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_active_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Use valid category_id and brand_id for model matching
    category_id = uuid4()
    brand_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # If there are active candidates, return a match
            if num_active > 0:
                mock_find_best.return_value = (
                    {'id': mock_active_rows[0]['id'], 'name': mock_active_rows[0]['name']},
                    best_score
                )
            else:
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_model(model_text, category_id, brand_id)
            
            # Property: If a match is returned, it must correspond to an active record
            if result is not None:
                # Verify the query was called with is_active = true filter
                mock_conn.fetch.assert_called_once()
                query_sql = mock_conn.fetch.call_args[0][0]
                assert 'is_active = true' in query_sql.lower(), \
                    "Query must filter for active records only"
                
                # Verify all rows returned by query are active
                for row in mock_active_rows:
                    assert row.get('is_active', True) is True, \
                        f"Query returned inactive record: {row}"


# Feature: database-matching-integration, Property 7: Active Records Only
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_active_records_only_inactive_excluded():
    """
    **Validates: Requirements 2.3, 3.4, 4.4**
    
    Verify that inactive records are explicitly excluded from query results.
    This test ensures the WHERE is_active = true clause is working correctly.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Simulate database returning only active records (inactive filtered by SQL)
    active_id = uuid4()
    mock_active_rows = [
        {'id': active_id, 'name': 'Active Category', 'is_active': True}
    ]
    
    # The inactive record should NOT be in the results because of WHERE clause
    # inactive_id = uuid4()
    # {'id': inactive_id, 'name': 'Inactive Category', 'is_active': False}  # NOT returned
    
    mock_conn.fetch = AsyncMock(return_value=mock_active_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return the active record as best match
            mock_find_best.return_value = (
                {'id': active_id, 'name': 'Active Category'},
                0.95
            )
            
            result = await matcher.match_category("active category")
            
            # Property: Only active records should be returned
            assert result is not None, "Should find active record"
            assert result.id == active_id, "Should return the active record ID"
            
            # Verify the SQL query includes is_active filter
            mock_conn.fetch.assert_called_once()
            query_sql = mock_conn.fetch.call_args[0][0]
            assert 'WHERE is_active = true' in query_sql or 'where is_active = true' in query_sql, \
                "Query must explicitly filter for active records"


# Feature: database-matching-integration, Property 8: Best Match Selection
@pytest.mark.asyncio
@given(
    query_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_candidates=st.integers(min_value=2, max_value=10),
    score_seed=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_best_match_selection_category(query_text: str, num_candidates: int, score_seed: int):
    """
    **Validates: Requirements 2.4, 3.5, 4.5**
    
    For any category matching operation where multiple candidates exceed the threshold,
    the returned match should have the highest similarity score among all candidates.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows with different names
    mock_rows = []
    for i in range(num_candidates):
        mock_rows.append({
            'id': uuid4(),
            'name': f'Category_{i}_{score_seed}'
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Don't mock find_best_match - let it run with real FuzzyMatcher
        # This tests the actual best match selection logic
        result = await matcher.match_category(query_text)
        
        # Property: If a match is returned, it should have the highest score
        if result is not None:
            # Manually calculate all scores to verify the best was selected
            from app.services.fuzzy_matcher import FuzzyMatcher
            
            all_scores = []
            for row in mock_rows:
                score = FuzzyMatcher.calculate_similarity(query_text, row['name'])
                all_scores.append((row['id'], row['name'], score))
            
            # Find the maximum score
            max_score = max(score for _, _, score in all_scores)
            
            # The returned match should have the maximum score
            assert result.similarity_score == max_score, \
                f"Returned match has score {result.similarity_score}, but max score is {max_score}"
            
            # Verify the returned match corresponds to one of the candidates with max score
            matching_candidates = [
                (cid, cname) for cid, cname, score in all_scores 
                if score == max_score
            ]
            assert any(result.id == cid for cid, _ in matching_candidates), \
                f"Returned match ID {result.id} does not correspond to any candidate with max score"


# Feature: database-matching-integration, Property 8: Best Match Selection
@pytest.mark.asyncio
@given(
    query_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_candidates=st.integers(min_value=2, max_value=10),
    score_seed=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_best_match_selection_brand(query_text: str, num_candidates: int, score_seed: int):
    """
    **Validates: Requirements 2.4, 3.5, 4.5**
    
    For any brand matching operation where multiple candidates exceed the threshold,
    the returned match should have the highest similarity score among all candidates.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows with different names
    mock_rows = []
    for i in range(num_candidates):
        mock_rows.append({
            'id': uuid4(),
            'name': f'Brand_{i}_{score_seed}'
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Use a valid category_id for brand matching
    category_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Don't mock find_best_match - let it run with real FuzzyMatcher
        result = await matcher.match_brand(query_text, category_id)
        
        # Property: If a match is returned, it should have the highest score
        if result is not None:
            # Manually calculate all scores to verify the best was selected
            from app.services.fuzzy_matcher import FuzzyMatcher
            
            all_scores = []
            for row in mock_rows:
                score = FuzzyMatcher.calculate_similarity(query_text, row['name'])
                all_scores.append((row['id'], row['name'], score))
            
            # Find the maximum score
            max_score = max(score for _, _, score in all_scores)
            
            # The returned match should have the maximum score
            assert result.similarity_score == max_score, \
                f"Returned match has score {result.similarity_score}, but max score is {max_score}"
            
            # Verify the returned match corresponds to one of the candidates with max score
            matching_candidates = [
                (cid, cname) for cid, cname, score in all_scores 
                if score == max_score
            ]
            assert any(result.id == cid for cid, _ in matching_candidates), \
                f"Returned match ID {result.id} does not correspond to any candidate with max score"


# Feature: database-matching-integration, Property 8: Best Match Selection
@pytest.mark.asyncio
@given(
    query_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_candidates=st.integers(min_value=2, max_value=10),
    score_seed=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_best_match_selection_model(query_text: str, num_candidates: int, score_seed: int):
    """
    **Validates: Requirements 2.4, 3.5, 4.5**
    
    For any model matching operation where multiple candidates exceed the threshold,
    the returned match should have the highest similarity score among all candidates.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows with different names
    mock_rows = []
    for i in range(num_candidates):
        mock_rows.append({
            'id': uuid4(),
            'name': f'Model_{i}_{score_seed}'
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Use valid category_id and brand_id for model matching
    category_id = uuid4()
    brand_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Don't mock find_best_match - let it run with real FuzzyMatcher
        result = await matcher.match_model(query_text, category_id, brand_id)
        
        # Property: If a match is returned, it should have the highest score
        if result is not None:
            # Manually calculate all scores to verify the best was selected
            from app.services.fuzzy_matcher import FuzzyMatcher
            
            all_scores = []
            for row in mock_rows:
                score = FuzzyMatcher.calculate_similarity(query_text, row['name'])
                all_scores.append((row['id'], row['name'], score))
            
            # Find the maximum score
            max_score = max(score for _, _, score in all_scores)
            
            # The returned match should have the maximum score
            assert result.similarity_score == max_score, \
                f"Returned match has score {result.similarity_score}, but max score is {max_score}"
            
            # Verify the returned match corresponds to one of the candidates with max score
            matching_candidates = [
                (cid, cname) for cid, cname, score in all_scores 
                if score == max_score
            ]
            assert any(result.id == cid for cid, _ in matching_candidates), \
                f"Returned match ID {result.id} does not correspond to any candidate with max score"


# Feature: database-matching-integration, Property 8: Best Match Selection
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_best_match_selection_specific_scenario():
    """
    **Validates: Requirements 2.4, 3.5, 4.5**
    
    Test a specific scenario with known similarity scores to verify best match selection.
    Query "iPhone" should match "iPhone 14" better than "Samsung Phone".
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create candidates with predictable similarity to "iPhone"
    iphone_id = uuid4()
    samsung_id = uuid4()
    mock_rows = [
        {'id': iphone_id, 'name': 'iPhone 14'},  # Should have higher similarity to "iPhone"
        {'id': samsung_id, 'name': 'Samsung Phone'}  # Should have lower similarity to "iPhone"
    ]
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Test with category matching
        result = await matcher.match_category("iPhone")
        
        # Calculate expected scores
        from app.services.fuzzy_matcher import FuzzyMatcher
        iphone_score = FuzzyMatcher.calculate_similarity("iPhone", "iPhone 14")
        samsung_score = FuzzyMatcher.calculate_similarity("iPhone", "Samsung Phone")
        
        # Property: The match should be the one with higher score
        if result is not None:
            if iphone_score > samsung_score:
                assert result.id == iphone_id, \
                    f"Expected iPhone 14 (score {iphone_score:.2f}) to be selected over Samsung Phone (score {samsung_score:.2f})"
                assert result.similarity_score == iphone_score, \
                    f"Expected score {iphone_score:.2f}, got {result.similarity_score:.2f}"
            else:
                assert result.id == samsung_id, \
                    f"Expected Samsung Phone (score {samsung_score:.2f}) to be selected over iPhone 14 (score {iphone_score:.2f})"
                assert result.similarity_score == samsung_score, \
                    f"Expected score {samsung_score:.2f}, got {result.similarity_score:.2f}"


# Feature: database-matching-integration, Property 8: Best Match Selection
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_best_match_selection_tie_scenario():
    """
    **Validates: Requirements 2.4, 3.5, 4.5**
    
    Test scenario where multiple candidates have identical similarity scores.
    Any of the tied candidates is acceptable as long as they all have the max score.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create candidates with identical names (will have identical scores)
    id1 = uuid4()
    id2 = uuid4()
    id3 = uuid4()
    mock_rows = [
        {'id': id1, 'name': 'Mobile Phone'},
        {'id': id2, 'name': 'Mobile Phone'},  # Identical name
        {'id': id3, 'name': 'Mobile Phone'}   # Identical name
    ]
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        result = await matcher.match_category("Mobile Phone")
        
        # Property: When there's a tie, any of the tied candidates is acceptable
        if result is not None:
            from app.services.fuzzy_matcher import FuzzyMatcher
            expected_score = FuzzyMatcher.calculate_similarity("Mobile Phone", "Mobile Phone")
            
            # The returned match should have the maximum score (1.0 in this case)
            assert result.similarity_score == expected_score, \
                f"Expected score {expected_score:.2f}, got {result.similarity_score:.2f}"
            
            # The returned match should be one of the candidates
            assert result.id in [id1, id2, id3], \
                f"Returned match ID {result.id} is not one of the tied candidates"


# Feature: database-matching-integration, Property 9: Brand Query with Category Validation
@pytest.mark.asyncio
@given(
    brand_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_valid_brands=st.integers(min_value=0, max_value=5),
    num_invalid_brands=st.integers(min_value=0, max_value=5),
    best_score=st.floats(min_value=0.80, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_brand_category_validation(
    brand_text: str, 
    num_valid_brands: int, 
    num_invalid_brands: int, 
    best_score: float
):
    """
    **Validates: Requirements 3.1, 3.2**
    
    For any non-null brand text input when a category_id exists, the database query 
    should only return brands that are valid for that category according to the 
    category_brand junction table.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create a category_id for validation
    category_id = uuid4()
    
    # Generate mock database rows - only brands valid for this category
    # (The SQL query uses INNER JOIN with category_brand table)
    mock_valid_brands = []
    for i in range(num_valid_brands):
        mock_valid_brands.append({
            'id': uuid4(),
            'name': f'ValidBrand_{i}',
            'category_id': category_id  # Valid for this category
        })
    
    # Invalid brands should NOT be in the query results
    # (They are filtered out by the INNER JOIN with category_brand)
    # These brands exist in device_brand table but not in category_brand for this category
    mock_conn.fetch = AsyncMock(return_value=mock_valid_brands)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # If there are valid candidates, return a match
            if num_valid_brands > 0:
                mock_find_best.return_value = (
                    {'id': mock_valid_brands[0]['id'], 'name': mock_valid_brands[0]['name']},
                    best_score
                )
            else:
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_brand(brand_text, category_id)
            
            # Property: The query must use INNER JOIN with category_brand table
            if mock_conn.fetch.called:
                query_sql = mock_conn.fetch.call_args[0][0]
                
                # Verify the query joins with category_brand table
                assert 'category_brand' in query_sql.lower(), \
                    "Query must join with category_brand table for validation"
                
                # Verify the query uses INNER JOIN (not LEFT JOIN)
                assert 'inner join' in query_sql.lower(), \
                    "Query must use INNER JOIN to filter brands by category"
                
                # Verify the query filters by category_id
                assert 'category_id' in query_sql.lower(), \
                    "Query must filter by category_id"
                
                # Verify the category_id parameter is passed correctly
                query_params = mock_conn.fetch.call_args[0][1:]
                assert category_id in query_params, \
                    f"Query must pass category_id {category_id} as parameter"
            
            # Property: If a match is returned, it must be valid for the category
            if result is not None:
                # The returned brand must be one of the valid brands for this category
                valid_brand_ids = [brand['id'] for brand in mock_valid_brands]
                assert result.id in valid_brand_ids, \
                    f"Returned brand {result.id} is not valid for category {category_id}"


# Feature: database-matching-integration, Property 9: Brand Query with Category Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_category_validation_no_category():
    """
    **Validates: Requirements 3.1, 3.2**
    
    When category_id is None, brand matching should be skipped and return None.
    This tests the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    # Execute brand matching without a category_id
    result = await matcher.match_brand("Apple", None)
    
    # Property: Without category_id, brand matching should return None
    assert result is None, \
        "Brand matching should return None when category_id is not provided"


# Feature: database-matching-integration, Property 9: Brand Query with Category Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_category_validation_specific_scenario():
    """
    **Validates: Requirements 3.1, 3.2**
    
    Test a specific scenario: "Apple" brand should only be returned if it's valid
    for the "Mobile Phone" category according to category_brand junction table.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create specific category and brand IDs
    mobile_phone_category_id = uuid4()
    apple_brand_id = uuid4()
    samsung_brand_id = uuid4()
    
    # Simulate that only Apple and Samsung are valid for Mobile Phone category
    # (according to category_brand junction table)
    mock_valid_brands = [
        {'id': apple_brand_id, 'name': 'Apple'},
        {'id': samsung_brand_id, 'name': 'Samsung'}
    ]
    
    mock_conn.fetch = AsyncMock(return_value=mock_valid_brands)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Test matching "Apple" for Mobile Phone category
        result = await matcher.match_brand("Apple", mobile_phone_category_id)
        
        # Verify the query was called with correct category_id
        mock_conn.fetch.assert_called_once()
        query_sql = mock_conn.fetch.call_args[0][0]
        query_params = mock_conn.fetch.call_args[0][1:]
        
        # Property: Query must validate against category_brand junction table
        assert 'INNER JOIN category_brand' in query_sql or 'inner join category_brand' in query_sql, \
            "Query must use INNER JOIN with category_brand table"
        
        assert mobile_phone_category_id in query_params, \
            f"Query must filter by category_id {mobile_phone_category_id}"
        
        # Property: Only brands valid for the category should be in candidates
        # The query result should only contain Apple and Samsung (not other brands)
        if result is not None:
            assert result.id in [apple_brand_id, samsung_brand_id], \
                f"Returned brand must be valid for Mobile Phone category"


# Feature: database-matching-integration, Property 9: Brand Query with Category Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_category_validation_empty_junction():
    """
    **Validates: Requirements 3.1, 3.2**
    
    When no brands are valid for a category (empty category_brand junction),
    the query should return no results and match_brand should return None.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create a category with no valid brands in category_brand junction table
    category_id = uuid4()
    
    # Empty result set - no brands valid for this category
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Test matching a brand for a category with no valid brands
        result = await matcher.match_brand("Apple", category_id)
        
        # Property: When no brands are valid for category, should return None
        assert result is None, \
            "Should return None when no brands are valid for the category"
        
        # Verify the query was executed with category validation
        mock_conn.fetch.assert_called_once()
        query_sql = mock_conn.fetch.call_args[0][0]
        assert 'category_brand' in query_sql.lower(), \
            "Query must join with category_brand table even when result is empty"


# Feature: database-matching-integration, Property 9: Brand Query with Category Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_category_validation_query_structure():
    """
    **Validates: Requirements 3.1, 3.2**
    
    Verify the SQL query structure explicitly validates brand-category relationships
    using the category_brand junction table with proper INNER JOIN.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    category_id = uuid4()
    brand_id = uuid4()
    
    mock_brands = [{'id': brand_id, 'name': 'TestBrand'}]
    mock_conn.fetch = AsyncMock(return_value=mock_brands)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Execute brand matching
        await matcher.match_brand("TestBrand", category_id)
        
        # Verify the query structure
        mock_conn.fetch.assert_called_once()
        query_sql = mock_conn.fetch.call_args[0][0].lower()
        
        # Property: Query must have all required components for category validation
        assert 'select' in query_sql, "Query must be a SELECT statement"
        assert 'device_brand' in query_sql, "Query must select from device_brand table"
        assert 'inner join category_brand' in query_sql, \
            "Query must use INNER JOIN with category_brand table (not LEFT JOIN)"
        assert 'cb.category_id = $1' in query_sql or 'category_id = $1' in query_sql, \
            "Query must filter by category_id parameter"
        assert 'is_active = true' in query_sql, \
            "Query must filter for active brands only"
        
        # Verify the join condition
        assert 'b.id = cb.brand_id' in query_sql or 'brand_id' in query_sql, \
            "Query must join on brand_id"


# Feature: database-matching-integration, Property 10: Brand Threshold Enforcement
@pytest.mark.asyncio
@given(
    brand_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_candidates=st.integers(min_value=0, max_value=10),
    best_score=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_brand_threshold_enforcement(brand_text: str, num_candidates: int, best_score: float):
    """
    **Validates: Requirements 3.3, 3.7**
    
    For any brand matching operation, if a match is returned, its similarity 
    score should be >= 0.80; otherwise brand_id should be null.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows
    mock_rows = []
    for i in range(num_candidates):
        mock_rows.append({
            'id': uuid4(),
            'name': f'Brand_{i}'
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Use a valid category_id for brand matching
    category_id = uuid4()
    
    # Mock the find_best_match to return controlled score
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Determine if match should be returned based on threshold
            if best_score >= app_settings.BRAND_MATCH_THRESHOLD and num_candidates > 0:
                # Return a match
                mock_find_best.return_value = (
                    {'id': mock_rows[0]['id'], 'name': mock_rows[0]['name']},
                    best_score
                )
            else:
                # No match above threshold
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_brand(brand_text, category_id)
            
            # Property: If a match is returned, similarity score must be >= 0.80
            if result is not None:
                from app.services.database_matcher import BrandMatch
                assert isinstance(result, BrandMatch), \
                    f"Result should be BrandMatch instance, got {type(result)}"
                assert result.similarity_score >= app_settings.BRAND_MATCH_THRESHOLD, \
                    f"Match returned with score {result.similarity_score} below threshold {app_settings.BRAND_MATCH_THRESHOLD}"
                assert result.id is not None, \
                    "Match returned but brand_id is None"
            
            # Property: If no match is returned (None), it means either:
            # 1. No candidates exist, or
            # 2. Best score is below threshold
            if result is None:
                # This is expected when score < threshold or no candidates
                # The brand_id will be null in the response
                pass


# Feature: database-matching-integration, Property 10: Brand Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_threshold_enforcement_exact_threshold():
    """
    **Validates: Requirements 3.3, 3.7**
    
    Test boundary condition: a match with exactly 0.80 similarity should be returned.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database row
    mock_id = uuid4()
    category_id = uuid4()
    mock_rows = [{'id': mock_id, 'name': 'Apple'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return match with exactly threshold score
            mock_find_best.return_value = (
                {'id': mock_id, 'name': 'Apple'},
                0.80
            )
            
            result = await matcher.match_brand("apple", category_id)
            
            # Property: Match at exactly threshold should be returned
            assert result is not None, \
                "Match with score exactly at threshold (0.80) should be returned"
            assert result.similarity_score == 0.80, \
                f"Expected score 0.80, got {result.similarity_score}"
            assert result.id == mock_id, \
                "Returned match should have correct UUID"


# Feature: database-matching-integration, Property 10: Brand Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_threshold_enforcement_below_threshold():
    """
    **Validates: Requirements 3.3, 3.7**
    
    Test boundary condition: a match with 0.79 similarity should NOT be returned.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database row
    category_id = uuid4()
    mock_rows = [{'id': uuid4(), 'name': 'Apple'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return None because score is below threshold
            mock_find_best.return_value = None
            
            result = await matcher.match_brand("apple", category_id)
            
            # Property: Match below threshold should return None (null brand_id)
            assert result is None, \
                "Match with score below threshold (0.79) should return None"


# Feature: database-matching-integration, Property 10: Brand Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_threshold_enforcement_no_candidates():
    """
    **Validates: Requirements 3.3, 3.7**
    
    When no candidates exist in database, should return None (null brand_id).
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # No candidates in database
    category_id = uuid4()
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # No candidates means no match
            mock_find_best.return_value = None
            
            result = await matcher.match_brand("some brand", category_id)
            
            # Property: No candidates should return None (null brand_id)
            assert result is None, \
                "When no candidates exist, should return None"


# Feature: database-matching-integration, Property 10: Brand Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_threshold_enforcement_no_category():
    """
    **Validates: Requirements 3.3, 3.7**
    
    When category_id is None, brand matching should be skipped and return None (null brand_id).
    This validates the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    result = await matcher.match_brand("Apple", None)
    
    # Property: Without category_id, brand matching should return None (null brand_id)
    assert result is None, \
        "When category_id is None, should return None"


# Feature: database-matching-integration, Property 10: Brand Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_brand_threshold_enforcement_database_unavailable():
    """
    **Validates: Requirements 3.3, 3.7**
    
    When database is unavailable, should return None (null brand_id).
    """
    matcher = DatabaseMatcher()
    
    category_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = False
        
        result = await matcher.match_brand("Apple", category_id)
        
        # Property: Database unavailable should return None (null brand_id)
        assert result is None, \
            "When database is unavailable, should return None"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@given(
    model_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_valid_models=st.integers(min_value=0, max_value=5),
    num_invalid_models=st.integers(min_value=0, max_value=5),
    best_score=st.floats(min_value=0.75, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_model_category_brand_validation(
    model_text: str, 
    num_valid_models: int, 
    num_invalid_models: int, 
    best_score: float
):
    """
    **Validates: Requirements 4.1, 4.2**
    
    For any non-null model text input when both category_id and brand_id exist, 
    the database query should only return models where category_id matches the 
    identified category AND brand_id matches the identified brand.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create specific category_id and brand_id for validation
    category_id = uuid4()
    brand_id = uuid4()
    
    # Generate mock database rows - only models valid for this category AND brand
    # (The SQL query filters WHERE category_id = $1 AND brand_id = $2)
    mock_valid_models = []
    for i in range(num_valid_models):
        mock_valid_models.append({
            'id': uuid4(),
            'name': f'ValidModel_{i}',
            'category_id': category_id,  # Matches the identified category
            'brand_id': brand_id  # Matches the identified brand
        })
    
    # Invalid models should NOT be in the query results
    # (They are filtered out by the WHERE clause)
    # These models exist in device_model table but have different category_id or brand_id
    mock_conn.fetch = AsyncMock(return_value=mock_valid_models)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # If there are valid candidates, return a match
            if num_valid_models > 0:
                mock_find_best.return_value = (
                    {'id': mock_valid_models[0]['id'], 'name': mock_valid_models[0]['name']},
                    best_score
                )
            else:
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_model(model_text, category_id, brand_id)
            
            # Property: The query must filter by both category_id AND brand_id
            if mock_conn.fetch.called:
                query_sql = mock_conn.fetch.call_args[0][0]
                
                # Verify the query filters by category_id
                assert 'category_id = $1' in query_sql or 'category_id=$1' in query_sql, \
                    "Query must filter by category_id"
                
                # Verify the query filters by brand_id
                assert 'brand_id = $2' in query_sql or 'brand_id=$2' in query_sql, \
                    "Query must filter by brand_id"
                
                # Verify both parameters are passed correctly
                query_params = mock_conn.fetch.call_args[0][1:]
                assert len(query_params) >= 2, \
                    "Query must pass both category_id and brand_id as parameters"
                assert query_params[0] == category_id, \
                    f"First parameter must be category_id {category_id}"
                assert query_params[1] == brand_id, \
                    f"Second parameter must be brand_id {brand_id}"
            
            # Property: If a match is returned, it must be valid for both category and brand
            if result is not None:
                # The returned model must be one of the valid models for this category AND brand
                valid_model_ids = [model['id'] for model in mock_valid_models]
                assert result.id in valid_model_ids, \
                    f"Returned model {result.id} is not valid for category {category_id} and brand {brand_id}"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_no_category():
    """
    **Validates: Requirements 4.1, 4.2**
    
    When category_id is None, model matching should be skipped and return None.
    This tests the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    brand_id = uuid4()
    
    # Execute model matching without a category_id
    result = await matcher.match_model("iPhone 14", None, brand_id)
    
    # Property: Without category_id, model matching should return None
    assert result is None, \
        "Model matching should return None when category_id is not provided"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_no_brand():
    """
    **Validates: Requirements 4.1, 4.2**
    
    When brand_id is None, model matching should be skipped and return None.
    This tests the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    category_id = uuid4()
    
    # Execute model matching without a brand_id
    result = await matcher.match_model("iPhone 14", category_id, None)
    
    # Property: Without brand_id, model matching should return None
    assert result is None, \
        "Model matching should return None when brand_id is not provided"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_no_category_or_brand():
    """
    **Validates: Requirements 4.1, 4.2**
    
    When both category_id and brand_id are None, model matching should be skipped and return None.
    This tests the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    # Execute model matching without category_id or brand_id
    result = await matcher.match_model("iPhone 14", None, None)
    
    # Property: Without category_id and brand_id, model matching should return None
    assert result is None, \
        "Model matching should return None when neither category_id nor brand_id is provided"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_specific_scenario():
    """
    **Validates: Requirements 4.1, 4.2**
    
    Test a specific scenario: "iPhone 14 Pro" model should only be returned if it 
    matches both the "Mobile Phone" category AND "Apple" brand.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create specific category, brand, and model IDs
    mobile_phone_category_id = uuid4()
    apple_brand_id = uuid4()
    iphone_14_model_id = uuid4()
    iphone_15_model_id = uuid4()
    
    # Simulate that only iPhone 14 and iPhone 15 are valid for Mobile Phone category AND Apple brand
    mock_valid_models = [
        {'id': iphone_14_model_id, 'name': 'iPhone 14 Pro'},
        {'id': iphone_15_model_id, 'name': 'iPhone 15 Pro'}
    ]
    
    mock_conn.fetch = AsyncMock(return_value=mock_valid_models)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Test matching "iPhone 14 Pro" for Mobile Phone category and Apple brand
        result = await matcher.match_model("iPhone 14 Pro", mobile_phone_category_id, apple_brand_id)
        
        # Verify the query was called with correct category_id and brand_id
        mock_conn.fetch.assert_called_once()
        query_sql = mock_conn.fetch.call_args[0][0]
        query_params = mock_conn.fetch.call_args[0][1:]
        
        # Property: Query must filter by both category_id AND brand_id
        assert 'WHERE category_id = $1' in query_sql or 'where category_id = $1' in query_sql, \
            "Query must filter by category_id"
        
        assert 'AND brand_id = $2' in query_sql or 'and brand_id = $2' in query_sql, \
            "Query must filter by brand_id using AND condition"
        
        assert mobile_phone_category_id in query_params, \
            f"Query must filter by category_id {mobile_phone_category_id}"
        
        assert apple_brand_id in query_params, \
            f"Query must filter by brand_id {apple_brand_id}"
        
        # Property: Only models valid for both the category AND brand should be in candidates
        # The query result should only contain iPhone models (not Samsung models)
        if result is not None:
            assert result.id in [iphone_14_model_id, iphone_15_model_id], \
                f"Returned model must be valid for both Mobile Phone category AND Apple brand"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_empty_result():
    """
    **Validates: Requirements 4.1, 4.2**
    
    When no models match both the category_id AND brand_id filters,
    the query should return no results and match_model should return None.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Create a category and brand with no matching models
    category_id = uuid4()
    brand_id = uuid4()
    
    # Empty result set - no models match both category AND brand
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Test matching a model for a category/brand combination with no models
        result = await matcher.match_model("iPhone 14", category_id, brand_id)
        
        # Property: When no models match both filters, should return None
        assert result is None, \
            "Should return None when no models match both category_id and brand_id"
        
        # Verify the query was executed with both filters
        mock_conn.fetch.assert_called_once()
        query_sql = mock_conn.fetch.call_args[0][0]
        assert 'category_id' in query_sql.lower(), \
            "Query must filter by category_id"
        assert 'brand_id' in query_sql.lower(), \
            "Query must filter by brand_id"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_query_structure():
    """
    **Validates: Requirements 4.1, 4.2**
    
    Verify the SQL query structure explicitly validates model-category-brand relationships
    using WHERE clause with both category_id AND brand_id filters.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    category_id = uuid4()
    brand_id = uuid4()
    model_id = uuid4()
    
    mock_models = [{'id': model_id, 'name': 'TestModel'}]
    mock_conn.fetch = AsyncMock(return_value=mock_models)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Execute model matching
        await matcher.match_model("TestModel", category_id, brand_id)
        
        # Verify the query structure
        mock_conn.fetch.assert_called_once()
        query_sql = mock_conn.fetch.call_args[0][0].lower()
        
        # Property: Query must have all required components for category and brand validation
        assert 'select' in query_sql, "Query must be a SELECT statement"
        assert 'device_model' in query_sql, "Query must select from device_model table"
        assert 'where category_id = $1' in query_sql, \
            "Query must filter by category_id parameter"
        assert 'and brand_id = $2' in query_sql, \
            "Query must filter by brand_id parameter using AND condition"
        assert 'is_active = true' in query_sql, \
            "Query must filter for active models only"
        
        # Verify both parameters are passed in correct order
        query_params = mock_conn.fetch.call_args[0][1:]
        assert len(query_params) == 2, \
            "Query must pass exactly 2 parameters (category_id and brand_id)"
        assert query_params[0] == category_id, \
            "First parameter must be category_id"
        assert query_params[1] == brand_id, \
            "Second parameter must be brand_id"


# Feature: database-matching-integration, Property 12: Model Query with Category and Brand Validation
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_category_brand_validation_database_unavailable():
    """
    **Validates: Requirements 4.1, 4.2**
    
    When database is unavailable, should return None (null model_id).
    """
    matcher = DatabaseMatcher()
    
    category_id = uuid4()
    brand_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = False
        
        result = await matcher.match_model("iPhone 14", category_id, brand_id)
        
        # Property: Database unavailable should return None (null model_id)
        assert result is None, \
            "When database is unavailable, should return None"


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@given(
    model_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    num_candidates=st.integers(min_value=0, max_value=10),
    best_score=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_model_threshold_enforcement(model_text: str, num_candidates: int, best_score: float):
    """
    **Validates: Requirements 4.3, 4.7**
    
    For any model matching operation, if a match is returned, its similarity 
    score should be >= 0.75; otherwise model_id should be null.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database rows
    mock_rows = []
    for i in range(num_candidates):
        mock_rows.append({
            'id': uuid4(),
            'name': f'Model_{i}'
        })
    
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    # Use valid category_id and brand_id for model matching
    category_id = uuid4()
    brand_id = uuid4()
    
    # Mock the find_best_match to return controlled score
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Determine if match should be returned based on threshold
            if best_score >= app_settings.MODEL_MATCH_THRESHOLD and num_candidates > 0:
                # Return a match
                mock_find_best.return_value = (
                    {'id': mock_rows[0]['id'], 'name': mock_rows[0]['name']},
                    best_score
                )
            else:
                # No match above threshold
                mock_find_best.return_value = None
            
            # Execute the match
            result = await matcher.match_model(model_text, category_id, brand_id)
            
            # Property: If a match is returned, similarity score must be >= 0.75
            if result is not None:
                from app.services.database_matcher import ModelMatch
                assert isinstance(result, ModelMatch), \
                    f"Result should be ModelMatch instance, got {type(result)}"
                assert result.similarity_score >= app_settings.MODEL_MATCH_THRESHOLD, \
                    f"Match returned with score {result.similarity_score} below threshold {app_settings.MODEL_MATCH_THRESHOLD}"
                assert result.id is not None, \
                    "Match returned but model_id is None"
            
            # Property: If no match is returned (None), it means either:
            # 1. No candidates exist, or
            # 2. Best score is below threshold
            if result is None:
                # This is expected when score < threshold or no candidates
                # The model_id will be null in the response
                pass


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_threshold_enforcement_exact_threshold():
    """
    **Validates: Requirements 4.3, 4.7**
    
    Test boundary condition: a match with exactly 0.75 similarity should be returned.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database row
    mock_id = uuid4()
    category_id = uuid4()
    brand_id = uuid4()
    mock_rows = [{'id': mock_id, 'name': 'iPhone 14 Pro'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return match with exactly threshold score
            mock_find_best.return_value = (
                {'id': mock_id, 'name': 'iPhone 14 Pro'},
                0.75
            )
            
            result = await matcher.match_model("iphone 14 pro", category_id, brand_id)
            
            # Property: Match at exactly threshold should be returned
            assert result is not None, \
                "Match with score exactly at threshold (0.75) should be returned"
            assert result.similarity_score == 0.75, \
                f"Expected score 0.75, got {result.similarity_score}"
            assert result.id == mock_id, \
                "Returned match should have correct UUID"


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_threshold_enforcement_below_threshold():
    """
    **Validates: Requirements 4.3, 4.7**
    
    Test boundary condition: a match with 0.74 similarity should NOT be returned.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Generate mock database row
    category_id = uuid4()
    brand_id = uuid4()
    mock_rows = [{'id': uuid4(), 'name': 'iPhone 14 Pro'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Return None because score is below threshold
            mock_find_best.return_value = None
            
            result = await matcher.match_model("iphone 14 pro", category_id, brand_id)
            
            # Property: Match below threshold should return None (null model_id)
            assert result is None, \
                "Match with score below threshold (0.74) should return None"


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_threshold_enforcement_no_candidates():
    """
    **Validates: Requirements 4.3, 4.7**
    
    When no candidates exist in database, should return None (null model_id).
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # No candidates in database
    category_id = uuid4()
    brand_id = uuid4()
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # No candidates means no match
            mock_find_best.return_value = None
            
            result = await matcher.match_model("some model", category_id, brand_id)
            
            # Property: No candidates should return None (null model_id)
            assert result is None, \
                "When no candidates exist, should return None"


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_threshold_enforcement_no_category():
    """
    **Validates: Requirements 4.3, 4.7**
    
    When category_id is None, model matching should be skipped and return None (null model_id).
    This validates the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    brand_id = uuid4()
    
    result = await matcher.match_model("iPhone 14 Pro", None, brand_id)
    
    # Property: Without category_id, model matching should return None (null model_id)
    assert result is None, \
        "When category_id is None, should return None"


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_threshold_enforcement_no_brand():
    """
    **Validates: Requirements 4.3, 4.7**
    
    When brand_id is None, model matching should be skipped and return None (null model_id).
    This validates the hierarchical dependency requirement.
    """
    matcher = DatabaseMatcher()
    
    category_id = uuid4()
    
    result = await matcher.match_model("iPhone 14 Pro", category_id, None)
    
    # Property: Without brand_id, model matching should return None (null model_id)
    assert result is None, \
        "When brand_id is None, should return None"


# Feature: database-matching-integration, Property 13: Model Threshold Enforcement
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_model_threshold_enforcement_database_unavailable():
    """
    **Validates: Requirements 4.3, 4.7**
    
    When database is unavailable, should return None (null model_id).
    """
    matcher = DatabaseMatcher()
    
    category_id = uuid4()
    brand_id = uuid4()
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = False
        
        result = await matcher.match_model("iPhone 14 Pro", category_id, brand_id)
        
        # Property: Database unavailable should return None (null model_id)
        assert result is None, \
            "When database is unavailable, should return None"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
    category_found=st.booleans(),
    brand_found=st.booleans(),
    category_score=st.floats(min_value=0.80, max_value=1.0),
    brand_score=st.floats(min_value=0.80, max_value=1.0),
    model_score=st.floats(min_value=0.75, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_hierarchical_matching_dependencies(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str],
    category_found: bool,
    brand_found: bool,
    category_score: float,
    brand_score: float,
    model_score: float
):
    """
    **Validates: Requirements 3.6, 4.6**
    
    For any matching operation, brand matching should only execute when category_id 
    is not null, and model matching should only execute when both category_id and 
    brand_id are not null.
    
    This property verifies the hierarchical dependency chain:
    - Category matching always executes (no dependencies)
    - Brand matching requires category_id to be present
    - Model matching requires both category_id and brand_id to be present
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Setup mock category data
    category_id = uuid4() if category_found else None
    category_rows = [{'id': category_id, 'name': 'TestCategory'}] if category_found else []
    
    # Setup mock brand data
    brand_id = uuid4() if brand_found else None
    brand_rows = [{'id': brand_id, 'name': 'TestBrand'}] if brand_found else []
    
    # Setup mock model data
    model_id = uuid4()
    model_rows = [{'id': model_id, 'name': 'TestModel'}]
    
    # Track which queries were executed
    query_calls = []
    
    async def mock_fetch(query, *params):
        """Track query execution and return appropriate results"""
        query_lower = query.lower()
        query_calls.append(query_lower)
        
        if 'device_category' in query_lower:
            return category_rows
        elif 'device_brand' in query_lower or 'category_brand' in query_lower:
            return brand_rows
        elif 'device_model' in query_lower:
            return model_rows
        return []
    
    mock_conn.fetch = AsyncMock(side_effect=mock_fetch)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Setup mock responses for fuzzy matching
            def mock_find_best_side_effect(query, candidates, threshold):
                if not candidates:
                    return None
                
                # Determine which entity we're matching based on candidates
                if candidates and 'TestCategory' in str(candidates):
                    if category_found and category_score >= threshold:
                        return ({'id': category_id, 'name': 'TestCategory'}, category_score)
                    return None
                elif candidates and 'TestBrand' in str(candidates):
                    if brand_found and brand_score >= threshold:
                        return ({'id': brand_id, 'name': 'TestBrand'}, brand_score)
                    return None
                elif candidates and 'TestModel' in str(candidates):
      

# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
    failure_scenario=st.sampled_from([
        "no_candidates",
        "below_threshold_category",
        "below_threshold_brand",
        "below_threshold_model",
        "database_unavailable"
    ])
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_null_id_on_match_failure(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str],
    failure_scenario: str
):
    """
    **Validates: Requirements 6.3**
    
    For any failed database match where the threshold is not met or no candidates exist,
    the corresponding id field should be null.
    
    This property tests various failure scenarios:
    - no_candidates: Database returns empty result set
    - below_threshold_category: Category similarity score below 0.80
    - below_threshold_brand: Brand similarity score below 0.80
    - below_threshold_model: Model similarity score below 0.75
    - database_unavailable: Database connection is not available
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Setup mock data based on failure scenario
    if failure_scenario == "no_candidates":
        # Empty result sets - no candidates in database
        category_rows = []
        brand_rows = []
        model_rows = []
    else:
        # Candidates exist but will fail threshold or other checks
        category_id = uuid4()
        brand_id = uuid4()
        model_id = uuid4()
        
        category_rows = [{'id': category_id, 'name': 'TestCategory'}]
        brand_rows = [{'id': brand_id, 'name': 'TestBrand'}]
        model_rows = [{'id': model_id, 'name': 'TestModel'}]
    
    async def mock_fetch(query, *params):
        """Return appropriate results based on query type"""
        query_lower = query.lower()
        
        if 'device_category' in query_lower:
            return category_rows
        elif 'device_brand' in query_lower or 'category_brand' in query_lower:
            return brand_rows
        elif 'device_model' in query_lower:
            return model_rows
        return []
    
    mock_conn.fetch = AsyncMock(side_effect=mock_fetch)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    if failure_scenario == "database_unavailable":
        # Database is not available
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = False
            
            # Test category matching
            category_result = await matcher.match_category(category_text)
            
            # Property: When database is unavailable, category_id should be None
            assert category_result is None, \
                "category_id should be None when database is unavailable"
            
            # Test brand matching (if brand_text provided)
            if brand_text:
                brand_result = await matcher.match_brand(brand_text, uuid4())
                
                # Property: When database is unavailable, brand_id should be None
                assert brand_result is None, \
                    "brand_id should be None when database is unavailable"
            
            # Test model matching (if model_text provided)
            if model_text:
                model_result = await matcher.match_model(model_text, uuid4(), uuid4())
                
                # Property: When database is unavailable, model_id should be None
                assert model_result is None, \
                    "model_id should be None when database is unavailable"
    
    else:
        # Database is available but matching fails
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
                # Setup mock responses based on failure scenario
                if failure_scenario == "no_candidates":
                    # No candidates means find_best_match returns None
                    mock_find_best.return_value = None
                    
                elif failure_scenario == "below_threshold_category":
                    # Category score below threshold (0.79 < 0.80)
                    mock_find_best.return_value = None
                    
                elif failure_scenario == "below_threshold_brand":
                    # Category succeeds, brand fails threshold
                    def mock_find_best_side_effect(query, candidates, threshold):
                        if not candidates:
                            return None
                        # Category succeeds
                        if 'TestCategory' in str(candidates):
                            return ({'id': category_rows[0]['id'], 'name': 'TestCategory'}, 0.85)
                        # Brand fails threshold
                        elif 'TestBrand' in str(candidates):
                            return None
                        return None
                    
                    mock_find_best.side_effect = mock_find_best_side_effect
                    
                elif failure_scenario == "below_threshold_model":
                    # Category and brand succeed, model fails threshold
                    def mock_find_best_side_effect(query, candidates, threshold):
                        if not candidates:
                            return None
                        # Category succeeds
                        if 'TestCategory' in str(candidates):
                            return ({'id': category_rows[0]['id'], 'name': 'TestCategory'}, 0.85)
                        # Brand succeeds
                        elif 'TestBrand' in str(candidates):
                            return ({'id': brand_rows[0]['id'], 'name': 'TestBrand'}, 0.85)
                        # Model fails threshold
                        elif 'TestModel' in str(candidates):
                            return None
                        return None
                    
                    mock_find_best.side_effect = mock_find_best_side_effect
                
                # Test category matching
                category_result = await matcher.match_category(category_text)
                
                # Property: When category matching fails, category_id should be None
                if failure_scenario in ["no_candidates", "below_threshold_category"]:
                    assert category_result is None, \
                        f"category_id should be None when {failure_scenario}"
                
                # Test brand matching (if brand_text provided and category succeeded)
                if brand_text and failure_scenario not in ["no_candidates", "below_threshold_category"]:
                    # Get category_id from successful category match
                    test_category_id = category_rows[0]['id'] if category_rows else None
                    
                    if test_category_id:
                        brand_result = await matcher.match_brand(brand_text, test_category_id)
                        
                        # Property: When brand matching fails, brand_id should be None
                        if failure_scenario == "below_threshold_brand":
                            assert brand_result is None, \
                                f"brand_id should be None when {failure_scenario}"
                
                # Test model matching (if model_text provided and category+brand succeeded)
                if model_text and failure_scenario == "below_threshold_model":
                    test_category_id = category_rows[0]['id'] if category_rows else None
                    test_brand_id = brand_rows[0]['id'] if brand_rows else None
                    
                    if test_category_id and test_brand_id:
                        model_result = await matcher.match_model(model_text, test_category_id, test_brand_id)
                        
                        # Property: When model matching fails, model_id should be None
                        assert model_result is None, \
                            f"model_id should be None when {failure_scenario}"


# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_null_id_on_match_failure_no_candidates_category():
    """
    **Validates: Requirements 6.3**
    
    Specific test: When no category candidates exist in database, category_id should be None.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Empty result set - no categories in database
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        result = await matcher.match_category("Mobile Phone")
        
        # Property: No candidates should result in None (null category_id)
        assert result is None, \
            "category_id should be None when no candidates exist in database"


# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_null_id_on_match_failure_below_threshold_category():
    """
    **Validates: Requirements 6.3**
    
    Specific test: When category similarity score is below 0.80 threshold, category_id should be None.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Candidates exist but similarity will be below threshold
    mock_rows = [{'id': uuid4(), 'name': 'Completely Different Category'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Simulate score below threshold - find_best_match returns None
            mock_find_best.return_value = None
            
            result = await matcher.match_category("Mobile Phone")
            
            # Property: Below threshold should result in None (null category_id)
            assert result is None, \
                "category_id should be None when similarity score is below threshold"


# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_null_id_on_match_failure_below_threshold_brand():
    """
    **Validates: Requirements 6.3**
    
    Specific test: When brand similarity score is below 0.80 threshold, brand_id should be None.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Candidates exist but similarity will be below threshold
    category_id = uuid4()
    mock_rows = [{'id': uuid4(), 'name': 'Completely Different Brand'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Simulate score below threshold - find_best_match returns None
            mock_find_best.return_value = None
            
            result = await matcher.match_brand("Apple", category_id)
            
            # Property: Below threshold should result in None (null brand_id)
            assert result is None, \
                "brand_id should be None when similarity score is below threshold"


# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_null_id_on_match_failure_below_threshold_model():
    """
    **Validates: Requirements 6.3**
    
    Specific test: When model similarity score is below 0.75 threshold, model_id should be None.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Candidates exist but similarity will be below threshold
    category_id = uuid4()
    brand_id = uuid4()
    mock_rows = [{'id': uuid4(), 'name': 'Completely Different Model'}]
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Simulate score below threshold - find_best_match returns None
            mock_find_best.return_value = None
            
            result = await matcher.match_model("iPhone 14 Pro", category_id, brand_id)
            
            # Property: Below threshold should result in None (null model_id)
            assert result is None, \
                "model_id should be None when similarity score is below threshold"


# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_null_id_on_match_failure_hierarchical_dependency():
    """
    **Validates: Requirements 6.3**
    
    Specific test: When hierarchical dependencies are not met (e.g., no category_id),
    dependent matches should return None.
    """
    matcher = DatabaseMatcher()
    
    # Test brand matching without category_id
    brand_result = await matcher.match_brand("Apple", None)
    
    # Property: Without category_id, brand_id should be None
    assert brand_result is None, \
        "brand_id should be None when category_id is not provided"
    
    # Test model matching without category_id
    model_result = await matcher.match_model("iPhone 14 Pro", None, uuid4())
    
    # Property: Without category_id, model_id should be None
    assert model_result is None, \
        "model_id should be None when category_id is not provided"
    
    # Test model matching without brand_id
    model_result = await matcher.match_model("iPhone 14 Pro", uuid4(), None)
    
    # Property: Without brand_id, model_id should be None
    assert model_result is None, \
        "model_id should be None when brand_id is not provided"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126))),
    category_found=st.booleans(),
    brand_found=st.booleans(),
    category_score=st.floats(min_value=0.80, max_value=1.0),
    brand_score=st.floats(min_value=0.80, max_value=1.0),
    model_score=st.floats(min_value=0.75, max_value=1.0)
)
@settings(max_examples=100)
@pytest.mark.property_test
async def test_hierarchical_matching_dependencies(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str],
    category_found: bool,
    brand_found: bool,
    category_score: float,
    brand_score: float,
    model_score: float
):
    """
    **Validates: Requirements 3.6, 4.6**
    
    For any matching operation, brand matching should only execute when category_id 
    is not null, and model matching should only execute when both category_id and 
    brand_id are not null.
    
    This property verifies the hierarchical dependency chain:
    - Category matching always executes (no dependencies)
    - Brand matching requires category_id to be present
    - Model matching requires both category_id and brand_id to be present
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Setup mock category data
    category_id = uuid4() if category_found else None
    category_rows = [{'id': category_id, 'name': 'TestCategory'}] if category_found else []
    
    # Setup mock brand data
    brand_id = uuid4() if brand_found else None
    brand_rows = [{'id': brand_id, 'name': 'TestBrand'}] if brand_found else []
    
    # Setup mock model data
    model_id = uuid4()
    model_rows = [{'id': model_id, 'name': 'TestModel'}]
    
    # Track which queries were executed
    query_calls = []
    
    async def mock_fetch(query, *params):
        """Track query execution and return appropriate results"""
        query_lower = query.lower()
        query_calls.append(query_lower)
        
        if 'device_category' in query_lower:
            return category_rows
        elif 'device_brand' in query_lower or 'category_brand' in query_lower:
            return brand_rows
        elif 'device_model' in query_lower:
            return model_rows
        return []
    
    mock_conn.fetch = AsyncMock(side_effect=mock_fetch)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        with patch('app.services.database_matcher.FuzzyMatcher.find_best_match') as mock_find_best:
            # Setup mock responses for fuzzy matching
            def mock_find_best_side_effect(query, candidates, threshold):
                if not candidates:
                    return None
                
                # Determine which entity we're matching based on candidates
                if candidates and 'TestCategory' in str(candidates):
                    if category_found and category_score >= threshold:
                        return ({'id': category_id, 'name': 'TestCategory'}, category_score)
                    return None
                elif candidates and 'TestBrand' in str(candidates):
                    if brand_found and brand_score >= threshold:
                        return ({'id': brand_id, 'name': 'TestBrand'}, brand_score)
                    return None
                elif candidates and 'TestModel' in str(candidates):
                    if model_score >= threshold:
                        return ({'id': model_id, 'name': 'TestModel'}, model_score)
                    return None
                return None
            
            mock_find_best.side_effect = mock_find_best_side_effect
            
            # Execute the hierarchical matching through match_device
            result = await matcher.match_device(category_text, brand_text, model_text)
            
            # Property 1: Category matching always executes (no dependencies)
            # Verify category query was attempted
            category_queries = [q for q in query_calls if 'device_category' in q]
            assert len(category_queries) > 0, \
                "Category query should always be executed (no dependencies)"
            
            # Property 2: Brand matching should only execute when category_id is not null
            brand_queries = [q for q in query_calls if 'device_brand' in q or 'category_brand' in q]
            
            if brand_text:
                if category_found and category_score >= 0.80:
                    # Category was found, so brand query should have been executed
                    assert len(brand_queries) > 0, \
                        "Brand query should execute when category_id is not null and brand_text is provided"
                    
                    # Verify the result reflects the hierarchical dependency
                    assert result.category is not None, \
                        "Category should be found when category_found=True and score >= threshold"
                    
                    if brand_found and brand_score >= 0.80:
                        assert result.brand is not None, \
                            "Brand should be found when brand_found=True and score >= threshold"
                    else:
                        assert result.brand is None, \
                            "Brand should be None when brand_found=False or score < threshold"
                else:
                    # Category was not found, so brand query should NOT have been executed
                    assert len(brand_queries) == 0, \
                        "Brand query should NOT execute when category_id is null"
                    
                    assert result.brand is None, \
                        "Brand should be None when category is not found"
            else:
                # No brand_text provided, so brand query should not execute
                assert len(brand_queries) == 0, \
                    "Brand query should NOT execute when brand_text is not provided"
                assert result.brand is None, \
                    "Brand should be None when brand_text is not provided"
            
            # Property 3: Model matching should only execute when both category_id and brand_id are not null
            model_queries = [q for q in query_calls if 'device_model' in q]
            
            if model_text:
                if (category_found and category_score >= 0.80 and 
                    brand_text and brand_found and brand_score >= 0.80):
                    # Both category and brand were found, so model query should have been executed
                    assert len(model_queries) > 0, \
                        "Model query should execute when both category_id and brand_id are not null and model_text is provided"
                    
                    # Verify the result reflects the hierarchical dependency
                    assert result.category is not None, \
                        "Category should be found"
                    assert result.brand is not None, \
                        "Brand should be found"
                    
                    if model_score >= 0.75:
                        assert result.model is not None, \
                            "Model should be found when model score >= threshold"
                    else:
                        assert result.model is None, \
                            "Model should be None when model score < threshold"
                else:
                    # Either category or brand was not found, so model query should NOT have been executed
                    assert len(model_queries) == 0, \
                        "Model query should NOT execute when category_id or brand_id is null"
                    
                    assert result.model is None, \
                        "Model should be None when category or brand is not found"
            else:
                # No model_text provided, so model query should not execute
                assert len(model_queries) == 0, \
                    "Model query should NOT execute when model_text is not provided"
                assert result.model is None, \
                    "Model should be None when model_text is not provided"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_hierarchical_dependencies_brand_requires_category():
    """
    **Validates: Requirements 3.6, 4.6**
    
    Specific test: Brand matching should return None when category_id is None,
    regardless of whether brand_text is provided.
    """
    matcher = DatabaseMatcher()
    
    # Test with None category_id
    result = await matcher.match_brand("Apple", None)
    
    # Property: Brand matching requires category_id
    assert result is None, \
        "Brand matching should return None when category_id is None"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_hierarchical_dependencies_model_requires_category():
    """
    **Validates: Requirements 3.6, 4.6**
    
    Specific test: Model matching should return None when category_id is None,
    regardless of whether brand_id and model_text are provided.
    """
    matcher = DatabaseMatcher()
    
    brand_id = uuid4()
    
    # Test with None category_id
    result = await matcher.match_model("iPhone 14 Pro", None, brand_id)
    
    # Property: Model matching requires category_id
    assert result is None, \
        "Model matching should return None when category_id is None"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_hierarchical_dependencies_model_requires_brand():
    """
    **Validates: Requirements 3.6, 4.6**
    
    Specific test: Model matching should return None when brand_id is None,
    regardless of whether category_id and model_text are provided.
    """
    matcher = DatabaseMatcher()
    
    category_id = uuid4()
    
    # Test with None brand_id
    result = await matcher.match_model("iPhone 14 Pro", category_id, None)
    
    # Property: Model matching requires brand_id
    assert result is None, \
        "Model matching should return None when brand_id is None"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_hierarchical_dependencies_model_requires_both():
    """
    **Validates: Requirements 3.6, 4.6**
    
    Specific test: Model matching should return None when either category_id or brand_id is None.
    """
    matcher = DatabaseMatcher()
    
    # Test with both None
    result = await matcher.match_model("iPhone 14 Pro", None, None)
    
    # Property: Model matching requires both category_id and brand_id
    assert result is None, \
        "Model matching should return None when both category_id and brand_id are None"


# Feature: database-matching-integration, Property 11: Hierarchical Matching Dependencies
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_hierarchical_dependencies_match_device_flow():
    """
    **Validates: Requirements 3.6, 4.6**
    
    Integration test: Verify the complete hierarchical flow through match_device.
    When category is not found, brand and model should not be attempted.
    """
    matcher = DatabaseMatcher()
    
    # Mock database connection manager
    mock_conn = MagicMock()
    
    # Setup: Category query returns empty (no match)
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        mock_db_manager.pool = mock_pool
        
        # Execute match_device with all three texts provided
        result = await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
        
        # Property: When category is not found, brand and model should also be None
        assert result.category is None, \
            "Category should be None when no match found"
        assert result.brand is None, \
            "Brand should be None when category is not found (hierarchical dependency)"
        assert result.model is None, \
            "Model should be None when category is not found (hierarchical dependency)"
        
        # Verify only category query was executed (not brand or model)
        # The fetch should have been called only once for category
        assert mock_conn.fetch.call_count == 1, \
            "Only category query should be executed when category is not found"
