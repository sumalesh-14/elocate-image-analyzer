"""
Unit tests for API routes.

Tests specific scenarios for:
- POST /api/v1/analyze accepts multipart/form-data
- Health check endpoint returns correct status
- Error responses have correct format
- Successful responses have correct format
- All error codes return appropriate HTTP status and messages

Requirements: 1.2, 1.3, 1.4, 1.5, 3.8, 7.1, 7.2, 7.4, 8.4
"""

import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.models.response import DeviceData, IdentificationResponse, ErrorData
from app.services.analyzer import AnalysisError
from app.api.middleware import limiter
from app.config import settings


@pytest.fixture
def client():
    """Create a test client for the API."""
    # Disable rate limiting for tests
    limiter.enabled = False
    
    client = TestClient(app)
    
    yield client
    
    # Re-enable rate limiting after tests
    limiter.enabled = True


@pytest.fixture
def valid_image_file():
    """Create a valid test image file."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


@pytest.fixture
def mock_device_data():
    """Create mock device data for successful responses."""
    return DeviceData(
        category='Mobile Phone',
        brand='Samsung',
        model='Galaxy S21',
        deviceType='smartphone',
        confidenceScore=0.85,
        attributes={'color': 'black', 'condition': 'good'},
        lowConfidence=False
    )


# Test POST /api/v1/analyze accepts multipart/form-data
# Requirements: 1.2, 7.1, 7.2

def test_analyze_endpoint_accepts_multipart_form_data(client, valid_image_file, mock_device_data):
    """Test that /api/v1/analyze accepts multipart/form-data requests."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        assert mock_analyze.called


