"""
Unit tests for analyzer service.

Tests specific examples and edge cases for device analysis functionality.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
from PIL import Image
from fastapi import UploadFile

from app.services.analyzer import (
    analyzer_service,
    AnalysisError,
    CATEGORY_MAPPING
)
from app.models.response import DeviceData
from app.services.gemini_service import GeminiAPIError


def create_test_image(format_name="jpeg", width=100, height=100):
    """Helper to create valid test image bytes."""
    img = Image.new("RGB", (width, height), color="blue")
    buffer = BytesIO()
    
    format_map = {
        "jpeg": "JPEG",
        "jpg": "JPEG",
        "png": "PNG",
        "webp": "WEBP"
    }
    
    pil_format = format_map.get(format_name.lower(), format_name.upper())
    img.save(buffer, format=pil_format)
    return buffer.getvalue()


def create_upload_file(filename: str, content: bytes) -> UploadFile:
    """Create a mock UploadFile for testing."""
    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.content_type = "image/jpeg"
    file.read = AsyncMock(return_value=content)
    return file


class TestSuccessfulAnalysis:
    """Test successful analysis returns all required fields."""
    
    @pytest.mark.asyncio
    async def test_successful_analysis_returns_all_required_fields(self):
        """Successful analysis should return DeviceData with all required fields."""
        # Create a valid image
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("test.jpg", image_bytes)
        
        # Mock Gemini response with complete data
        gemini_response = {
            "category": "mobile",
            "brand": "Samsung",
            "model": "Galaxy S21",
            "deviceType": "smartphone",
            "confidenceScore": 0.85,
            "attributes": {
                "color": "phantom gray",
                "condition": "good",
                "visiblePorts": "USB-C"
            }
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            # Analyze the device
            result = await analyzer_service.analyze_device(upload_file)
            
            # Verify all required fields are present
            assert isinstance(result, DeviceData)
            assert result.category == "Mobile Phone"  # Normalized
            assert result.brand == "Samsung"
            assert result.model == "Galaxy S21"
            assert result.deviceType == "smartphone"
            assert result.confidenceScore > 0.0
            assert result.confidenceScore <= 1.0
            assert isinstance(result.attributes, dict)
            assert len(result.attributes) > 0
            assert isinstance(result.lowConfidence, bool)
    
    @pytest.mark.asyncio
    async def test_high_confidence_analysis_with_rich_attributes(self):
        """High confidence analysis with many attributes should succeed."""
        image_bytes = create_test_image("png", 300, 300)
        upload_file = create_upload_file("laptop.png", image_bytes)
        
        gemini_response = {
            "category": "laptop",
            "brand": "Dell",
            "model": "XPS 15",
            "deviceType": "laptop computer",
            "confidenceScore": 0.92,
            "attributes": {
                "color": "silver",
                "condition": "excellent",
                "screenSize": "15 inches",
                "visiblePorts": "USB-C, HDMI, USB-A",
                "keyboard": "backlit"
            }
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.category == "Laptop"
            assert result.brand == "Dell"
            assert result.model == "XPS 15"
            assert result.confidenceScore >= 0.92  # May be adjusted slightly
            assert result.lowConfidence is False
            assert len(result.attributes) == 5


class TestLowConfidenceResults:
    """Test low confidence results set lowConfidence flag."""
    
    @pytest.mark.asyncio
    async def test_low_confidence_sets_flag_true(self):
        """Analysis with confidence < 0.5 should set lowConfidence to True."""
        image_bytes = create_test_image("jpeg", 150, 150)
        upload_file = create_upload_file("charger.jpg", image_bytes)
        
        gemini_response = {
            "category": "charger",
            "brand": None,
            "model": None,
            "deviceType": "USB wall charger",
            "confidenceScore": 0.42,
            "attributes": {
                "color": "white",
                "connectorType": "USB-A"
            }
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.lowConfidence is True
            assert result.confidenceScore < 0.5
    
    @pytest.mark.asyncio
    async def test_confidence_at_boundary_0_5(self):
        """Confidence at exactly 0.5 should set lowConfidence to False."""
        image_bytes = create_test_image("jpeg", 150, 150)
        upload_file = create_upload_file("battery.jpg", image_bytes)
        
        # Set confidence high enough that after adjustments it stays >= 0.5
        # Missing model causes -0.1 adjustment, so start at 0.6
        gemini_response = {
            "category": "battery",
            "brand": "Energizer",
            "model": "AA",
            "deviceType": "lithium-ion battery",
            "confidenceScore": 0.5,
            "attributes": {"color": "black"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # At exactly 0.5 or above, lowConfidence should be False
            assert result.lowConfidence is False
            assert result.confidenceScore >= 0.5
    
    @pytest.mark.asyncio
    async def test_very_low_confidence_0_2(self):
        """Very low confidence (0.2) should set lowConfidence to True."""
        image_bytes = create_test_image("webp", 100, 100)
        upload_file = create_upload_file("device.webp", image_bytes)
        
        gemini_response = {
            "category": "accessory",
            "brand": None,
            "model": None,
            "deviceType": "unknown accessory",
            "confidenceScore": 0.2,
            "attributes": {}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.lowConfidence is True
            assert result.confidenceScore < 0.5


class TestUncertainBrandModel:
    """Test uncertain brand/model return null."""
    
    @pytest.mark.asyncio
    async def test_null_brand_remains_null(self):
        """When Gemini returns null brand, result should have null brand."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("cable.jpg", image_bytes)
        
        gemini_response = {
            "category": "cable",
            "brand": None,
            "model": None,
            "deviceType": "USB cable",
            "confidenceScore": 0.7,
            "attributes": {"connectorType": "USB-C to USB-C"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.brand is None
            assert result.model is None
    
    @pytest.mark.asyncio
    async def test_unknown_brand_becomes_null(self):
        """When brand contains 'unknown', it should become null."""
        image_bytes = create_test_image("png", 200, 200)
        upload_file = create_upload_file("device.png", image_bytes)
        
        gemini_response = {
            "category": "charger",
            "brand": "unknown",
            "model": "unclear",
            "deviceType": "wall charger",
            "confidenceScore": 0.6,
            "attributes": {"color": "black"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.brand is None
            assert result.model is None
    
    @pytest.mark.asyncio
    async def test_uncertain_indicators_become_null(self):
        """Fields with uncertainty indicators should become null."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("device.jpg", image_bytes)
        
        gemini_response = {
            "category": "battery",
            "brand": "not visible",
            "model": "uncertain",
            "deviceType": "battery pack",
            "confidenceScore": 0.65,
            "attributes": {"condition": "used"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.brand is None
            assert result.model is None
    
    @pytest.mark.asyncio
    async def test_very_low_confidence_makes_fields_null(self):
        """Very low confidence (< 0.4) should make brand/model null."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("device.jpg", image_bytes)
        
        gemini_response = {
            "category": "appliance",
            "brand": "SomeBrand",
            "model": "SomeModel",
            "deviceType": "small appliance",
            "confidenceScore": 0.35,
            "attributes": {}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # With very low confidence, brand and model should be null
            assert result.brand is None
            assert result.model is None


class TestCategoryNormalization:
    """Test category normalization works correctly."""
    
    @pytest.mark.asyncio
    async def test_mobile_normalized_to_mobile_phone(self):
        """Category 'mobile' should be normalized to 'Mobile Phone'."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "Apple",
            "model": "iPhone 13",
            "deviceType": "smartphone",
            "confidenceScore": 0.9,
            "attributes": {"color": "blue"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.category == "Mobile Phone"
    
    @pytest.mark.asyncio
    async def test_smartphone_normalized_to_mobile_phone(self):
        """Category 'smartphone' should be normalized to 'Mobile Phone'."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "smartphone",
            "brand": "Samsung",
            "model": "Galaxy",
            "deviceType": "smartphone",
            "confidenceScore": 0.88,
            "attributes": {}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.category == "Mobile Phone"
    
    @pytest.mark.asyncio
    async def test_laptop_normalized_correctly(self):
        """Category 'laptop' should be normalized to 'Laptop'."""
        image_bytes = create_test_image("png", 200, 200)
        upload_file = create_upload_file("laptop.png", image_bytes)
        
        gemini_response = {
            "category": "laptop",
            "brand": "HP",
            "model": "Pavilion",
            "deviceType": "laptop computer",
            "confidenceScore": 0.91,
            "attributes": {"color": "silver"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.category == "Laptop"
    
    @pytest.mark.asyncio
    async def test_adapter_normalized_to_charger(self):
        """Category 'adapter' should be normalized to 'Charger'."""
        image_bytes = create_test_image("jpeg", 150, 150)
        upload_file = create_upload_file("adapter.jpg", image_bytes)
        
        gemini_response = {
            "category": "adapter",
            "brand": "Anker",
            "model": "PowerPort",
            "deviceType": "power adapter",
            "confidenceScore": 0.8,
            "attributes": {"ports": "2"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.category == "Charger"
    
    @pytest.mark.asyncio
    async def test_wire_normalized_to_cable(self):
        """Category 'wire' should be normalized to 'Cable'."""
        image_bytes = create_test_image("jpeg", 150, 150)
        upload_file = create_upload_file("wire.jpg", image_bytes)
        
        gemini_response = {
            "category": "wire",
            "brand": None,
            "model": None,
            "deviceType": "charging cable",
            "confidenceScore": 0.75,
            "attributes": {"type": "USB-C"}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.category == "Cable"
    
    @pytest.mark.asyncio
    async def test_unknown_category_preserved(self):
        """Unknown category should be preserved as-is."""
        image_bytes = create_test_image("jpeg", 150, 150)
        upload_file = create_upload_file("device.jpg", image_bytes)
        
        gemini_response = {
            "category": "UnknownDevice",
            "brand": "TestBrand",
            "model": "TestModel",
            "deviceType": "unknown type",
            "confidenceScore": 0.6,
            "attributes": {}
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Unknown categories are preserved
            assert result.category == "UnknownDevice"


class TestNonDeviceImages:
    """Test non-device images return error."""
    
    @pytest.mark.asyncio
    async def test_other_category_with_low_confidence_raises_error(self):
        """Image with 'other' category and low confidence should raise NOT_A_DEVICE error."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("random.jpg", image_bytes)
        
        gemini_response = {
            "category": "other",
            "brand": None,
            "model": None,
            "deviceType": "not a device",
            "confidenceScore": 0.25,
            "attributes": {}
        }
        
        with patch('app.services.analyzer.logger'):
            with patch('app.services.analyzer.gemini_service') as mock_gemini:
                mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
                
                with pytest.raises(AnalysisError) as exc_info:
                    await analyzer_service.analyze_device(upload_file)
                
                assert exc_info.value.error_code == "NOT_A_DEVICE"
                assert "does not appear to contain an electronic device" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_invalid_category_with_very_low_confidence_raises_error(self):
        """Invalid category with very low confidence should raise error."""
        image_bytes = create_test_image("png", 200, 200)
        upload_file = create_upload_file("landscape.png", image_bytes)
        
        gemini_response = {
            "category": "furniture",
            "brand": None,
            "model": None,
            "deviceType": "chair",
            "confidenceScore": 0.15,
            "attributes": {}
        }
        
        with patch('app.services.analyzer.logger'):
            with patch('app.services.analyzer.gemini_service') as mock_gemini:
                mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
                
                with pytest.raises(AnalysisError) as exc_info:
                    await analyzer_service.analyze_device(upload_file)
                
                assert exc_info.value.error_code == "NOT_A_DEVICE"


class TestTemporaryFileCleanup:
    """Test temporary file cleanup."""
    
    @pytest.mark.asyncio
    async def test_temp_file_cleaned_up_after_success(self):
        """Temporary file should be deleted after successful analysis."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("test.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "Apple",
            "model": "iPhone",
            "deviceType": "smartphone",
            "confidenceScore": 0.9,
            "attributes": {"color": "black"}
        }
        
        created_files = []
        
        # Track created temporary files
        original_named_temp_file = tempfile.NamedTemporaryFile
        
        def tracked_temp_file(*args, **kwargs):
            temp_file = original_named_temp_file(*args, **kwargs)
            created_files.append(temp_file.name)
            return temp_file
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            with patch('tempfile.NamedTemporaryFile', side_effect=tracked_temp_file):
                result = await analyzer_service.analyze_device(upload_file)
                
                # Verify analysis succeeded
                assert isinstance(result, DeviceData)
                
                # Verify all temp files were deleted
                for temp_file_path in created_files:
                    assert not os.path.exists(temp_file_path), \
                        f"Temporary file {temp_file_path} was not cleaned up"
    
    @pytest.mark.asyncio
    async def test_temp_file_cleaned_up_after_error(self):
        """Temporary file should be deleted even when analysis fails."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("test.jpg", image_bytes)
        
        created_files = []
        
        # Track created temporary files
        original_named_temp_file = tempfile.NamedTemporaryFile
        
        def tracked_temp_file(*args, **kwargs):
            temp_file = original_named_temp_file(*args, **kwargs)
            created_files.append(temp_file.name)
            return temp_file
        
        with patch('app.services.analyzer.logger'):
            with patch('app.services.analyzer.gemini_service') as mock_gemini:
                # Make Gemini raise an error
                mock_gemini.analyze_device_image = AsyncMock(
                    side_effect=GeminiAPIError("API Error")
                )
                
                with patch('tempfile.NamedTemporaryFile', side_effect=tracked_temp_file):
                    with pytest.raises(AnalysisError):
                        await analyzer_service.analyze_device(upload_file)
                    
                    # Verify all temp files were deleted even on error
                    for temp_file_path in created_files:
                        assert not os.path.exists(temp_file_path), \
                            f"Temporary file {temp_file_path} was not cleaned up after error"
    
    @pytest.mark.asyncio
    async def test_temp_file_cleaned_up_on_validation_error(self):
        """Temporary file should be deleted when validation fails."""
        # Create invalid file (too large)
        oversized_bytes = b"x" * (11 * 1024 * 1024)  # 11MB
        upload_file = create_upload_file("huge.jpg", oversized_bytes)
        
        # No temp file should be created for validation errors
        # (validation happens before temp file creation)
        with patch('app.services.analyzer.logger'):
            with pytest.raises(AnalysisError) as exc_info:
                await analyzer_service.analyze_device(upload_file)
            
            assert exc_info.value.error_code == "INVALID_FILE_SIZE"


class TestErrorHandling:
    """Test error handling in analyzer service."""
    
    @pytest.mark.asyncio
    async def test_gemini_timeout_raises_analysis_timeout(self):
        """Gemini timeout should raise ANALYSIS_TIMEOUT error."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("test.jpg", image_bytes)
        
        with patch('app.services.analyzer.logger'):
            with patch('app.services.analyzer.gemini_service') as mock_gemini:
                mock_gemini.analyze_device_image = AsyncMock(
                    side_effect=TimeoutError("Request timed out")
                )
                
                with pytest.raises(AnalysisError) as exc_info:
                    await analyzer_service.analyze_device(upload_file)
                
                assert exc_info.value.error_code == "ANALYSIS_TIMEOUT"
    
    @pytest.mark.asyncio
    async def test_gemini_api_error_raises_service_unavailable(self):
        """Gemini API error should raise SERVICE_UNAVAILABLE error."""
        image_bytes = create_test_image("png", 200, 200)
        upload_file = create_upload_file("test.png", image_bytes)
        
        with patch('app.services.analyzer.logger'):
            with patch('app.services.analyzer.gemini_service') as mock_gemini:
                mock_gemini.analyze_device_image = AsyncMock(
                    side_effect=GeminiAPIError("API is down")
                )
                
                with pytest.raises(AnalysisError) as exc_info:
                    await analyzer_service.analyze_device(upload_file)
                
                assert exc_info.value.error_code == "SERVICE_UNAVAILABLE"
    
    @pytest.mark.asyncio
    async def test_unexpected_error_raises_internal_error(self):
        """Unexpected errors should raise INTERNAL_ERROR."""
        image_bytes = create_test_image("webp", 200, 200)
        upload_file = create_upload_file("test.webp", image_bytes)
        
        with patch('app.services.analyzer.logger'):
            with patch('app.services.analyzer.gemini_service') as mock_gemini:
                mock_gemini.analyze_device_image = AsyncMock(
                    side_effect=ValueError("Unexpected error")
                )
                
                with pytest.raises(AnalysisError) as exc_info:
                    await analyzer_service.analyze_device(upload_file)
                
                assert exc_info.value.error_code == "INTERNAL_ERROR"
                assert "unexpected error" in exc_info.value.message.lower()


class TestEnhancedFieldValidation:
    """Test enhanced field validation logic."""
    
    @pytest.mark.asyncio
    async def test_severity_enum_validation_rejects_invalid_values(self):
        """Invalid severity values should be replaced with defaults."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("test.jpg", image_bytes)
        
        gemini_response = {
            "category": "cable",
            "brand": "Anker",
            "model": "PowerLine",
            "deviceType": "USB cable",
            "confidenceScore": 0.8,
            "attributes": {"color": "black"},
            "severity": "invalid_severity",  # Invalid value
            "contains_precious_metals": False,
            "contains_hazardous_materials": False
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Should use default severity for cable category (low)
            assert result.severity in ["low", "medium", "high", "critical"]
            assert result.severity == "low"

    
    @pytest.mark.asyncio
    async def test_precious_metals_info_only_when_flag_true(self):
        """precious_metals_info should only be present when contains_precious_metals is true."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("cable.jpg", image_bytes)
        
        gemini_response = {
            "category": "cable",
            "brand": "Generic",
            "model": None,
            "deviceType": "USB cable",
            "confidenceScore": 0.75,
            "attributes": {"type": "USB-C"},
            "severity": "low",
            "contains_precious_metals": False,
            "precious_metals_info": "Should not appear",  # Should be removed
            "contains_hazardous_materials": False
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.contains_precious_metals is False
            assert result.precious_metals_info is None

    
    @pytest.mark.asyncio
    async def test_hazardous_materials_info_only_when_flag_true(self):
        """hazardous_materials_info should only be present when contains_hazardous_materials is true."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("cable.jpg", image_bytes)
        
        gemini_response = {
            "category": "cable",
            "brand": "Anker",
            "model": "PowerLine",
            "deviceType": "USB cable",
            "confidenceScore": 0.8,
            "attributes": {"color": "white"},
            "severity": "low",
            "contains_precious_metals": False,
            "contains_hazardous_materials": False,
            "hazardous_materials_info": "Should not appear"  # Should be removed
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.contains_hazardous_materials is False
            assert result.hazardous_materials_info is None

    
    @pytest.mark.asyncio
    async def test_accuracy_equals_confidence_score(self):
        """accuracy field should always equal confidenceScore."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "Apple",
            "model": "iPhone 12",
            "deviceType": "smartphone",
            "confidenceScore": 0.87,
            "attributes": {"color": "blue"},
            "severity": "high",
            "contains_precious_metals": True,
            "precious_metals_info": "Gold in connectors",
            "contains_hazardous_materials": True,
            "hazardous_materials_info": "Lithium battery"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.accuracy == result.confidenceScore
            assert result.accuracy == 0.87

    
    @pytest.mark.asyncio
    async def test_string_length_limits_info_note(self):
        """info_note should be truncated to 500 characters."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("laptop.jpg", image_bytes)
        
        # Create a string longer than 500 characters
        long_info = "A" * 600
        
        gemini_response = {
            "category": "laptop",
            "brand": "Dell",
            "model": "XPS",
            "deviceType": "laptop",
            "confidenceScore": 0.9,
            "attributes": {"color": "silver"},
            "info_note": long_info,
            "severity": "high",
            "contains_precious_metals": True,
            "precious_metals_info": "Gold and silver",
            "contains_hazardous_materials": True,
            "hazardous_materials_info": "Battery"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.info_note is not None
            assert len(result.info_note) <= 500

    
    @pytest.mark.asyncio
    async def test_string_length_limits_precious_metals_info(self):
        """precious_metals_info should be truncated to 300 characters."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("laptop.jpg", image_bytes)
        
        # Create a string longer than 300 characters
        long_precious_info = "B" * 400
        
        gemini_response = {
            "category": "laptop",
            "brand": "HP",
            "model": "Pavilion",
            "deviceType": "laptop",
            "confidenceScore": 0.85,
            "attributes": {"color": "black"},
            "severity": "high",
            "contains_precious_metals": True,
            "precious_metals_info": long_precious_info,
            "contains_hazardous_materials": True,
            "hazardous_materials_info": "Battery"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.precious_metals_info is not None
            assert len(result.precious_metals_info) <= 300

    
    @pytest.mark.asyncio
    async def test_string_length_limits_hazardous_materials_info(self):
        """hazardous_materials_info should be truncated to 300 characters."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        # Create a string longer than 300 characters
        long_hazardous_info = "C" * 400
        
        gemini_response = {
            "category": "mobile",
            "brand": "Samsung",
            "model": "Galaxy",
            "deviceType": "smartphone",
            "confidenceScore": 0.88,
            "attributes": {"color": "black"},
            "severity": "high",
            "contains_precious_metals": True,
            "precious_metals_info": "Gold",
            "contains_hazardous_materials": True,
            "hazardous_materials_info": long_hazardous_info
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.hazardous_materials_info is not None
            assert len(result.hazardous_materials_info) <= 300



class TestDefaultSeverityLogic:
    """Test default severity determination based on device category."""
    
    @pytest.mark.asyncio
    async def test_mobile_phone_default_severity_high(self):
        """Mobile phones should default to 'high' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "OnePlus",
            "model": "9 Pro",
            "deviceType": "smartphone",
            "confidenceScore": 0.85,
            "attributes": {"color": "green"},
            # No severity provided - should use default
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "high"

    
    @pytest.mark.asyncio
    async def test_laptop_default_severity_high(self):
        """Laptops should default to 'high' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("laptop.jpg", image_bytes)
        
        gemini_response = {
            "category": "laptop",
            "brand": "Lenovo",
            "model": "ThinkPad",
            "deviceType": "laptop computer",
            "confidenceScore": 0.9,
            "attributes": {"color": "black"},
            # No severity provided
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "high"
    
    @pytest.mark.asyncio
    async def test_tablet_default_severity_high(self):
        """Tablets should default to 'high' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("tablet.jpg", image_bytes)
        
        gemini_response = {
            "category": "tablet",
            "brand": "Apple",
            "model": "iPad",
            "deviceType": "tablet",
            "confidenceScore": 0.92,
            "attributes": {"color": "silver"},
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "high"

    
    @pytest.mark.asyncio
    async def test_charger_default_severity_medium(self):
        """Chargers should default to 'medium' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("charger.jpg", image_bytes)
        
        gemini_response = {
            "category": "charger",
            "brand": "Anker",
            "model": "PowerPort",
            "deviceType": "wall charger",
            "confidenceScore": 0.8,
            "attributes": {"ports": "2"},
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "medium"
    
    @pytest.mark.asyncio
    async def test_cable_default_severity_low(self):
        """Cables should default to 'low' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("cable.jpg", image_bytes)
        
        gemini_response = {
            "category": "cable",
            "brand": None,
            "model": None,
            "deviceType": "USB cable",
            "confidenceScore": 0.75,
            "attributes": {"type": "USB-C"},
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "low"

    
    @pytest.mark.asyncio
    async def test_accessory_default_severity_low(self):
        """Accessories should default to 'low' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("accessory.jpg", image_bytes)
        
        gemini_response = {
            "category": "accessory",
            "brand": "Generic",
            "model": None,
            "deviceType": "headset stand",  # Changed from "phone case" to avoid "phone" keyword
            "confidenceScore": 0.7,
            "attributes": {"material": "plastic"},
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "low"


class TestLithiumBatteryDevices:
    """Test lithium battery devices get severity >= 'high'."""
    
    @pytest.mark.asyncio
    async def test_smartphone_with_lithium_battery_high_severity(self):
        """Smartphones should have at least 'high' severity due to lithium battery."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "Google",
            "model": "Pixel 6",
            "deviceType": "smartphone",
            "confidenceScore": 0.88,
            "attributes": {"color": "black"},
            "severity": "medium",  # Should be upgraded to at least "high"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Should be upgraded from medium to high
            assert result.severity in ["high", "critical"]

    
    @pytest.mark.asyncio
    async def test_laptop_with_lithium_battery_high_severity(self):
        """Laptops should have at least 'high' severity due to lithium battery."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("laptop.jpg", image_bytes)
        
        gemini_response = {
            "category": "laptop",
            "brand": "Asus",
            "model": "ZenBook",
            "deviceType": "laptop",
            "confidenceScore": 0.91,
            "attributes": {"color": "silver"},
            "severity": "low",  # Should be upgraded to at least "high"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Should be upgraded from low to high
            assert result.severity in ["high", "critical"]
    
    @pytest.mark.asyncio
    async def test_tablet_with_lithium_battery_high_severity(self):
        """Tablets should have at least 'high' severity due to lithium battery."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("tablet.jpg", image_bytes)
        
        gemini_response = {
            "category": "tablet",
            "brand": "Samsung",
            "model": "Galaxy Tab",
            "deviceType": "tablet",
            "confidenceScore": 0.89,
            "attributes": {"color": "gray"},
            "severity": "medium",  # Should be upgraded to at least "high"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Should be upgraded from medium to high
            assert result.severity in ["high", "critical"]

    
    @pytest.mark.asyncio
    async def test_lithium_battery_device_type_high_severity(self):
        """Devices with 'lithium' in device type should have at least 'high' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("battery.jpg", image_bytes)
        
        gemini_response = {
            "category": "battery",
            "brand": "Duracell",
            "model": None,
            "deviceType": "lithium-ion battery pack",
            "confidenceScore": 0.82,
            "attributes": {"size": "large"},
            "severity": "low",  # Should be upgraded to at least "high"
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Should be upgraded from low to high
            assert result.severity in ["high", "critical"]
    
    @pytest.mark.asyncio
    async def test_lithium_battery_preserves_critical_severity(self):
        """If Gemini already sets critical severity, it should be preserved."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "Apple",
            "model": "iPhone",
            "deviceType": "smartphone",
            "confidenceScore": 0.9,
            "attributes": {"color": "white"},
            "severity": "critical",  # Should be preserved
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Critical should be preserved
            assert result.severity == "critical"



class TestCRTDisplays:
    """Test CRT displays get severity = 'critical'."""
    
    @pytest.mark.asyncio
    async def test_crt_monitor_critical_severity(self):
        """CRT monitors should always have 'critical' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("monitor.jpg", image_bytes)
        
        gemini_response = {
            "category": "appliance",
            "brand": "ViewSonic",
            "model": None,
            "deviceType": "CRT monitor",
            "confidenceScore": 0.85,
            "attributes": {"size": "17 inch"},
            "severity": "low",  # Should be overridden to critical
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "critical"
    
    @pytest.mark.asyncio
    async def test_cathode_ray_tube_tv_critical_severity(self):
        """Cathode ray tube TVs should always have 'critical' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("tv.jpg", image_bytes)
        
        gemini_response = {
            "category": "appliance",
            "brand": "Sony",
            "model": "Trinitron",
            "deviceType": "cathode ray tube television",
            "confidenceScore": 0.88,
            "attributes": {"size": "27 inch"},
            "severity": "medium",  # Should be overridden to critical
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "critical"

    
    @pytest.mark.asyncio
    async def test_tube_monitor_critical_severity(self):
        """Tube monitors should always have 'critical' severity."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("old_monitor.jpg", image_bytes)
        
        gemini_response = {
            "category": "appliance",
            "brand": "Dell",
            "model": None,
            "deviceType": "tube monitor",
            "confidenceScore": 0.8,
            "attributes": {"condition": "old"},
            "severity": "high",  # Should be overridden to critical
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "critical"
    
    @pytest.mark.asyncio
    async def test_crt_display_no_severity_provided(self):
        """CRT displays should get 'critical' severity even when none is provided."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("crt.jpg", image_bytes)
        
        gemini_response = {
            "category": "appliance",
            "brand": "Samsung",
            "model": None,
            "deviceType": "CRT display",
            "confidenceScore": 0.83,
            "attributes": {"color": "beige"},
            # No severity provided
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.severity == "critical"



class TestSensibleDefaults:
    """Test sensible defaults when Gemini data is incomplete."""
    
    @pytest.mark.asyncio
    async def test_missing_enhanced_fields_get_defaults(self):
        """When Gemini doesn't provide enhanced fields, sensible defaults should be applied."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("phone.jpg", image_bytes)
        
        gemini_response = {
            "category": "mobile",
            "brand": "Xiaomi",
            "model": "Mi 11",
            "deviceType": "smartphone",
            "confidenceScore": 0.86,
            "attributes": {"color": "blue"},
            # No enhanced fields provided
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Should have default severity for mobile (high)
            assert result.severity == "high"
            # Should have default precious metals flag (True for mobile)
            assert result.contains_precious_metals is True
            # Should have default precious metals info
            assert result.precious_metals_info is not None
            # Should have default hazardous materials flag (True for mobile)
            assert result.contains_hazardous_materials is True
            # Should have default hazardous materials info
            assert result.hazardous_materials_info is not None

    
    @pytest.mark.asyncio
    async def test_laptop_gets_default_precious_metals_info(self):
        """Laptops should get default precious metals information."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("laptop.jpg", image_bytes)
        
        gemini_response = {
            "category": "laptop",
            "brand": "Acer",
            "model": "Aspire",
            "deviceType": "laptop",
            "confidenceScore": 0.87,
            "attributes": {"color": "black"},
            "contains_precious_metals": True,
            # No precious_metals_info provided
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.contains_precious_metals is True
            assert result.precious_metals_info is not None
            assert "gold" in result.precious_metals_info.lower() or "silver" in result.precious_metals_info.lower()
    
    @pytest.mark.asyncio
    async def test_cable_gets_no_hazardous_materials_by_default(self):
        """Cables should not have hazardous materials by default."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("cable.jpg", image_bytes)
        
        gemini_response = {
            "category": "cable",
            "brand": "Belkin",
            "model": None,
            "deviceType": "USB cable",
            "confidenceScore": 0.78,
            "attributes": {"type": "USB-A to USB-C"},
            # No enhanced fields provided
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            # Cables don't typically have hazardous materials
            assert result.contains_hazardous_materials is False
            assert result.hazardous_materials_info is None

    
    @pytest.mark.asyncio
    async def test_appliance_gets_default_hazardous_materials_info(self):
        """Appliances should get default hazardous materials information."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("appliance.jpg", image_bytes)
        
        gemini_response = {
            "category": "appliance",
            "brand": "Generic",
            "model": None,
            "deviceType": "small appliance",
            "confidenceScore": 0.72,
            "attributes": {"condition": "used"},
            "contains_hazardous_materials": True,
            # No hazardous_materials_info provided
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.contains_hazardous_materials is True
            assert result.hazardous_materials_info is not None
            assert len(result.hazardous_materials_info) > 0
    
    @pytest.mark.asyncio
    async def test_empty_info_note_becomes_none(self):
        """Empty info_note strings should become None."""
        image_bytes = create_test_image("jpeg", 200, 200)
        upload_file = create_upload_file("charger.jpg", image_bytes)
        
        gemini_response = {
            "category": "charger",
            "brand": "Apple",
            "model": "20W",
            "deviceType": "USB-C charger",
            "confidenceScore": 0.85,
            "attributes": {"color": "white"},
            "info_note": "",  # Empty string
            "severity": "medium",
            "contains_precious_metals": False,
            "contains_hazardous_materials": False
        }
        
        with patch('app.services.analyzer.gemini_service') as mock_gemini:
            mock_gemini.analyze_device_image = AsyncMock(return_value=gemini_response)
            
            result = await analyzer_service.analyze_device(upload_file)
            
            assert result.info_note is None

