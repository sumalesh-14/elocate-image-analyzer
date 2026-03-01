"""
Integration tests for analyzer service with database matcher.

Tests that the analyzer service correctly integrates with the database matcher
to populate UUID and score fields in the response.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from io import BytesIO
from PIL import Image
from fastapi import UploadFile

from app.services.analyzer import analyzer_service
from app.services.database_matcher import DeviceMatch, CategoryMatch, BrandMatch, ModelMatch


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
async def test_analyzer_populates_database_fields_on_successful_match(mock_upload_file):
    """
    Test that analyzer populates UUID and score fields when database matching succeeds.
    
    Validates Requirements: 6.1, 6.2, 6.4, 6.6
    """
    # Create mock UUIDs
    category_id = uuid4()
    brand_id = uuid4()
    model_id = uuid4()
    
    # Mock Gemini response
    mock_gemini_result = {
        "category": "mobile",
        "brand": "Apple",
        "model": "iPhone 14",
        "deviceType": "smartphone",
        "confidenceScore": 0.9,
        "attributes": {"color": "black"},
        "severity": "high",
        "contains_precious_metals": True,
        "precious_metals_info": "Contains gold and silver",
        "contains_hazardous_materials": True,
        "hazardous_materials_info": "Contains lithium battery"
    }
    
    # Mock database match result
    mock_device_match = DeviceMatch(
        category=CategoryMatch(id=category_id, name="Mobile Phone", similarity_score=0.95),
        brand=BrandMatch(id=brand_id, name="Apple", similarity_score=0.98),
        model=ModelMatch(id=model_id, name="iPhone 14", similarity_score=0.92),
        database_status="success"
    )
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher.match_device', new_callable=AsyncMock) as mock_db_match:
        
        # Setup mocks
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        mock_db_match.return_value = mock_device_match
        
        # Execute analysis
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify database matcher was called with correct parameters
        mock_db_match.assert_called_once()
        call_args = mock_db_match.call_args
        assert call_args.kwargs['category_text'] == "Mobile Phone"  # Normalized
        assert call_args.kwargs['brand_text'] == "Apple"
        assert call_args.kwargs['model_text'] == "iPhone 14"
        
        # Verify UUID fields are populated
        assert result.category_id == category_id
        assert result.brand_id == brand_id
        assert result.model_id == model_id
        
        # Verify score fields are populated
        assert result.category_match_score == 0.95
        assert result.brand_match_score == 0.98
        assert result.model_match_score == 0.92
        
        # Verify database status
        assert result.database_status == "success"
        
        # Verify text fields are preserved from Gemini
        assert result.category == "Mobile Phone"
        assert result.brand == "Apple"
        assert result.model == "iPhone 14"


@pytest.mark.asyncio
async def test_analyzer_handles_partial_database_match(mock_upload_file):
    """
    Test that analyzer handles partial matches (category found, brand not found).
    
    Validates Requirements: 6.3, 8.5
    """
    category_id = uuid4()
    
    mock_gemini_result = {
        "category": "mobile",
        "brand": "RareBrand",  # Changed from "UnknownBrand" to avoid uncertainty logic
        "model": "RareModel",  # Changed from "UnknownModel" to avoid uncertainty logic
        "deviceType": "smartphone",
        "confidenceScore": 0.8,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    # Mock partial match: only category found
    mock_device_match = DeviceMatch(
        category=CategoryMatch(id=category_id, name="Mobile Phone", similarity_score=0.90),
        brand=None,
        model=None,
        database_status="partial_success"
    )
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher.match_device', new_callable=AsyncMock) as mock_db_match:
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        mock_db_match.return_value = mock_device_match
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify category match
        assert result.category_id == category_id
        assert result.category_match_score == 0.90
        
        # Verify brand and model are null
        assert result.brand_id is None
        assert result.model_id is None
        assert result.brand_match_score is None
        assert result.model_match_score is None
        
        # Verify partial success status
        assert result.database_status == "partial_success"
        
        # Verify text fields are still preserved
        assert result.category == "Mobile Phone"
        assert result.brand == "RareBrand"
        assert result.model == "RareModel"


@pytest.mark.asyncio
async def test_analyzer_handles_database_unavailable(mock_upload_file):
    """
    Test that analyzer gracefully handles database unavailability.
    
    Validates Requirements: 1.4, 8.2, 8.6
    """
    mock_gemini_result = {
        "category": "laptop",
        "brand": "Dell",
        "model": "XPS 15",
        "deviceType": "laptop",
        "confidenceScore": 0.85,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    # Mock database unavailable
    mock_device_match = DeviceMatch(
        category=None,
        brand=None,
        model=None,
        database_status="unavailable"
    )
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher.match_device', new_callable=AsyncMock) as mock_db_match:
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        mock_db_match.return_value = mock_device_match
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify all UUID fields are null
        assert result.category_id is None
        assert result.brand_id is None
        assert result.model_id is None
        
        # Verify all score fields are null
        assert result.category_match_score is None
        assert result.brand_match_score is None
        assert result.model_match_score is None
        
        # Verify database status is unavailable
        assert result.database_status == "unavailable"
        
        # Verify text fields are still populated from Gemini
        assert result.category == "Laptop"
        assert result.brand == "Dell"
        assert result.model == "XPS 15"


@pytest.mark.asyncio
async def test_analyzer_handles_database_matcher_exception(mock_upload_file):
    """
    Test that analyzer handles exceptions from database matcher gracefully.
    
    Validates Requirements: 8.1, 8.2
    """
    mock_gemini_result = {
        "category": "tablet",
        "brand": "Samsung",
        "model": "Galaxy Tab",
        "deviceType": "tablet",
        "confidenceScore": 0.75,
        "attributes": {},
        "severity": "high",
        "contains_precious_metals": True,
        "contains_hazardous_materials": True
    }
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher.match_device', new_callable=AsyncMock) as mock_db_match:
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        # Simulate database matcher raising an exception
        mock_db_match.side_effect = Exception("Database connection failed")
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify all UUID fields are null
        assert result.category_id is None
        assert result.brand_id is None
        assert result.model_id is None
        
        # Verify database status is failure
        assert result.database_status == "failure"
        
        # Verify text fields are still populated from Gemini
        assert result.category == "Tablet"
        assert result.brand == "Samsung"
        assert result.model == "Galaxy Tab"


@pytest.mark.asyncio
async def test_analyzer_preserves_text_fields_regardless_of_database_status(mock_upload_file):
    """
    Test that text fields from Gemini are always preserved regardless of database status.
    
    Validates Requirement: 6.4 (Property 19: Text Field Preservation)
    """
    mock_gemini_result = {
        "category": "charger",
        "brand": "Anker",
        "model": "PowerPort",
        "deviceType": "USB charger",
        "confidenceScore": 0.7,
        "attributes": {},
        "severity": "medium",
        "contains_precious_metals": False,
        "contains_hazardous_materials": False
    }
    
    # Test with failure status
    mock_device_match = DeviceMatch(
        category=None,
        brand=None,
        model=None,
        database_status="failure"
    )
    
    with patch('app.services.analyzer.validate_image') as mock_validate, \
         patch('app.services.analyzer.gemini_service.analyze_device_image', new_callable=AsyncMock) as mock_gemini, \
         patch('app.services.analyzer.database_matcher.match_device', new_callable=AsyncMock) as mock_db_match:
        
        mock_validate.return_value = MagicMock(is_valid=True)
        mock_gemini.return_value = mock_gemini_result
        mock_db_match.return_value = mock_device_match
        
        result = await analyzer_service.analyze_device(mock_upload_file)
        
        # Verify text fields exactly match Gemini output (after normalization)
        assert result.category == "Charger"  # Normalized
        assert result.brand == "Anker"
        assert result.model == "PowerPort"
        assert result.deviceType == "USB charger"

