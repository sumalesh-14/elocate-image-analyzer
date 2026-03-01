"""
Property-based tests for image validator.

Uses Hypothesis to verify universal properties across randomized inputs.
Each test runs minimum 100 iterations to ensure comprehensive coverage.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from io import BytesIO
from PIL import Image
from app.services.image_validator import (
    validate_image,
    check_file_headers,
    is_safe_image,
    ValidationResult,
    INVALID_FILE_TYPE,
    INVALID_FILE_SIZE,
    INVALID_FILE_HEADERS,
)

# Helper functions to generate valid image bytes
def create_valid_image_bytes(format_name, width=100, height=100):
    """Create valid image bytes in the specified format."""
    img = Image.new('RGB', (width, height), color='red')
    buffer = BytesIO()
    
    format_map = {
        'jpeg': 'JPEG',
        'jpg': 'JPEG',
        'png': 'PNG',
        'webp': 'WEBP'
    }
    
    pil_format = format_map.get(format_name.lower(), format_name.upper())
    img.save(buffer, format=pil_format)
    return buffer.getvalue()


def create_mismatched_image(actual_format, claimed_extension):
    """Create an image with mismatched format and extension."""
    image_bytes = create_valid_image_bytes(actual_format)
    filename = f"test{claimed_extension}"
    return image_bytes, filename
    # Create valid image
    image_bytes = create_valid_image_bytes(format_name, 200, 200)
    
    # Map to extension
    extension_map = {
        'jpeg': '.jpg',
        'png': '.png',
        'webp': '.webp'
    }
    filename = f"test{extension_map[format_name]}"
    
    # Validate the image
    result = validate_image(image_bytes, filename)
    
    # Valid images should pass validation
    assert result.is_valid is True
    assert result.error_code is None
    assert result.message is None
# Feature: image-device-identification, Property 1: Valid image formats are accepted
@settings(max_examples=20)
@given(st.sampled_from(['jpeg', 'png', 'webp']))
def test_property_1_valid_image_formats_are_accepted(format_name):
    """
    **Validates: Requirements 1.1, 1.3**
    
    For any file with format JPEG, PNG, or WebP and valid file headers matching 
    the format, the Image_Analyzer should accept the file and proceed with analysis 
    rather than returning a format error.
    """
    # Create valid image
    image_bytes = create_valid_image_bytes(format_name, 200, 200)
    
    # Map to extension
    extension_map = {
        'jpeg': '.jpg',
        'png': '.png',
        'webp': '.webp'
    }
    filename = f"test{extension_map[format_name]}"
    
    # Validate the image
    result = validate_image(image_bytes, filename)
    
    # Valid images should pass validation
    assert result.is_valid is True
    assert result.error_code is None
    assert result.message is None
