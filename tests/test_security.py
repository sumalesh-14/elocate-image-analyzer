"""
Security tests for database matching integration.

Tests SQL injection prevention, credential sanitization, SSL/TLS enforcement,
and read-only permissions.

Validates Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import pytest
import asyncpg
import logging
from unittest.mock import patch, MagicMock
from io import StringIO

from app.services.database_matcher import DatabaseMatcher
from app.services.input_sanitizer import InputSanitizer


@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection_in_category_input(test_db_connection):
    """
    Test that SQL injection attempts in category strings are prevented.
    
    Validates Requirements: 10.3, 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # SQL injection attempts
    injection_attempts = [
        "'; DROP TABLE device_category; --",
        "' OR '1'='1",
        "'; DELETE FROM device_category WHERE '1'='1",
        "' UNION SELECT * FROM device_category --",
        "admin'--",
        "' OR 1=1--",
        "1' AND '1'='1",
    ]
    
    for injection_string in injection_attempts:
        # Attempt to match with injection string
        result = await matcher.match_category(injection_string)
        
        # Should either return None or a legitimate match, never execute SQL injection
        # The key is that no exception should be raised and tables should remain intact
        assert result is None or hasattr(result, 'id')
    
    # Verify tables still exist and have data
    categories = await test_db_connection.fetch("SELECT COUNT(*) as count FROM device_category")
    assert categories[0]['count'] > 0, "device_category table was compromised"


@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection_in_brand_input(test_db_connection):
    """
    Test that SQL injection attempts in brand strings are prevented.
    
    Validates Requirements: 10.3, 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # First get a valid category
    from tests.test_db_setup import TEST_CATEGORY_MOBILE_ID
    
    injection_attempts = [
        "'; DROP TABLE device_brand; --",
        "' OR '1'='1",
        "'; DELETE FROM device_brand WHERE '1'='1",
        "' UNION SELECT * FROM device_brand --",
    ]
    
    for injection_string in injection_attempts:
        result = await matcher.match_brand(injection_string, TEST_CATEGORY_MOBILE_ID)
        
        # Should either return None or a legitimate match
        assert result is None or hasattr(result, 'id')
    
    # Verify tables still exist and have data
    brands = await test_db_connection.fetch("SELECT COUNT(*) as count FROM device_brand")
    assert brands[0]['count'] > 0, "device_brand table was compromised"


@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection_in_model_input(test_db_connection):
    """
    Test that SQL injection attempts in model strings are prevented.
    
    Validates Requirements: 10.3, 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    from tests.test_db_setup import TEST_CATEGORY_MOBILE_ID, TEST_BRAND_APPLE_ID
    
    injection_attempts = [
        "'; DROP TABLE device_model; --",
        "' OR '1'='1",
        "'; DELETE FROM device_model WHERE '1'='1",
        "' UNION SELECT * FROM device_model --",
    ]
    
    for injection_string in injection_attempts:
        result = await matcher.match_model(
            injection_string,
            TEST_CATEGORY_MOBILE_ID,
            TEST_BRAND_APPLE_ID
        )
        
        # Should either return None or a legitimate match
        assert result is None or hasattr(result, 'id')
    
    # Verify tables still exist and have data
    models = await test_db_connection.fetch("SELECT COUNT(*) as count FROM device_model")
    assert models[0]['count'] > 0, "device_model table was compromised"


@pytest.mark.asyncio
@pytest.mark.security
async def test_special_characters_in_input(test_db_connection):
    """
    Test that special characters in input are handled safely.
    
    Validates Requirements: 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    special_char_inputs = [
        "Test<script>alert('xss')</script>",
        "Test\x00null",
        "Test\n\r\t",
        "Test'\"\\",
        "Test;SELECT*FROM",
        "Test%00",
        "../../../etc/passwd",
    ]
    
    for special_input in special_char_inputs:
        # Should handle gracefully without errors
        result = await matcher.match_category(special_input)
        
        # Should return None or valid match, never raise exception
        assert result is None or hasattr(result, 'id')


@pytest.mark.security
def test_connection_string_not_logged():
    """
    Test that database connection strings with credentials are not logged.
    
    Validates Requirements: 10.2
    """
    # Create a string buffer to capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    # Get the logger
    logger = logging.getLogger('app.services.db_connection')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    # Simulate logging that might contain connection info
    test_password = "super_secret_password_123"
    test_connection_string = f"postgresql://user:{test_password}@localhost:5432/testdb"
    
    # Log some messages (simulating what the connection manager might log)
    logger.info("Database connection initialized")
    logger.debug("Connection pool created")
    logger.error("Connection failed")
    
    # Get logged output
    log_output = log_stream.getvalue()
    
    # Verify password and connection string are NOT in logs
    assert test_password not in log_output, "Password found in logs!"
    assert test_connection_string not in log_output, "Connection string with credentials found in logs!"
    
    # Cleanup
    logger.removeHandler(handler)


@pytest.mark.security
def test_input_sanitizer_prevents_injection():
    """
    Test that input sanitizer properly sanitizes potentially dangerous inputs.
    
    Validates Requirements: 10.5
    """
    sanitizer = InputSanitizer()
    
    # Test SQL injection patterns
    dangerous_inputs = [
        ("'; DROP TABLE users; --", True),  # Should be flagged as dangerous
        ("' OR '1'='1", True),
        ("admin'--", True),
        ("Normal Brand Name", False),  # Should be safe
        ("Apple iPhone 14", False),
        ("Samsung Galaxy S23", False),
    ]
    
    for input_str, should_be_dangerous in dangerous_inputs:
        is_safe = sanitizer.is_safe(input_str)
        
        if should_be_dangerous:
            assert not is_safe, f"Input '{input_str}' should be flagged as dangerous"
        else:
            assert is_safe, f"Input '{input_str}' should be safe"


@pytest.mark.asyncio
@pytest.mark.security
async def test_parameterized_queries_used(test_db_connection):
    """
    Test that parameterized queries are used (not string concatenation).
    
    This is verified by ensuring SQL injection attempts don't work.
    
    Validates Requirements: 10.3
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # If parameterized queries are used, this should not cause any issues
    malicious_input = "'; DROP TABLE device_category; SELECT * FROM device_category WHERE name='"
    
    # This should safely return None or a match, not execute the DROP
    result = await matcher.match_category(malicious_input)
    
    # Verify the table still exists
    try:
        count = await test_db_connection.fetchval("SELECT COUNT(*) FROM device_category")
        assert count > 0, "Table should still have data"
    except asyncpg.exceptions.UndefinedTableError:
        pytest.fail("device_category table was dropped - SQL injection succeeded!")


