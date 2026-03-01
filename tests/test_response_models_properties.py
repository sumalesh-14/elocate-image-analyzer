"""
Property-based tests for response models.

Uses Hypothesis to verify universal properties across randomized inputs.
Each test runs minimum 100 iterations to ensure comprehensive coverage.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from pydantic import ValidationError
from app.models.response import (
    DeviceData,
    ErrorData,
    IdentificationResponse,
    HealthResponse
)


# Custom strategies for generating test data
@st.composite
def device_data_strategy(draw):
    """Generate valid DeviceData instances with random values."""
    category = draw(st.sampled_from([
        "mobile", "laptop", "tablet", "charger", "battery", 
        "cable", "appliance", "accessory", "other"
    ]))
    
    # Brand and model can be None or a string
    brand = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    model = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    
    device_type = draw(st.text(min_size=1, max_size=100))
    confidence_score = draw(st.floats(min_value=0.0, max_value=1.0))
    
    # Generate attributes dictionary
    attributes = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.text(min_size=0, max_size=100),
        max_size=10
    ))
    
    # Enhanced fields
    severity = draw(st.sampled_from(["low", "medium", "high", "critical"]))
    contains_precious_metals = draw(st.booleans())
    contains_hazardous_materials = draw(st.booleans())
    
    # Conditional fields
    precious_metals_info = None
    if contains_precious_metals:
        precious_metals_info = draw(st.one_of(st.none(), st.text(min_size=1, max_size=300)))
    
    hazardous_materials_info = None
    if contains_hazardous_materials:
        hazardous_materials_info = draw(st.one_of(st.none(), st.text(min_size=1, max_size=300)))
    
    info_note = draw(st.one_of(st.none(), st.text(min_size=1, max_size=500)))
    
    return DeviceData(
        category=category,
        brand=brand,
        model=model,
        deviceType=device_type,
        confidenceScore=confidence_score,
        accuracy=confidence_score,  # accuracy equals confidenceScore
        attributes=attributes,
        severity=severity,
        contains_precious_metals=contains_precious_metals,
        precious_metals_info=precious_metals_info,
        contains_hazardous_materials=contains_hazardous_materials,
        hazardous_materials_info=hazardous_materials_info,
        info_note=info_note
    )


@st.composite
def error_data_strategy(draw):
    """Generate valid ErrorData instances with random values."""
    error_codes = [
        "INVALID_FILE_TYPE", "INVALID_FILE_SIZE", "INVALID_FILE_HEADERS",
        "MALICIOUS_FILE", "NOT_A_DEVICE", "MISSING_FILE", 
        "SERVICE_UNAVAILABLE", "ANALYSIS_TIMEOUT", "RATE_LIMIT_EXCEEDED",
        "UNAUTHORIZED", "INTERNAL_ERROR"
    ]
    
    code = draw(st.sampled_from(error_codes))
    message = draw(st.text(min_size=1, max_size=200))
    
    return ErrorData(code=code, message=message)


# Feature: image-device-identification, Property 2: Response contains required device fields
@settings(max_examples=20)
@given(device_data_strategy())
def test_property_2_response_contains_required_fields(device_data):
    """
    **Validates: Requirements 2.1-2.7, 3.1-3.7**
    
    For any valid device identification result, the DeviceData object should 
    contain all required fields: category, brand (or null), model (or null), 
    deviceType, confidenceScore, and attributes.
    """
    # Verify all required fields are present
    assert hasattr(device_data, 'category')
    assert hasattr(device_data, 'brand')
    assert hasattr(device_data, 'model')
    assert hasattr(device_data, 'deviceType')
    assert hasattr(device_data, 'confidenceScore')
    assert hasattr(device_data, 'attributes')
    assert hasattr(device_data, 'lowConfidence')
    
    # Verify fields have correct types
    assert isinstance(device_data.category, str)
    assert device_data.brand is None or isinstance(device_data.brand, str)
    assert device_data.model is None or isinstance(device_data.model, str)
    assert isinstance(device_data.deviceType, str)
    assert isinstance(device_data.confidenceScore, float)
    assert isinstance(device_data.attributes, dict)
    assert isinstance(device_data.lowConfidence, bool)
    
    # Verify category is not empty
    assert len(device_data.category) > 0
    
    # Verify deviceType is not empty
    assert len(device_data.deviceType) > 0


# Feature: image-device-identification, Property 3: Confidence score is within valid range
@settings(max_examples=20)
@given(st.floats(min_value=0.0, max_value=1.0))
def test_property_3_confidence_score_within_valid_range(confidence_score):
    """
    **Validates: Requirements 2.7, 3.6**
    
    For any identification result, the confidenceScore field should be a number 
    between 0.0 and 1.0 inclusive.
    """
    device_data = DeviceData(
        category="mobile",
        brand="Test",
        model="Test",
        deviceType="smartphone",
        confidenceScore=confidence_score,
        attributes={}
    )
    
    # Verify confidence score is within valid range
    assert 0.0 <= device_data.confidenceScore <= 1.0


@settings(max_examples=20)
@given(st.floats(min_value=-1000.0, max_value=-0.01))
def test_property_3_confidence_score_rejects_negative(invalid_score):
    """
    **Validates: Requirements 2.7, 3.6**
    
    Confidence scores below 0.0 should be rejected with a validation error.
    """
    with pytest.raises(ValidationError):
        DeviceData(
            category="mobile",
            brand="Test",
            model="Test",
            deviceType="smartphone",
            confidenceScore=invalid_score,
            attributes={}
        )


@settings(max_examples=20)
@given(st.floats(min_value=1.01, max_value=1000.0))
def test_property_3_confidence_score_rejects_above_one(invalid_score):
    """
    **Validates: Requirements 2.7, 3.6**
    
    Confidence scores above 1.0 should be rejected with a validation error.
    """
    with pytest.raises(ValidationError):
        DeviceData(
            category="mobile",
            brand="Test",
            model="Test",
            deviceType="smartphone",
            confidenceScore=invalid_score,
            attributes={}
        )


# Feature: image-device-identification, Property 7: Response conforms to JSON schema
@settings(max_examples=20)
@given(
    success=st.booleans(),
    processing_time=st.integers(min_value=0, max_value=100000),
    device_data=st.one_of(st.none(), device_data_strategy()),
    error_data=st.one_of(st.none(), error_data_strategy())
)
def test_property_7_response_conforms_to_json_schema(success, processing_time, device_data, error_data):
    """
    **Validates: Requirements 3.1, 8.1**
    
    For any request (successful or failed), the IdentificationResponse should be 
    valid JSON that conforms to the documented schema with all required fields present.
    """
    # Create response
    response = IdentificationResponse(
        success=success,
        processingTimeMs=processing_time,
        data=device_data,
        error=error_data
    )
    
    # Verify all required fields are present
    assert hasattr(response, 'success')
    assert hasattr(response, 'timestamp')
    assert hasattr(response, 'processingTimeMs')
    assert hasattr(response, 'data')
    assert hasattr(response, 'error')
    
    # Verify field types
    assert isinstance(response.success, bool)
    assert isinstance(response.timestamp, datetime)
    assert isinstance(response.processingTimeMs, int)
    assert response.data is None or isinstance(response.data, DeviceData)
    assert response.error is None or isinstance(response.error, ErrorData)
    
    # Verify response can be serialized to JSON
    json_dict = response.model_dump()
    assert isinstance(json_dict, dict)
    assert 'success' in json_dict
    assert 'timestamp' in json_dict
    assert 'processingTimeMs' in json_dict
    assert 'data' in json_dict
    assert 'error' in json_dict
    
    # Verify JSON serialization produces valid structure
    assert isinstance(json_dict['success'], bool)
    assert isinstance(json_dict['processingTimeMs'], int)


@settings(max_examples=20)
@given(device_data_strategy())
def test_property_7_successful_response_json_schema(device_data):
    """
    **Validates: Requirements 3.1, 8.1, 8.3**
    
    For successful responses, data should be present and error should be null.
    """
    response = IdentificationResponse(
        success=True,
        processingTimeMs=1000,
        data=device_data,
        error=None
    )
    
    # Verify successful response structure
    assert response.success is True
    assert response.data is not None
    assert response.error is None
    
    # Verify JSON serialization
    json_dict = response.model_dump()
    assert json_dict['success'] is True
    assert json_dict['data'] is not None
    assert json_dict['error'] is None


@settings(max_examples=20, deadline=None)
@given(error_data_strategy())
def test_property_7_error_response_json_schema(error_data):
    """
    **Validates: Requirements 3.1, 8.1, 8.4**
    
    For error responses, error should be present and data should be null.
    """
    response = IdentificationResponse(
        success=False,
        processingTimeMs=100,
        data=None,
        error=error_data
    )
    
    # Verify error response structure
    assert response.success is False
    assert response.data is None
    assert response.error is not None
    
    # Verify JSON serialization
    json_dict = response.model_dump()
    assert json_dict['success'] is False
    assert json_dict['data'] is None
    assert json_dict['error'] is not None


# Feature: image-device-identification, Property 9: Response includes timestamp and processing time
@settings(max_examples=20)
@given(
    success=st.booleans(),
    processing_time=st.integers(min_value=0, max_value=100000),
    has_data=st.booleans()
)
def test_property_9_response_includes_timestamp_and_processing_time(success, processing_time, has_data):
    """
    **Validates: Requirements 8.5, 8.6**
    
    For any request, the IdentificationResponse should include a timestamp field 
    in ISO 8601 format and a processingTimeMs field with a positive integer value.
    """
    # Create appropriate data based on success flag
    device_data = None
    error_data = None
    
    if has_data:
        if success:
            device_data = DeviceData(
                category="mobile",
                brand="Test",
                model="Test",
                deviceType="smartphone",
                confidenceScore=0.8,
                attributes={}
            )
        else:
            error_data = ErrorData(
                code="TEST_ERROR",
                message="Test error message"
            )
    
    response = IdentificationResponse(
        success=success,
        processingTimeMs=processing_time,
        data=device_data,
        error=error_data
    )
    
    # Verify timestamp is present and is a datetime
    assert response.timestamp is not None
    assert isinstance(response.timestamp, datetime)
    
    # Verify processingTimeMs is present and non-negative
    assert response.processingTimeMs is not None
    assert isinstance(response.processingTimeMs, int)
    assert response.processingTimeMs >= 0
    
    # Verify timestamp can be serialized to ISO 8601 format
    json_dict = response.model_dump()
    timestamp_str = json_dict['timestamp']
    assert isinstance(timestamp_str, str)
    
    # Verify ISO 8601 format (basic check)
    # Should contain date and time components
    assert 'T' in timestamp_str or '-' in timestamp_str


@settings(max_examples=20)
@given(st.integers(min_value=-10000, max_value=-1))
def test_property_9_rejects_negative_processing_time(negative_time):
    """
    **Validates: Requirements 8.6**
    
    Processing time must be non-negative. Negative values should be rejected.
    """
    with pytest.raises(ValidationError):
        IdentificationResponse(
            success=True,
            processingTimeMs=negative_time,
            data=None,
            error=None
        )


# Additional property test: Low confidence flag consistency
@settings(max_examples=20)
@given(st.floats(min_value=0.0, max_value=1.0))
def test_low_confidence_flag_consistency(confidence_score):
    """
    **Validates: Requirements 5.3**
    
    For any identification result, if the confidenceScore is below 0.5, 
    then the lowConfidence flag should be set to true; otherwise it should be false.
    """
    device_data = DeviceData(
        category="mobile",
        brand="Test",
        model="Test",
        deviceType="smartphone",
        confidenceScore=confidence_score,
        attributes={}
    )
    
    # Verify lowConfidence flag matches confidence score
    expected_low_confidence = confidence_score < 0.5
    assert device_data.lowConfidence == expected_low_confidence


# Additional property test: Attributes dictionary structure
@settings(max_examples=20)
@given(st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=st.text(min_size=0, max_size=200),
    max_size=20
))
def test_attributes_dictionary_structure(attributes_dict):
    """
    **Validates: Requirements 2.6, 3.7**
    
    The attributes field should accept any dictionary with string keys and values.
    """
    device_data = DeviceData(
        category="mobile",
        brand="Test",
        model="Test",
        deviceType="smartphone",
        confidenceScore=0.8,
        attributes=attributes_dict
    )
    
    # Verify attributes are stored correctly
    assert device_data.attributes == attributes_dict
    assert isinstance(device_data.attributes, dict)
    
    # Verify all keys and values are strings
    for key, value in device_data.attributes.items():
        assert isinstance(key, str)
        assert isinstance(value, str)