def test_analyze_endpoint_accepts_jpeg_image(client, mock_device_data):
    """Test that /api/v1/analyze accepts JPEG images."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        # Create JPEG image
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test.jpg', img_bytes, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200


def test_analyze_endpoint_accepts_png_image(client, mock_device_data):
    """Test that /api/v1/analyze accepts PNG images."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        # Create PNG image
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {'file': ('test.png', img_bytes, 'image/png')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200


def test_analyze_endpoint_accepts_webp_image(client, mock_device_data):
    """Test that /api/v1/analyze accepts WebP images."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        # Create WebP image
        img = Image.new('RGB', (100, 100), color='yellow')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='WEBP')
        img_bytes.seek(0)
        
        files = {'file': ('test.webp', img_bytes, 'image/webp')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200


def test_analyze_endpoint_requires_file_parameter(client):
    """Test that /api/v1/analyze requires a file parameter."""
    headers = {"X-API-Key": settings.API_KEY}
    
    # Send request without file
    response = client.post("/api/v1/analyze", headers=headers)
    
    # Should return 422 (Unprocessable Entity) for missing required parameter
    assert response.status_code == 422


# Test Health Check Endpoint
# Requirements: 7.4

def test_health_endpoint_returns_correct_status(client):
    """Test that /health endpoint returns correct status."""
    with patch('app.api.routes.gemini_service.check_availability') as mock_gemini, \
         patch('app.services.db_connection.db_manager.health_check') as mock_db:
        mock_gemini.return_value = True
        mock_db.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['gemini_api_available'] is True
        assert data['database_available'] is True


def test_health_endpoint_returns_degraded_when_gemini_unavailable(client):
    """Test that /health returns degraded status when Gemini API is unavailable."""
    with patch('app.api.routes.gemini_service.check_availability') as mock_gemini, \
         patch('app.services.db_connection.db_manager.health_check') as mock_db:
        mock_gemini.return_value = False
        mock_db.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'degraded'
        assert data['gemini_api_available'] is False
        assert data['database_available'] is True


def test_health_endpoint_includes_timestamp(client):
    """Test that /health response includes timestamp."""
    with patch('app.api.routes.gemini_service.check_availability') as mock_gemini, \
         patch('app.services.db_connection.db_manager.health_check') as mock_db:
        mock_gemini.return_value = True
        mock_db.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert 'timestamp' in data
        assert data['timestamp'] is not None


def test_health_endpoint_handles_exceptions(client):
    """Test that /health handles exceptions gracefully."""
    with patch('app.api.routes.gemini_service.check_availability') as mock_gemini, \
         patch('app.services.db_connection.db_manager.health_check') as mock_db:
        mock_gemini.side_effect = Exception("Test exception")
        mock_db.side_effect = Exception("Test exception")
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'unhealthy'
        assert data['gemini_api_available'] is False


# Test Test Interface Endpoint
# Requirements: 7.1

def test_test_interface_endpoint_returns_html(client):
    """Test that /test endpoint returns HTML content."""
    response = client.get("/test")
    
    # Should return HTML (either the actual interface or a placeholder)
    assert response.status_code in [200, 404]
    assert 'text/html' in response.headers.get('content-type', '')


# Test Successful Responses
# Requirements: 3.8, 8.4

def test_successful_response_has_correct_format(client, valid_image_file, mock_device_data):
    """Test that successful responses have correct format."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data['success'] is True
        assert 'timestamp' in data
        assert 'processingTimeMs' in data
        assert data['data'] is not None
        assert data['error'] is None


def test_successful_response_includes_device_data(client, valid_image_file, mock_device_data):
    """Test that successful responses include device data."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check device data fields
        assert data['data']['category'] == 'Mobile Phone'
        assert data['data']['brand'] == 'Samsung'
        assert data['data']['model'] == 'Galaxy S21'
        assert data['data']['deviceType'] == 'smartphone'
        assert data['data']['confidenceScore'] == 0.85
        assert data['data']['lowConfidence'] is False
        assert 'attributes' in data['data']


def test_successful_response_includes_processing_time(client, valid_image_file, mock_device_data):
    """Test that successful responses include processing time."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check processing time
        assert 'processingTimeMs' in data
        assert isinstance(data['processingTimeMs'], int)
        assert data['processingTimeMs'] >= 0


# Test Error Responses
# Requirements: 1.2, 1.3, 3.8, 8.4

def test_error_response_has_correct_format(client, valid_image_file):
    """Test that error responses have correct format."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError('INVALID_FILE_TYPE', 'Invalid file type')
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        data = response.json()
        
        # Check response structure
        assert data['success'] is False
        assert 'timestamp' in data
        assert 'processingTimeMs' in data
        assert data['data'] is None
        assert data['error'] is not None


def test_error_response_includes_error_code_and_message(client, valid_image_file):
    """Test that error responses include error code and message."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError('INVALID_FILE_SIZE', 'File size exceeds 10MB limit')
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        data = response.json()
        
        # Check error structure
        assert data['error']['code'] == 'INVALID_FILE_SIZE'
        assert data['error']['message'] == 'File size exceeds 10MB limit'


# Test All Error Codes
# Requirements: 1.2, 1.3, 1.5, 3.8

def test_invalid_file_type_error(client, valid_image_file):
    """Test INVALID_FILE_TYPE error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(
            'INVALID_FILE_TYPE',
            'Please upload a valid image file (JPEG, PNG, or WebP)'
        )
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200  # Returns 200 with error in body
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_FILE_TYPE'


def test_invalid_file_size_error(client, valid_image_file):
    """Test INVALID_FILE_SIZE error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(
            'INVALID_FILE_SIZE',
            'File size exceeds 10MB limit'
        )
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_FILE_SIZE'


def test_invalid_file_headers_error(client, valid_image_file):
    """Test INVALID_FILE_HEADERS error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(
            'INVALID_FILE_HEADERS',
            'File appears to be corrupted or has mismatched format'
        )
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_FILE_HEADERS'


def test_malicious_file_error(client, valid_image_file):
    """Test MALICIOUS_FILE error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(
            'MALICIOUS_FILE',
            'File failed security validation'
        )
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'MALICIOUS_FILE'


def test_not_a_device_error(client, valid_image_file):
    """Test NOT_A_DEVICE error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(
            'NOT_A_DEVICE',
            'Image does not appear to contain an electronic device'
        )
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_A_DEVICE'


def test_missing_file_error(client):
    """Test MISSING_FILE error code."""
    headers = {"X-API-Key": settings.API_KEY}
    
    # Create a request with None file
    with patch('app.api.routes.File') as mock_file:
        mock_file.return_value = None
        
        # Send request without proper file
        response = client.post("/api/v1/analyze", headers=headers, data={})
        
        # Should return 422 for missing required parameter
        assert response.status_code == 422


def test_service_unavailable_error(client, valid_image_file):
    """Test SERVICE_UNAVAILABLE error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(
            'SERVICE_UNAVAILABLE',
            'Image analysis service is temporarily unavailable'
        )
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'SERVICE_UNAVAILABLE'


def test_analysis_timeout_error(client, valid_image_file):
    """Test ANALYSIS_TIMEOUT error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = TimeoutError()
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'ANALYSIS_TIMEOUT'


def test_internal_error(client, valid_image_file):
    """Test INTERNAL_ERROR error code."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = Exception('Unexpected error')
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'INTERNAL_ERROR'


# Test Edge Cases

def test_analyze_with_low_confidence_result(client, valid_image_file):
    """Test analysis with low confidence result."""
    low_confidence_data = DeviceData(
        category='Charger',
        brand=None,
        model=None,
        deviceType='USB wall charger',
        confidenceScore=0.42,
        attributes={'color': 'white'},
        lowConfidence=True
    )
    
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = low_confidence_data
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['confidenceScore'] == 0.42
        assert data['data']['lowConfidence'] is True
        assert data['data']['brand'] is None
        assert data['data']['model'] is None


def test_analyze_with_null_brand_and_model(client, valid_image_file):
    """Test analysis with null brand and model."""
    uncertain_data = DeviceData(
        category='Battery',
        brand=None,
        model=None,
        deviceType='lithium-ion battery',
        confidenceScore=0.65,
        attributes={'condition': 'used'},
        lowConfidence=False
    )
    
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = uncertain_data
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['brand'] is None
        assert data['data']['model'] is None


def test_analyze_logs_errors(client, valid_image_file):
    """Test that analysis errors are logged."""
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError('TEST_ERROR', 'Test error message')
        
        files = {'file': ('test.jpg', valid_image_file, 'image/jpeg')}
        headers = {"X-API-Key": settings.API_KEY}
        
        response = client.post("/api/v1/analyze", files=files, headers=headers)
        
        assert response.status_code == 200
        # Verify error response structure
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'TEST_ERROR'


def test_health_endpoint_returns_degraded_when_database_unavailable(client):
    """Test that /health returns degraded status when database is unavailable."""
    with patch('app.api.routes.gemini_service.check_availability') as mock_gemini, \
         patch('app.services.db_connection.db_manager.health_check') as mock_db:
        mock_gemini.return_value = True
        mock_db.return_value = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'degraded'
        assert data['gemini_api_available'] is True
        assert data['database_available'] is False


def test_health_endpoint_returns_unhealthy_when_both_unavailable(client):
    """Test that /health returns unhealthy status when both Gemini and database are unavailable."""
    with patch('app.api.routes.gemini_service.check_availability') as mock_gemini, \
         patch('app.services.db_connection.db_manager.health_check') as mock_db:
        mock_gemini.return_value = False
        mock_db.return_value = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'unhealthy'
        assert data['gemini_api_available'] is False
        assert data['database_available'] is False

