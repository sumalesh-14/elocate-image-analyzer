"""
Integration tests for complete database matching flow.

Tests end-to-end scenarios: image upload → Gemini → database matching → response.
Validates complete match, partial match, fuzzy matching, threshold rejection,
database unavailable, and cache effectiveness scenarios.

Validates Requirements: 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 7.5, 8.2
"""

import pytest
import asyncpg
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from io import BytesIO
from PIL import Image
from fastapi import UploadFile

from app.services.analyzer import analyzer_service
from app.services.database_matcher import database_matcher, DatabaseMatcher
from tests.test_db_setup import (
    TEST_CATEGORY_MOBILE_ID,
    TEST_CATEGORY_LAPTOP_ID,
    TEST_CATEGORY_TABLET_ID,
    TEST_BRAND_APPLE_ID,
    TEST_BRAND_SAMSUNG_ID,
    TEST_BRAND_DELL_ID,
    TEST_MODEL_IPHONE_14_ID,
    TEST_MODEL_GALAXY_S23_ID,
    TEST_MODEL_XPS_15_ID,
    TEST_MODEL_IPAD_PRO_ID,
)


@pytest.fixture
def mock_image_bytes():
    """Create a valid test image."""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


@pytest.fixture
def mock_upload_file(mock_image_bytes):
    """Create a mock UploadFile."""
    file = MagicMock(spec=UploadFile)
    file.filename = "test_device.jpg"
    file.content_type = "image/jpeg"
    file.read = AsyncMock(return_value=mock_image_bytes)
    return file


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_match_scenario_category_brand_model(test_db_connection, mock_upload_file):
    """
    Test complete match scenario where category, brand, and model are all found.
    
    End-to-end flow: image upload → Gemini → database matching → response
    
    Validates Requirements: 2.1, 3.1, 4.1
    """
    # Setup database matcher with test connection
    test_matcher = DatabaseMatcher(test_db_connection)
    
    # Mock Gemini response with iPhone data
    mock_gemini_result = {
        "category": "mobile phone",
        "brand": "Apple",
        "model": "iPhone 14 Pro",
        "deviceType": "smartphone",
        "confidenceScore": 0.95,
        "attributes": {"color": "black"},
        "severity": "high",
        "contains_precious_metals": True,
        "precious_metals_info": "Contains gold and silver",
        "contains_hazardous_materials": True,
        "hazardous_materials_info": "Contains lithium battery"
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        # Execute analysis
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify complete match
        assert result.category_id == TEST_CATEGORY_MOBILE_ID
        assert result.brand_id == TEST_BRAND_APPLE_ID
        assert result.model_id == TEST_MODEL_IPHONE_14_ID
        
        # Verify match scores are present and reasonable
        assert result.category_match_score is not None
        assert result.category_match_score >= 0.80
        assert result.brand_match_score is not None
        assert result.brand_match_score >= 0.80
        assert result.model_match_score is not None
        assert result.model_match_score >= 0.75
        
        # Verify database status
        assert result.database_status == "success"
        
        # Verify text fields preserved
        assert result.category == "Mobile Phone"
        assert result.brand == "Apple"
        assert result.model == "iPhone 14 Pro"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_partial_match_category_found_brand_not_found(test_db_connection, mock_upload_file):
    """
    Test partial match scenario where category is found but brand is not.
    
    Validates Requirements: 2.1, 3.1, 8.2
    """
    test_matcher = DatabaseMatcher(test_db_connection)
    
    # Mock Gemini response with unknown brand
    mock_gemini_result = {
        "category": "mobile phone",
        "brand": "UnknownBrandXYZ",  # Brand not in database
        "model": "Model 123",
        "deviceType": "smartphone",
        "confidenceScore": 0.85,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify partial match
        assert result.category_id == TEST_CATEGORY_MOBILE_ID
        assert result.category_match_score is not None
        assert result.category_match_score >= 0.80
        
        # Verify brand and model not matched
        assert result.brand_id is None
        assert result.model_id is None
        assert result.brand_match_score is None
        assert result.model_match_score is None
        
        # Verify partial success status
        assert result.database_status == "partial_success"
        
        # Verify text fields preserved
        assert result.category == "Mobile Phone"
        assert result.brand == "UnknownBrandXYZ"
        assert result.model == "Model 123"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fuzzy_matching_with_variations(test_db_connection, mock_upload_file):
    """
    Test fuzzy matching handles variations like "iphone" → "iPhone".
    
    Validates Requirements: 2.2, 3.3, 4.3
    """
    test_matcher = DatabaseMatcher(test_db_connection)
    
    # Mock Gemini response with lowercase and variations
    mock_gemini_result = {
        "category": "mobile",  # Variation of "Mobile Phone"
        "brand": "apple",  # Lowercase variation
        "model": "iphone 14 pro",  # Lowercase variation
        "deviceType": "smartphone",
        "confidenceScore": 0.90,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify fuzzy matching worked despite variations
        assert result.category_id == TEST_CATEGORY_MOBILE_ID
        assert result.brand_id == TEST_BRAND_APPLE_ID
        assert result.model_id == TEST_MODEL_IPHONE_14_ID
        
        # Verify match scores reflect fuzzy matching
        assert result.category_match_score is not None
        assert result.brand_match_score is not None
        assert result.model_match_score is not None
        
        assert result.database_status == "success"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_threshold_rejection_scenario(test_db_connection, mock_upload_file):
    """
    Test that very different strings are rejected based on threshold.
    
    Validates Requirements: 2.2, 2.5, 3.3, 3.7, 4.3, 4.7
    """
    test_matcher = DatabaseMatcher(test_db_connection)
    
    # Mock Gemini response with completely different strings
    mock_gemini_result = {
        "category": "xyz123abc",  # Completely different from any category
        "brand": "qwerty",
        "model": "asdfgh",
        "deviceType": "unknown",
        "confidenceScore": 0.50,
        "attributes": {},
        "severity": "low",
        "contains_precious_metals": False,
        "contains_hazardous_materials": False
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify all matches rejected due to low similarity
        assert result.category_id is None
        assert result.brand_id is None
        assert result.model_id is None
        
        # Verify no match scores
        assert result.category_match_score is None
        assert result.brand_match_score is None
        assert result.model_match_score is None
        
        # Verify partial success or failure status
        assert result.database_status in ["partial_success", "failure"]
        
        # Verify text fields still preserved
        assert result.category == "Xyz123abc"
        assert result.brand == "Qwerty"
        assert result.model == "Asdfgh"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_unavailable_scenario(mock_upload_file):
    """
    Test graceful degradation when database is unavailable.
    
    Validates Requirements: 1.4, 8.2, 8.6
    """
    # Mock Gemini response
    mock_gemini_result = {
        "category": "laptop",
        "brand": "Dell",
        "model": "XPS 15",
        "deviceType": "laptop",
        "confidenceScore": 0.88,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    # Create a matcher with invalid connection (simulating unavailable database)
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher.match_device', new_callable=AsyncMock) as mock_match:
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        # Simulate database unavailable by raising exception
        mock_match.side_effect = Exception("Database connection failed")
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify graceful degradation
        assert result.category_id is None
        assert result.brand_id is None
        assert result.model_id is None
        
        # Verify database status
        assert result.database_status == "failure"
        
        # Verify text fields still populated from Gemini
        assert result.category == "Laptop"
        assert result.brand == "Dell"
        assert result.model == "XPS 15"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_effectiveness(test_db_connection, mock_upload_file):
    """
    Test that cache is used for identical queries within TTL.
    
    Validates Requirements: 7.5
    """
    test_matcher = DatabaseMatcher(test_db_connection)
    
    # Clear cache before test
    test_matcher.cache.clear()
    
    # Mock Gemini response
    mock_gemini_result = {
        "category": "tablet",
        "brand": "Apple",
        "model": "iPad Pro",
        "deviceType": "tablet",
        "confidenceScore": 0.92,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        # First request - should query database
        result1 = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify cache has entries after first request
        cache_size_after_first = test_matcher.cache.size()
        assert cache_size_after_first > 0
        
        # Second request with same data - should use cache
        result2 = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify results are identical
        assert result1.category_id == result2.category_id
        assert result1.brand_id == result2.brand_id
        assert result1.model_id == result2.model_id
        assert result1.category_match_score == result2.category_match_score
        assert result1.brand_match_score == result2.brand_match_score
        assert result1.model_match_score == result2.model_match_score
        
        # Verify cache size didn't grow (reused existing entries)
        cache_size_after_second = test_matcher.cache.size()
        assert cache_size_after_second == cache_size_after_first


@pytest.mark.asyncio
@pytest.mark.integration
async def test_laptop_complete_match(test_db_connection, mock_upload_file):
    """
    Test complete match for laptop category with Dell brand.
    
    Validates Requirements: 2.1, 3.1, 4.1
    """
    test_matcher = DatabaseMatcher(test_db_connection)
    
    mock_gemini_result = {
        "category": "laptop",
        "brand": "Dell",
        "model": "XPS 15",
        "deviceType": "laptop",
        "confidenceScore": 0.93,
        "attributes": {"screen_size": "15 inch"},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify complete match for laptop
        assert result.category_id == TEST_CATEGORY_LAPTOP_ID
        assert result.brand_id == TEST_BRAND_DELL_ID
        assert result.model_id == TEST_MODEL_XPS_15_ID
        
        assert result.database_status == "success"
        
        # Verify text fields
        assert result.category == "Laptop"
        assert result.brand == "Dell"
        assert result.model == "XPS 15"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_samsung_galaxy_complete_match(test_db_connection, mock_upload_file):
    """
    Test complete match for Samsung Galaxy phone.
    
    Validates Requirements: 2.1, 3.1, 4.1
    """
    test_matcher = DatabaseMatcher(test_db_connection)
    
    mock_gemini_result = {
        "category": "mobile phone",
        "brand": "Samsung",
        "model": "Galaxy S23",
        "deviceType": "smartphone",
        "confidenceScore": 0.91,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher', test_matcher):
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify complete match for Samsung
        assert result.category_id == TEST_CATEGORY_MOBILE_ID
        assert result.brand_id == TEST_BRAND_SAMSUNG_ID
        assert result.model_id == TEST_MODEL_GALAXY_S23_ID
        
        assert result.database_status == "success"
