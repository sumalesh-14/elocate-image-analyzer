"""
Unit tests for response models.

Tests the Pydantic models to ensure proper validation and behavior.
"""

import pytest
from datetime import datetime
from app.models.response import (
    DeviceData,
    ErrorData,
    IdentificationResponse,
    HealthResponse
)


def create_device_data(**kwargs):
    """Helper function to create DeviceData with default enhanced fields."""
    defaults = {
        "accuracy": kwargs.get("confidenceScore", 0.5),
        "severity": "medium",
        "contains_precious_metals": False,
        "precious_metals_info": None,
        "contains_hazardous_materials": False,
        "hazardous_materials_info": None,
        "info_note": None
    }
    defaults.update(kwargs)
    return DeviceData(**defaults)


class TestDeviceData:
    """Tests for DeviceData model."""
    
    def test_valid_device_data(self):
        """Test creating valid DeviceData instance."""
        data = create_device_data(
            category="mobile",
            brand="Samsung",
            model="Galaxy S21",
            deviceType="smartphone",
            confidenceScore=0.87,
            attributes={"color": "black", "condition": "good"}
        )
        
        assert data.category == "mobile"
        assert data.brand == "Samsung"
        assert data.model == "Galaxy S21"
        assert data.deviceType == "smartphone"
        assert data.confidenceScore == 0.87
        assert data.accuracy == 0.87
        assert data.attributes == {"color": "black", "condition": "good"}
        assert data.lowConfidence is False
    
    def test_device_data_with_null_brand_model(self):
        """Test DeviceData with null brand and model."""
        data = create_device_data(
            category="charger",
            brand=None,
            model=None,
            deviceType="USB wall charger",
            confidenceScore=0.42,
            attributes={"color": "white"}
        )
        
        assert data.brand is None
        assert data.model is None
        assert data.lowConfidence is True
    
    def test_low_confidence_flag_set_correctly(self):
        """Test lowConfidence flag is set when confidence < 0.5."""
        # High confidence
        data_high = create_device_data(
            category="laptop",
            brand="Apple",
            model="MacBook Pro",
            deviceType="laptop",
            confidenceScore=0.95
        )
        assert data_high.lowConfidence is False
        
        # Low confidence
        data_low = create_device_data(
            category="battery",
            brand=None,
            model=None,
            deviceType="lithium-ion battery",
            confidenceScore=0.3
        )
        assert data_low.lowConfidence is True
        
        # Boundary case - exactly 0.5
        data_boundary = create_device_data(
            category="cable",
            brand="Generic",
            model=None,
            deviceType="USB cable",
            confidenceScore=0.5
        )
        assert data_boundary.lowConfidence is False
    
    def test_confidence_score_validation(self):
        """Test confidence score must be between 0.0 and 1.0."""
        # Valid scores
        create_device_data(
            category="mobile",
            brand="Test",
            model="Test",
            deviceType="smartphone",
            confidenceScore=0.0
        )
        
        create_device_data(
            category="mobile",
            brand="Test",
            model="Test",
            deviceType="smartphone",
            confidenceScore=1.0
        )
        
        # Invalid scores
        with pytest.raises(ValueError):
            create_device_data(
                category="mobile",
                brand="Test",
                model="Test",
                deviceType="smartphone",
                confidenceScore=-0.1
            )
        
        with pytest.raises(ValueError):
            create_device_data(
                category="mobile",
                brand="Test",
                model="Test",
                deviceType="smartphone",
                confidenceScore=1.1
            )
    
    def test_default_attributes(self):
        """Test attributes defaults to empty dict."""
        data = create_device_data(
            category="tablet",
            brand="Apple",
            model="iPad",
            deviceType="tablet",
            confidenceScore=0.8
        )
        assert data.attributes == {}


class TestErrorData:
    """Tests for ErrorData model."""
    
    def test_valid_error_data(self):
        """Test creating valid ErrorData instance."""
        error = ErrorData(
            code="INVALID_FILE_SIZE",
            message="File size exceeds 10MB limit"
        )
        
        assert error.code == "INVALID_FILE_SIZE"
        assert error.message == "File size exceeds 10MB limit"
    
    def test_required_fields(self):
        """Test that code and message are required."""
        with pytest.raises(ValueError):
            ErrorData(code="TEST")
        
        with pytest.raises(ValueError):
            ErrorData(message="Test message")


class TestIdentificationResponse:
    """Tests for IdentificationResponse model."""
    
    def test_success_response(self):
        """Test successful identification response."""
        device_data = create_device_data(
            category="mobile",
            brand="Samsung",
            model="Galaxy S21",
            deviceType="smartphone",
            confidenceScore=0.87,
            attributes={"color": "black"}
        )
        
        response = IdentificationResponse(
            success=True,
            processingTimeMs=3456,
            data=device_data,
            error=None
        )
        
        assert response.success is True
        assert response.processingTimeMs == 3456
        assert response.data == device_data
        assert response.error is None
        assert isinstance(response.timestamp, datetime)
    
    def test_error_response(self):
        """Test error identification response."""
        error_data = ErrorData(
            code="INVALID_FILE_SIZE",
            message="File size exceeds 10MB limit"
        )
        
        response = IdentificationResponse(
            success=False,
            processingTimeMs=45,
            data=None,
            error=error_data
        )
        
        assert response.success is False
        assert response.processingTimeMs == 45
        assert response.data is None
        assert response.error == error_data
    
    def test_processing_time_validation(self):
        """Test processing time must be non-negative."""
        # Valid processing time
        IdentificationResponse(
            success=True,
            processingTimeMs=0,
            data=None
        )
        
        # Invalid processing time
        with pytest.raises(ValueError):
            IdentificationResponse(
                success=True,
                processingTimeMs=-1,
                data=None
            )
    
    def test_timestamp_auto_generated(self):
        """Test timestamp is automatically generated."""
        response = IdentificationResponse(
            success=True,
            processingTimeMs=100,
            data=None
        )
        
        assert response.timestamp is not None
        assert isinstance(response.timestamp, datetime)
    
    def test_json_serialization(self):
        """Test response can be serialized to JSON."""
        device_data = DeviceData(
            category="mobile",
            brand="Samsung",
            model="Galaxy S21",
            deviceType="smartphone",
            confidenceScore=0.87
        )
        
        response = IdentificationResponse(
            success=True,
            processingTimeMs=3456,
            data=device_data
        )
        
        json_data = response.model_dump()
        assert json_data['success'] is True
        assert json_data['processingTimeMs'] == 3456
        assert json_data['data']['category'] == "mobile"


class TestHealthResponse:
    """Tests for HealthResponse model."""
    
    def test_healthy_response(self):
        """Test healthy service response."""
        response = HealthResponse(
            status="healthy",
            gemini_api_available=True
        )
        
        assert response.status == "healthy"
        assert response.gemini_api_available is True
        assert isinstance(response.timestamp, datetime)
    
    def test_degraded_response(self):
        """Test degraded service response."""
        response = HealthResponse(
            status="degraded",
            gemini_api_available=False
        )
        
        assert response.status == "degraded"
        assert response.gemini_api_available is False
    
    def test_timestamp_auto_generated(self):
        """Test timestamp is automatically generated."""
        response = HealthResponse(
            status="healthy",
            gemini_api_available=True
        )
        
        assert response.timestamp is not None
        assert isinstance(response.timestamp, datetime)