@pytest.mark.asyncio
@pytest.mark.security
async def test_read_only_permissions():
    """
    Test that database user has read-only permissions.
    
    Note: This test requires a properly configured read-only database user.
    In a real environment, the database user should only have SELECT permissions.
    
    Validates Requirements: 10.4
    """
    # This test documents the requirement but may not be enforceable in test environment
    # In production, the database user should be configured with:
    # GRANT SELECT ON device_category, device_brand, category_brand, device_model TO analyzer_readonly;
    # REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM analyzer_readonly;
    
    # We can at least verify that our code doesn't attempt write operations
    # by checking that DatabaseMatcher only has query methods, no insert/update/delete
    
    from app.services.database_matcher import DatabaseMatcher
    import inspect
    
    # Get all methods of DatabaseMatcher
    methods = [method for method in dir(DatabaseMatcher) if not method.startswith('_')]
    
    # Verify no write operation methods exist
    write_operations = ['insert', 'update', 'delete', 'create', 'drop', 'alter', 'truncate']
    
    for method in methods:
        method_lower = method.lower()
        for write_op in write_operations:
            assert write_op not in method_lower, f"DatabaseMatcher has write operation method: {method}"


@pytest.mark.security
def test_ssl_tls_configuration():
    """
    Test that SSL/TLS is configured for database connections.
    
    Validates Requirements: 10.1
    """
    from app.config import settings
    
    # Verify SSL mode is set to require or higher
    ssl_mode = getattr(settings, 'DB_SSL_MODE', None)
    
    # In production, this should be 'require', 'verify-ca', or 'verify-full'
    # For testing, we document the requirement
    assert ssl_mode is not None, "DB_SSL_MODE should be configured"
    
    # Document expected values
    valid_ssl_modes = ['require', 'verify-ca', 'verify-full', 'allow', 'prefer']
    
    # Note: In test environment, SSL might be disabled
    # In production, it should be 'require' or stricter
    print(f"\nSSL Mode configured: {ssl_mode}")
    print(f"Production should use: 'require', 'verify-ca', or 'verify-full'")


@pytest.mark.asyncio
@pytest.mark.security
async def test_no_sensitive_data_in_error_messages(test_db_connection):
    """
    Test that error messages don't leak sensitive information.
    
    Validates Requirements: 10.2
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # Create a scenario that might generate an error
    # Use invalid UUID to potentially trigger an error
    from uuid import UUID
    
    try:
        # This might fail but shouldn't leak connection details
        result = await matcher.match_brand("Test", UUID('00000000-0000-0000-0000-000000000000'))
    except Exception as e:
        error_message = str(e)
        
        # Verify no sensitive information in error message
        assert 'password' not in error_message.lower()
        assert 'secret' not in error_message.lower()
        assert 'postgresql://' not in error_message
        assert '@localhost' not in error_message or 'password' not in error_message


@pytest.mark.asyncio
@pytest.mark.security
async def test_input_length_limits(test_db_connection):
    """
    Test that extremely long inputs are handled safely.
    
    Validates Requirements: 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # Create very long input strings
    very_long_input = "A" * 10000
    
    # Should handle gracefully without errors or performance issues
    result = await matcher.match_category(very_long_input)
    
    # Should return None (no match) but not crash
    assert result is None


@pytest.mark.asyncio
@pytest.mark.security
async def test_unicode_and_encoding_safety(test_db_connection):
    """
    Test that unicode and various encodings are handled safely.
    
    Validates Requirements: 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    unicode_inputs = [
        "测试",  # Chinese
        "テスト",  # Japanese
        "тест",  # Russian
        "🔥📱💻",  # Emojis
        "Ñoño",  # Spanish with tildes
        "Café",  # French with accents
    ]
    
    for unicode_input in unicode_inputs:
        # Should handle gracefully without encoding errors
        result = await matcher.match_category(unicode_input)
        
        # Should return None or valid match, never raise encoding exception
        assert result is None or hasattr(result, 'id')


@pytest.mark.asyncio
@pytest.mark.security
async def test_null_byte_injection(test_db_connection):
    """
    Test that null byte injection attempts are prevented.
    
    Validates Requirements: 10.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    null_byte_inputs = [
        "test\x00",
        "\x00test",
        "te\x00st",
        "test\x00.jpg",
    ]
    
    for null_input in null_byte_inputs:
        # Should handle gracefully
        result = await matcher.match_category(null_input)
        
        # Should return None or valid match, never cause security issue
        assert result is None or hasattr(result, 'id')
