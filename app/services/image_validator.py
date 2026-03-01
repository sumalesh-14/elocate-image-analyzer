"""
Image validation service for security and format compliance.

This module validates uploaded images for:
- File format (JPEG, PNG, WebP)
- File size (max 10MB)
- File header integrity (prevents format spoofing)
- Malicious content detection
- Decompression bomb prevention
"""

import imghdr
from pathlib import Path
from typing import Optional
from PIL import Image
import io


class ValidationResult:
    """Result of image validation.
    
    Attributes:
        is_valid: Whether the image passed validation
        error_code: Error code if validation failed (None if valid)
        message: Human-readable error message (None if valid)
    """
    
    def __init__(self, is_valid: bool, error_code: Optional[str] = None, message: Optional[str] = None):
        self.is_valid = is_valid
        self.error_code = error_code
        self.message = message


# Error codes
INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
INVALID_FILE_SIZE = "INVALID_FILE_SIZE"
INVALID_FILE_HEADERS = "INVALID_FILE_HEADERS"
MALICIOUS_FILE = "MALICIOUS_FILE"
MISSING_FILE = "MISSING_FILE"

# Configuration
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
MAX_DIMENSION = 10000  # Maximum width or height to prevent decompression bombs


def validate_image(file_bytes: bytes, filename: str) -> ValidationResult:
    """
    Validate an uploaded image file for security and format compliance.
    
    Args:
        file_bytes: The raw bytes of the uploaded file
        filename: The original filename of the uploaded file
        
    Returns:
        ValidationResult indicating whether the file is valid and any error details
        
    Validates:
        - File is not empty
        - File extension is allowed (JPEG, PNG, WebP)
        - File size is within limits (max 10MB)
        - File headers match the declared extension
        - File is a genuine image without malicious content
        - Image dimensions are reasonable (prevents decompression bombs)
    """
    # Check if file is empty
    if not file_bytes:
        return ValidationResult(
            is_valid=False,
            error_code=MISSING_FILE,
            message="No image file provided"
        )
    
    # Check file extension
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return ValidationResult(
            is_valid=False,
            error_code=INVALID_FILE_TYPE,
            message=f"Invalid file type. Allowed formats: JPEG, PNG, WebP"
        )
    
    # Check file size
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            error_code=INVALID_FILE_SIZE,
            message=f"File size ({size_mb:.2f}MB) exceeds 10MB limit"
        )
    
    # Check file headers match extension
    if not check_file_headers(file_bytes, extension):
        return ValidationResult(
            is_valid=False,
            error_code=INVALID_FILE_HEADERS,
            message="File headers do not match declared format. File may be corrupted or misnamed."
        )
    
    # Check for malicious content and validate image integrity
    if not is_safe_image(file_bytes):
        return ValidationResult(
            is_valid=False,
            error_code=MALICIOUS_FILE,
            message="File failed security validation"
        )
    
    # All checks passed
    return ValidationResult(is_valid=True)


def check_file_headers(file_bytes: bytes, extension: str) -> bool:
    """
    Verify that file headers match the declared file extension.
    
    This prevents attacks where malicious files are renamed to appear as images.
    
    Args:
        file_bytes: The raw bytes of the file
        extension: The file extension (e.g., '.jpg', '.png')
        
    Returns:
        True if headers match extension, False otherwise
    """
    # Use imghdr to detect actual image type from headers
    detected_type = imghdr.what(None, h=file_bytes)
    
    # Map file extensions to expected imghdr types
    extension_map = {
        '.jpg': 'jpeg',
        '.jpeg': 'jpeg',
        '.png': 'png',
        '.webp': 'webp'
    }
    
    expected_type = extension_map.get(extension.lower())
    
    # Check if detected type matches expected type
    return detected_type == expected_type


def is_safe_image(file_bytes: bytes) -> bool:
    """
    Check if the file is a genuine image without malicious content.
    
    This function:
    - Verifies the file can be opened as an image
    - Validates image format is one of the allowed types
    - Checks dimensions to prevent decompression bombs
    - Uses PIL's verify() to detect corrupted or malicious images
    
    Args:
        file_bytes: The raw bytes of the file
        
    Returns:
        True if the image is safe, False otherwise
    """
    try:
        # Try to open the image with PIL
        image = Image.open(io.BytesIO(file_bytes))
        
        # Verify it's a valid image (this checks for corruption)
        image.verify()
        
        # Check format is allowed
        if image.format not in ['JPEG', 'PNG', 'WEBP']:
            return False
        
        # Reopen the image (verify() closes the file)
        image = Image.open(io.BytesIO(file_bytes))
        
        # Check dimensions to prevent decompression bombs
        # A decompression bomb is a small compressed file that expands to huge dimensions
        if image.width > MAX_DIMENSION or image.height > MAX_DIMENSION:
            return False
        
        return True
        
    except Exception:
        # Any exception during image processing indicates an invalid or malicious file
        return False
