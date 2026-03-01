"""
Unit tests for input sanitization service.

Tests validation and sanitization of input strings to prevent SQL injection
and other input-based attacks.
"""

import pytest

from app.services.input_sanitizer import InputSanitizer


class TestInputSanitizer:
    """Test suite for InputSanitizer class."""
    
    def test_sanitize_valid_simple_text(self):
        """Test sanitization of valid simple text."""
        result = InputSanitizer.sanitize("iPhone 14 Pro")
        assert result == "iPhone 14 Pro"
    
    def test_sanitize_valid_with_hyphens(self):
        """Test sanitization of valid text with hyphens."""
        result = InputSanitizer.sanitize("Samsung Galaxy-S23")
        assert result == "Samsung Galaxy-S23"
    
    def test_sanitize_valid_with_parentheses(self):
        """Test sanitization of valid text with parentheses."""
        result = InputSanitizer.sanitize("MacBook Pro (M2)")
        assert result == "MacBook Pro (M2)"
    
    def test_sanitize_valid_with_numbers(self):
        """Test sanitization of valid text with numbers."""
        result = InputSanitizer.sanitize("iPhone 14 Pro Max")
        assert result == "iPhone 14 Pro Max"
    
    def test_sanitize_valid_with_ampersand(self):
        """Test sanitization of valid text with ampersand."""
        result = InputSanitizer.sanitize("Phones & Tablets")
        assert result == "Phones & Tablets"
    
    def test_sanitize_valid_with_slash(self):
        """Test sanitization of valid text with slash."""
        result = InputSanitizer.sanitize("Laptop/Notebook")
        assert result == "Laptop/Notebook"
    
    def test_sanitize_strips_whitespace(self):
        """Test that sanitization strips leading/trailing whitespace."""
        result = InputSanitizer.sanitize("  iPhone 14  ")
        assert result == "iPhone 14"
    
    def test_sanitize_rejects_none(self):
        """Test that None input is rejected."""
        result = InputSanitizer.sanitize(None)
        assert result is None
    
    def test_sanitize_rejects_empty_string(self):
        """Test that empty string is rejected."""
        result = InputSanitizer.sanitize("")
        assert result is None
    
    def test_sanitize_rejects_whitespace_only(self):
        """Test that whitespace-only string is rejected."""
        result = InputSanitizer.sanitize("   ")
        assert result is None
    
    def test_sanitize_rejects_too_long(self):
        """Test that strings exceeding max length are rejected."""
        long_text = "A" * (InputSanitizer.MAX_INPUT_LENGTH + 1)
        result = InputSanitizer.sanitize(long_text)
        assert result is None
    
    def test_sanitize_accepts_max_length(self):
        """Test that strings at max length are accepted."""
        max_text = "A" * InputSanitizer.MAX_INPUT_LENGTH
        result = InputSanitizer.sanitize(max_text)
        assert result == max_text
    
    def test_sanitize_rejects_sql_select(self):
        """Test that SQL SELECT statements are rejected."""
        result = InputSanitizer.sanitize("'; SELECT * FROM device_category; --")
        assert result is None
    
    def test_sanitize_rejects_sql_drop(self):
        """Test that SQL DROP statements are rejected."""
        result = InputSanitizer.sanitize("'; DROP TABLE device_category; --")
        assert result is None
    
    def test_sanitize_rejects_sql_insert(self):
        """Test that SQL INSERT statements are rejected."""
        result = InputSanitizer.sanitize("'; INSERT INTO device_category VALUES ('test'); --")
        assert result is None
    
    def test_sanitize_rejects_sql_update(self):
        """Test that SQL UPDATE statements are rejected."""
        result = InputSanitizer.sanitize("'; UPDATE device_category SET name='hacked'; --")
        assert result is None
    
    def test_sanitize_rejects_sql_delete(self):
        """Test that SQL DELETE statements are rejected."""
        result = InputSanitizer.sanitize("'; DELETE FROM device_category; --")
        assert result is None
    
    def test_sanitize_rejects_sql_union(self):
        """Test that SQL UNION attacks are rejected."""
        result = InputSanitizer.sanitize("' UNION SELECT password FROM users --")
        assert result is None
    
    def test_sanitize_rejects_sql_or_equals(self):
        """Test that SQL OR equals attacks are rejected."""
        result = InputSanitizer.sanitize("1' OR '1'='1")
        assert result is None
    
    def test_sanitize_rejects_sql_comment(self):
        """Test that SQL comment syntax is rejected."""
        result = InputSanitizer.sanitize("test -- comment")
        assert result is None
    
    def test_sanitize_rejects_sql_multiline_comment(self):
        """Test that SQL multiline comment syntax is rejected."""
        result = InputSanitizer.sanitize("test /* comment */")
        assert result is None
    
    def test_sanitize_rejects_semicolon(self):
        """Test that semicolons are rejected."""
        result = InputSanitizer.sanitize("test; DROP TABLE")
        assert result is None
    
    def test_sanitize_rejects_special_chars(self):
        """Test that special characters like quotes are rejected."""
        result = InputSanitizer.sanitize("test'value")
        assert result is None
    
    def test_sanitize_rejects_backticks(self):
        """Test that backticks are rejected."""
        result = InputSanitizer.sanitize("test`value")
        assert result is None
    
    def test_sanitize_rejects_angle_brackets(self):
        """Test that angle brackets are rejected."""
        result = InputSanitizer.sanitize("test<script>")
        assert result is None
    
    def test_is_valid_returns_true_for_valid(self):
        """Test that is_valid returns True for valid input."""
        assert InputSanitizer.is_valid("iPhone 14 Pro") is True
    
    def test_is_valid_returns_false_for_invalid(self):
        """Test that is_valid returns False for invalid input."""
        assert InputSanitizer.is_valid("'; DROP TABLE") is False
    
    def test_sanitize_accepts_unicode(self):
        """Test that Unicode characters are accepted."""
        result = InputSanitizer.sanitize("Téléphone")
        assert result == "Téléphone"
    
    def test_sanitize_accepts_comma(self):
        """Test that commas are accepted."""
        result = InputSanitizer.sanitize("Phone, Tablet")
        assert result == "Phone, Tablet"
    
    def test_sanitize_accepts_period(self):
        """Test that periods are accepted."""
        result = InputSanitizer.sanitize("Model 3.0")
        assert result == "Model 3.0"
    
    def test_sanitize_accepts_plus(self):
        """Test that plus signs are accepted."""
        result = InputSanitizer.sanitize("iPhone 14 Plus")
        assert result == "iPhone 14 Plus"
    
    def test_sanitize_rejects_non_string(self):
        """Test that non-string types are rejected."""
        result = InputSanitizer.sanitize(12345)
        assert result is None


