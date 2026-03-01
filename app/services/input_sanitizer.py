"""
Input sanitization service for database queries.

This module provides input validation and sanitization to prevent SQL injection
and other input-based attacks. All user input strings should be validated before
being used in database queries.
"""

import re
from typing import Optional


class InputSanitizer:
    """
    Utility class for input validation and sanitization.
    
    Validates and sanitizes all input strings before database queries to prevent
    SQL injection and other input-based attacks. Works in conjunction with
    parameterized queries for defense in depth.
    """
    
    # Maximum length for input strings to prevent DoS attacks
    MAX_INPUT_LENGTH = 200
    
    # Allowed characters: alphanumeric, spaces, hyphens, underscores, and common punctuation
    # This pattern allows legitimate device names while blocking SQL injection attempts
    ALLOWED_PATTERN = re.compile(r'^[\w\s\-.,()&+/]+$', re.UNICODE)
    
    # Patterns that indicate potential SQL injection attempts
    SQL_INJECTION_PATTERNS = [
        re.compile(r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)', re.IGNORECASE),
        re.compile(r'(--|;|\/\*|\*\/|xp_|sp_)', re.IGNORECASE),
        re.compile(r'(\bOR\b.*=.*|1\s*=\s*1|\'.*\'.*=.*\')', re.IGNORECASE),
        re.compile(r'(\bUNION\b.*\bSELECT\b)', re.IGNORECASE),
    ]

    @staticmethod
    def sanitize(text: str) -> Optional[str]:
        """
        Validate and sanitize input text for database queries.
        
        Performs the following checks:
        1. Rejects None or empty strings
        2. Rejects strings exceeding maximum length
        3. Rejects strings containing SQL injection patterns
        4. Validates against allowed character pattern
        5. Strips leading/trailing whitespace
        
        Args:
            text: Input string to sanitize
            
        Returns:
            Sanitized string if valid, None if rejected
            
        Examples:
            >>> InputSanitizer.sanitize("iPhone 14 Pro")
            'iPhone 14 Pro'
            >>> InputSanitizer.sanitize("Apple MacBook Pro (M2)")
            'Apple MacBook Pro (M2)'
            >>> InputSanitizer.sanitize("'; DROP TABLE device_category; --")
            None
            >>> InputSanitizer.sanitize("1' OR '1'='1")
            None
        """
        # Reject None or empty strings
        if not text or not isinstance(text, str):
            return None
        
        # Strip whitespace
        text = text.strip()
        
        # Reject empty after stripping
        if not text:
            return None
        
        # Reject strings exceeding maximum length
        if len(text) > InputSanitizer.MAX_INPUT_LENGTH:
            return None
        
        # Check for SQL injection patterns
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if pattern.search(text):
                return None
        
        # Validate against allowed character pattern
        if not InputSanitizer.ALLOWED_PATTERN.match(text):
            return None
        
        return text

    @staticmethod
    def is_valid(text: str) -> bool:
        """
        Check if input text is valid without sanitizing.
        
        Useful for validation without modification.
        
        Args:
            text: Input string to validate
            
        Returns:
            True if valid, False otherwise
        """
        return InputSanitizer.sanitize(text) is not None

