"""
Property-based test for hierarchical matching dependencies.

Tests Property 11: Hierarchical Matching Dependencies from the database-matching-integration spec.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings
from uuid import uuid4
from typing import Optional

from app.services.database_matcher import DatabaseMatcher


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
@settings(max_examples=20)
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

