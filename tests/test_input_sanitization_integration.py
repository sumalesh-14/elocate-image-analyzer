"""
Integration tests for input sanitization in database matcher.

Tests that SQL injection attempts and malicious inputs are properly blocked
when used with the database matcher service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.database_matcher import DatabaseMatcher


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    with patch('app.services.database_matcher.db_manager') as mock:
        mock.is_available.return_value = True
        
        # Mock connection pool
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock.pool = mock_pool
        
        yield mock, mock_conn


@pytest.mark.asyncio
class TestInputSanitizationIntegration:
    """Test suite for input sanitization integration with database matcher."""
    
    async def test_category_rejects_sql_injection_select(self, mock_db_manager):
        """Test that SQL SELECT injection is rejected in category matching."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt SQL injection
        result = await matcher.match_category("'; SELECT * FROM device_category; --")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_rejects_sql_injection_drop(self, mock_db_manager):
        """Test that SQL DROP injection is rejected in category matching."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt SQL injection
        result = await matcher.match_category("'; DROP TABLE device_category; --")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_rejects_sql_injection_union(self, mock_db_manager):
        """Test that SQL UNION injection is rejected in category matching."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt SQL injection
        result = await matcher.match_category("' UNION SELECT password FROM users --")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_rejects_sql_injection_or_equals(self, mock_db_manager):
        """Test that SQL OR equals injection is rejected in category matching."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt SQL injection
        result = await matcher.match_category("1' OR '1'='1")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_brand_rejects_sql_injection(self, mock_db_manager):
        """Test that SQL injection is rejected in brand matching."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        category_id = uuid4()
        
        # Attempt SQL injection
        result = await matcher.match_brand("'; DROP TABLE device_brand; --", category_id)
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_model_rejects_sql_injection(self, mock_db_manager):
        """Test that SQL injection is rejected in model matching."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        category_id = uuid4()
        brand_id = uuid4()
        
        # Attempt SQL injection
        result = await matcher.match_model("'; DROP TABLE device_model; --", category_id, brand_id)
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_accepts_valid_input(self, mock_db_manager):
        """Test that valid input is accepted and processed."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Mock database response
        mock_conn.fetch.return_value = [
            {'id': uuid4(), 'name': 'Mobile Phone'}
        ]
        
        # Valid input should be processed
        result = await matcher.match_category("Mobile Phone")
        
        # Should query database
        mock_conn.fetch.assert_called_once()
    
    async def test_category_rejects_special_characters(self, mock_db_manager):
        """Test that special characters like quotes are rejected."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt with special characters
        result = await matcher.match_category("test'value")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_rejects_backticks(self, mock_db_manager):
        """Test that backticks are rejected."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt with backticks
        result = await matcher.match_category("test`value")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_rejects_angle_brackets(self, mock_db_manager):
        """Test that angle brackets are rejected."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt with angle brackets
        result = await matcher.match_category("test<script>")
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_category_rejects_too_long_input(self, mock_db_manager):
        """Test that excessively long input is rejected."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Create input exceeding max length
        long_input = "A" * 201
        result = await matcher.match_category(long_input)
        
        # Should return None without querying database
        assert result is None
        mock_conn.fetch.assert_not_called()
    
    async def test_brand_accepts_valid_input(self, mock_db_manager):
        """Test that valid brand input is accepted and processed."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        category_id = uuid4()
        
        # Mock database response
        mock_conn.fetch.return_value = [
            {'id': uuid4(), 'name': 'Apple'}
        ]
        
        # Valid input should be processed
        result = await matcher.match_brand("Apple", category_id)
        
        # Should query database
        mock_conn.fetch.assert_called_once()
    
    async def test_model_accepts_valid_input(self, mock_db_manager):
        """Test that valid model input is accepted and processed."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        category_id = uuid4()
        brand_id = uuid4()
        
        # Mock database response
        mock_conn.fetch.return_value = [
            {'id': uuid4(), 'name': 'iPhone 14 Pro'}
        ]
        
        # Valid input should be processed
        result = await matcher.match_model("iPhone 14 Pro", category_id, brand_id)
        
        # Should query database
        mock_conn.fetch.assert_called_once()
    
    async def test_device_match_with_sql_injection_attempts(self, mock_db_manager):
        """Test that device matching rejects SQL injection in all fields."""
        mock_manager, mock_conn = mock_db_manager
        matcher = DatabaseMatcher()
        
        # Attempt SQL injection in all fields
        result = await matcher.match_device(
            category_text="'; DROP TABLE device_category; --",
            brand_text="'; DROP TABLE device_brand; --",
            model_text="'; DROP TABLE device_model; --"
        )
        
        # Should return failure status without querying database
        assert result.category is None
        assert result.brand is None
        assert result.model is None
        mock_conn.fetch.assert_not_called()


