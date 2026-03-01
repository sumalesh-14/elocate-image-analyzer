"""
Unit tests for database matcher service.

Tests specific examples, edge cases, and known scenarios for the database matching
functionality used in device identification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from app.services.database_matcher import (
    DatabaseMatcher,
    CategoryMatch,
    BrandMatch,
    ModelMatch,
    DeviceMatch
)


class TestCategoryMatching:
    """Test cases for category matching with known examples."""

    @pytest.mark.asyncio
    async def test_match_category_exact_match(self):
        """Should match exact category name with score 1.0."""
        matcher = DatabaseMatcher()
        
        # Mock database connection
        mock_conn = MagicMock()
        category_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': category_id, 'name': 'Mobile Phone'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_category("Mobile Phone")
            
            assert result is not None
            assert isinstance(result, CategoryMatch)
            assert result.id == category_id
            assert result.name == 'Mobile Phone'
            assert result.similarity_score == 1.0

    @pytest.mark.asyncio
    async def test_match_category_fuzzy_match(self):
        """Should match similar category name with high score."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': category_id, 'name': 'Mobile Phone'},
            {'id': uuid4(), 'name': 'Laptop'},
            {'id': uuid4(), 'name': 'Tablet'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            # Test with slight variation
            result = await matcher.match_category("mobile phone")
            
            assert result is not None
            assert result.id == category_id
            assert result.name == 'Mobile Phone'
            assert result.similarity_score >= 0.8

    @pytest.mark.asyncio
    async def test_match_category_below_threshold(self):
        """Should return None when similarity is below threshold."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'Mobile Phone'},
            {'id': uuid4(), 'name': 'Laptop'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            # Test with completely different text
            result = await matcher.match_category("xyz123")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_match_category_empty_text(self):
        """Should return None for empty category text."""
        matcher = DatabaseMatcher()
        
        result = await matcher.match_category("")
        assert result is None

    @pytest.mark.asyncio
    async def test_match_category_database_unavailable(self):
        """Should return None when database is unavailable."""
        matcher = DatabaseMatcher()
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = False
            
            result = await matcher.match_category("Mobile Phone")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_match_category_no_candidates(self):
        """Should return None when no categories exist in database."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_category("Mobile Phone")
            
            assert result is None


class TestBrandMatching:
    """Test cases for brand matching with category validation."""

    @pytest.mark.asyncio
    async def test_match_brand_exact_match(self):
        """Should match exact brand name with category validation."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        brand_id = uuid4()
        category_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': brand_id, 'name': 'Apple'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_brand("Apple", category_id)
            
            assert result is not None
            assert isinstance(result, BrandMatch)
            assert result.id == brand_id
            assert result.name == 'Apple'
            assert result.similarity_score == 1.0

    @pytest.mark.asyncio
    async def test_match_brand_fuzzy_match(self):
        """Should match similar brand name with high score."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        brand_id = uuid4()
        category_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': brand_id, 'name': 'Samsung'},
            {'id': uuid4(), 'name': 'Apple'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_brand("samsung", category_id)
            
            assert result is not None
            assert result.id == brand_id
            assert result.name == 'Samsung'
            assert result.similarity_score >= 0.8

    @pytest.mark.asyncio
    async def test_match_brand_no_category_id(self):
        """Should return None when category_id is None (hierarchical dependency)."""
        matcher = DatabaseMatcher()
        
        result = await matcher.match_brand("Apple", None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_match_brand_empty_text(self):
        """Should return None for empty brand text."""
        matcher = DatabaseMatcher()
        category_id = uuid4()
        
        result = await matcher.match_brand("", category_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_match_brand_below_threshold(self):
        """Should return None when similarity is below threshold."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'Apple'},
            {'id': uuid4(), 'name': 'Samsung'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_brand("xyz123", category_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_match_brand_validates_category(self):
        """Should query with category_id to validate brand-category relationship."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        brand_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': brand_id, 'name': 'Apple'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_brand("Apple", category_id)
            
            # Verify the query was called with category_id parameter
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args
            assert category_id in call_args[0], "Query should include category_id parameter"


class TestModelMatching:
    """Test cases for model matching with category and brand validation."""

    @pytest.mark.asyncio
    async def test_match_model_exact_match(self):
        """Should match exact model name with category and brand validation."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        model_id = uuid4()
        category_id = uuid4()
        brand_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': model_id, 'name': 'iPhone 14 Pro'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_model("iPhone 14 Pro", category_id, brand_id)
            
            assert result is not None
            assert isinstance(result, ModelMatch)
            assert result.id == model_id
            assert result.name == 'iPhone 14 Pro'
            assert result.similarity_score == 1.0

    @pytest.mark.asyncio
    async def test_match_model_fuzzy_match(self):
        """Should match similar model name with high score."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        model_id = uuid4()
        category_id = uuid4()
        brand_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': model_id, 'name': 'Galaxy S23'},
            {'id': uuid4(), 'name': 'Galaxy S23 Plus'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_model("galaxy s23", category_id, brand_id)
            
            assert result is not None
            assert result.id == model_id
            assert result.name == 'Galaxy S23'
            assert result.similarity_score >= 0.75

    @pytest.mark.asyncio
    async def test_match_model_no_category_id(self):
        """Should return None when category_id is None (hierarchical dependency)."""
        matcher = DatabaseMatcher()
        brand_id = uuid4()
        
        result = await matcher.match_model("iPhone 14 Pro", None, brand_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_match_model_no_brand_id(self):
        """Should return None when brand_id is None (hierarchical dependency)."""
        matcher = DatabaseMatcher()
        category_id = uuid4()
        
        result = await matcher.match_model("iPhone 14 Pro", category_id, None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_match_model_empty_text(self):
        """Should return None for empty model text."""
        matcher = DatabaseMatcher()
        category_id = uuid4()
        brand_id = uuid4()
        
        result = await matcher.match_model("", category_id, brand_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_match_model_below_threshold(self):
        """Should return None when similarity is below threshold (75%)."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        brand_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'iPhone 14 Pro'},
            {'id': uuid4(), 'name': 'Galaxy S23'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_model("xyz123", category_id, brand_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_match_model_validates_category_and_brand(self):
        """Should query with both category_id and brand_id for validation."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        brand_id = uuid4()
        model_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': model_id, 'name': 'iPhone 14 Pro'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_model("iPhone 14 Pro", category_id, brand_id)
            
            # Verify the query was called with both category_id and brand_id parameters
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args
            assert category_id in call_args[0], "Query should include category_id parameter"
            assert brand_id in call_args[0], "Query should include brand_id parameter"


class TestPartialMatchScenarios:
    """Test cases for partial match scenarios."""

    @pytest.mark.asyncio
    async def test_category_found_brand_not_found(self):
        """Should return category match but None for brand when brand doesn't match."""
        matcher = DatabaseMatcher()
        
        category_id = uuid4()
        
        # Mock the individual match methods instead of the connection pool
        with patch.object(matcher, 'match_category') as mock_match_category:
            with patch.object(matcher, 'match_brand') as mock_match_brand:
                # Category found
                mock_match_category.return_value = CategoryMatch(
                    id=category_id,
                    name='Mobile Phone',
                    similarity_score=0.95
                )
                
                # Brand not found
                mock_match_brand.return_value = None
                
                with patch('app.services.database_matcher.db_manager') as mock_db_manager:
                    mock_db_manager.is_available.return_value = True
                    
                    result = await matcher.match_device("Mobile Phone", "UnknownBrand", None)
                    
                    assert result.category is not None
                    assert result.category.id == category_id
                    assert result.brand is None
                    assert result.model is None
                    assert result.database_status == "partial_success"

    @pytest.mark.asyncio
    async def test_category_and_brand_found_model_not_found(self):
        """Should return category and brand matches but None for model."""
        matcher = DatabaseMatcher()
        
        category_id = uuid4()
        brand_id = uuid4()
        
        # Mock the individual match methods
        with patch.object(matcher, 'match_category') as mock_match_category:
            with patch.object(matcher, 'match_brand') as mock_match_brand:
                with patch.object(matcher, 'match_model') as mock_match_model:
                    # Category found
                    mock_match_category.return_value = CategoryMatch(
                        id=category_id,
                        name='Mobile Phone',
                        similarity_score=0.95
                    )
                    
                    # Brand found
                    mock_match_brand.return_value = BrandMatch(
                        id=brand_id,
                        name='Apple',
                        similarity_score=0.90
                    )
                    
                    # Model not found
                    mock_match_model.return_value = None
                    
                    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
                        mock_db_manager.is_available.return_value = True
                        
                        result = await matcher.match_device("Mobile Phone", "Apple", "UnknownModel")
                        
                        assert result.category is not None
                        assert result.brand is not None
                        assert result.model is None
                        assert result.database_status == "partial_success"


class TestThresholdRejectionScenarios:
    """Test cases for threshold rejection scenarios."""

    @pytest.mark.asyncio
    async def test_category_threshold_rejection(self):
        """Should reject category match when below 80% threshold."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'Mobile Phone'},
            {'id': uuid4(), 'name': 'Laptop'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            # Use text that won't match well
            result = await matcher.match_category("completely different text xyz")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_brand_threshold_rejection(self):
        """Should reject brand match when below 80% threshold."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'Apple'},
            {'id': uuid4(), 'name': 'Samsung'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_brand("completely different text xyz", category_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_model_threshold_rejection(self):
        """Should reject model match when below 75% threshold."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        category_id = uuid4()
        brand_id = uuid4()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'iPhone 14 Pro'},
            {'id': uuid4(), 'name': 'Galaxy S23'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_model("completely different text xyz", category_id, brand_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_all_thresholds_rejected(self):
        """Should return failure status when all matches are rejected."""
        matcher = DatabaseMatcher()
        
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[
            {'id': uuid4(), 'name': 'Mobile Phone'}
        ])
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            mock_db_manager.pool = mock_pool
            
            result = await matcher.match_device("xyz123", "abc456", "def789")
            
            assert result.category is None
            assert result.brand is None
            assert result.model is None
            assert result.database_status == "failure"

