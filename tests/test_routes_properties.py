"""
Property-based tests for API routes.

These tests validate universal properties that should hold across all inputs:
- Property 6: Error responses contain error information
- Property 8: Successful responses include data object
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import io
from PIL import Image

from app.models.response import DeviceData, IdentificationResponse, ErrorData


# Test client fixture
@pytest.fixture
def client():
    """Create a test client for the API."""
    from app.main import app
    from app.api.middleware import limiter
    
    # Disable rate limiting for tests
    limiter.enabled = False
    
    client = TestClient(app)
    
    yield client
    
    # Re-enable rate limiting after tests
    limiter.enabled = True


# Strategy for generating valid image bytes
@st.composite
def valid_image_bytes(draw):
    """Generate valid image bytes for testing."""
    # Create a simple test image
    width = draw(st.integers(min_value=100, max_value=1000))
    height = draw(st.integers(min_value=100, max_value=1000))
    color = draw(st.tuples(
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255)
    ))
    
    # Create image
    img = Image.new('RGB', (width, height), color=color)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()


# Strategy for generating error codes
error_codes = st.sampled_from([
    "INVALID_FILE_TYPE",
    "INVALID_FILE_SIZE",
    "INVALID_FILE_HEADERS",
    "MALICIOUS_FILE",
    "NOT_A_DEVICE",
    "MISSING_FILE",
    "SERVICE_UNAVAILABLE",
    "ANALYSIS_TIMEOUT",
    "RATE_LIMIT_EXCEEDED",
    "UNAUTHORIZED",
    "INTERNAL_ERROR"
])


# Feature: image-device-identification, Property 6: Error responses contain error information
@given(error_code=error_codes, error_message=st.text(min_size=1, max_size=200))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50, deadline=500)
def test_error_responses_contain_error_information(client, error_code, error_message):
    """
    **Validates: Requirements 3.8, 8.2, 8.3, 8.4**
    
    For any request that fails during processing, the IdentificationResponse should have 
    success set to false and the error object should contain both code and message fields 
    with descriptive information.
    """
    from app.services.analyzer import AnalysisError
    
    # Mock the analyzer to raise an error
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.side_effect = AnalysisError(error_code, error_message)
        
        # Create a dummy file
        files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
        
        # Make request (skip auth for testing)
        with patch('app.api.middleware.settings.API_KEY', 'test-key'):
            response = client.post(
                "/api/v1/analyze",
                files=files,
                headers={"X-API-Key": "test-key"}
            )
        
        # Verify response structure
        assert response.status_code in [200, 400, 401, 429, 500, 503, 504]
        
        data = response.json()
        
        # Property: Error responses must have success=False
        assert data['success'] is False
        
        # Property: Error responses must have error object
        assert 'error' in data
        assert data['error'] is not None
        
        # Property: Error object must have code field
        assert 'code' in data['error']
        assert data['error']['code'] is not None
        assert isinstance(data['error']['code'], str)
        assert len(data['error']['code']) > 0
        
        # Property: Error object must have message field
        assert 'message' in data['error']
        assert data['error']['message'] is not None
        assert isinstance(data['error']['message'], str)
        assert len(data['error']['message']) > 0
        
        # Property: Error responses should have null data
        assert data['data'] is None
        
        # Property: Response must include timestamp
        assert 'timestamp' in data
        assert data['timestamp'] is not None
        
        # Property: Response must include processingTimeMs
        assert 'processingTimeMs' in data
        assert isinstance(data['processingTimeMs'], int)
        assert data['processingTimeMs'] >= 0


# Feature: image-device-identification, Property 8: Successful responses include data object
@given(
    category=st.sampled_from(['Mobile Phone', 'Laptop', 'Tablet', 'Charger', 'Battery']),
    brand=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    model=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    device_type=st.text(min_size=1, max_size=50),
    confidence=st.floats(min_value=0.0, max_value=1.0)
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
def test_successful_responses_include_data_object(
    client, category, brand, model, device_type, confidence
):
    """
    **Validates: Requirements 8.2, 8.3**
    
    For any successful identification (success = true), the IdentificationResponse should 
    include a data object containing device information, and the error field should be null.
    """
    # Mock the analyzer to return successful data
    mock_device_data = DeviceData(
        category=category,
        brand=brand,
        model=model,
        deviceType=device_type,
        confidenceScore=confidence,
        attributes={'color': 'black', 'condition': 'good'},
        lowConfidence=confidence < 0.5
    )
    
    with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
        mock_analyze.return_value = mock_device_data
        
        # Create a dummy file
        files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
        
        # Make request (skip auth for testing)
        with patch('app.api.middleware.settings.API_KEY', 'test-key'):
            response = client.post(
                "/api/v1/analyze",
                files=files,
                headers={"X-API-Key": "test-key"}
            )
        
        # Verify response
        assert response.status_code == 200
        
        data = response.json()
        
        # Property: Successful responses must have success=True
        assert data['success'] is True
        
        # Property: Successful responses must have data object
        assert 'data' in data
        assert data['data'] is not None
        
        # Property: Data object must contain device information
        assert 'category' in data['data']
        assert 'brand' in data['data']
        assert 'model' in data['data']
        assert 'deviceType' in data['data']
        assert 'confidenceScore' in data['data']
        assert 'attributes' in data['data']
        assert 'lowConfidence' in data['data']
        
        # Property: Successful responses should have null error
        assert data['error'] is None
        
        # Property: Response must include timestamp
        assert 'timestamp' in data
        assert data['timestamp'] is not None
        
        # Property: Response must include processingTimeMs
        assert 'processingTimeMs' in data
        assert isinstance(data['processingTimeMs'], int)
        assert data['processingTimeMs'] >= 0
        
        # Property: Data values should match what was returned
        assert data['data']['category'] == category
        assert data['data']['brand'] == brand
        assert data['data']['model'] == model
        assert data['data']['deviceType'] == device_type
        assert data['data']['confidenceScore'] == confidence
        assert data['data']['lowConfidence'] == (confidence < 0.5)


# Additional property test: Response structure consistency
@given(
    should_succeed=st.booleans(),
    confidence=st.floats(min_value=0.0, max_value=1.0)
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
def test_response_structure_consistency(client, should_succeed, confidence):
    """
    For any response (success or failure), the response structure should be consistent
    with required fields present.
    """
    if should_succeed:
        # Mock successful response
        mock_device_data = DeviceData(
            category='Mobile Phone',
            brand='TestBrand',
            model='TestModel',
            deviceType='smartphone',
            confidenceScore=confidence,
            attributes={},
            lowConfidence=confidence < 0.5
        )
        
        with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
            mock_analyze.return_value = mock_device_data
            
            files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
            
            with patch('app.api.middleware.settings.API_KEY', 'test-key'):
                response = client.post(
                    "/api/v1/analyze",
                    files=files,
                    headers={"X-API-Key": "test-key"}
                )
    else:
        # Mock error response
        from app.services.analyzer import AnalysisError
        
        with patch('app.api.routes.analyzer_service.analyze_device') as mock_analyze:
            mock_analyze.side_effect = AnalysisError('TEST_ERROR', 'Test error message')
            
            files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
            
            with patch('app.api.middleware.settings.API_KEY', 'test-key'):
                response = client.post(
                    "/api/v1/analyze",
                    files=files,
                    headers={"X-API-Key": "test-key"}
                )
    
    # Verify consistent structure
    data = response.json()
    
    # Property: All responses must have these fields
    assert 'success' in data
    assert 'timestamp' in data
    assert 'processingTimeMs' in data
    assert 'data' in data
    assert 'error' in data
    
    # Property: success field must be boolean
    assert isinstance(data['success'], bool)
    
    # Property: Exactly one of data or error should be non-null
    if data['success']:
        assert data['data'] is not None
        assert data['error'] is None
    else:
        assert data['data'] is None
        assert data['error'] is not None

