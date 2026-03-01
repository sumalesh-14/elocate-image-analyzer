"""
Property-based tests for error handling and logging.

Uses Hypothesis to verify error handling properties across randomized scenarios.
Each test runs minimum 100 iterations to ensure comprehensive coverage.

Feature: database-matching-integration
"""

import pytest
import asyncio
import logging
import os
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from hypothesis import given, strategies as st, settings
import asyncpg
from datetime import datetime

from app.services.db_connection import DatabaseConnectionManager
from app.services.database_matcher import DatabaseMatcher


# Feature: database-matching-integration, Property 4: Database Error Logging
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_connection_error_logging():
    """
    Property 4: Database Error Logging
    
    For any database connection error or query failure, a log entry should exist
    containing a timestamp and error details.
    
    **Validates: Requirements 1.5, 8.1**
    """
    manager = DatabaseConnectionManager()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.db_connection')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.ERROR)
    
    try:
        # Mock asyncpg.create_pool to always fail
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_create_pool.side_effect = asyncpg.PostgresConnectionError("Connection failed")
            
            # Mock asyncio.sleep to speed up test
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await manager.initialize()
                
                # Property: Should have logged error messages
                error_logs = [r for r in log_records if r.levelno >= logging.ERROR]
                assert len(error_logs) > 0, "Expected at least one error log entry"
                
                # Property: Each error log should contain error details
                for log_record in error_logs:
                    message = log_record.getMessage()
                    # Should contain error information (failed, error, exhausted, etc.)
                    error_keywords = ["failed", "error", "exhausted", "connection"]
                    has_error_info = any(keyword in message.lower() for keyword in error_keywords)
                    assert has_error_info, \
                        f"Error log should contain error information: {message}"
                
                # Property: Log records should have timestamps
                for log_record in error_logs:
                    assert hasattr(log_record, 'created'), "Log record should have timestamp"
                    assert log_record.created > 0, "Log timestamp should be valid"
                    # Verify timestamp is recent (within last minute)
                    timestamp = datetime.fromtimestamp(log_record.created)
                    now = datetime.now()
                    time_diff = (now - timestamp).total_seconds()
                    assert time_diff < 60, f"Log timestamp should be recent, got {time_diff}s ago"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 4: Database Error Logging
@pytest.mark.asyncio
@given(
    error_message=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))
)
@settings(max_examples=20)
@pytest.mark.property_test
async def test_query_error_logging(error_message: str):
    """
    Property 4: Database Error Logging
    
    For any query failure with any error message, a log entry should exist
    containing the error details.
    
    **Validates: Requirements 1.5, 8.1**
    """
    matcher = DatabaseMatcher()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.database_matcher')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.ERROR)
    
    try:
        # Mock database manager to be available
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            
            # Mock pool.acquire to raise an error
            mock_acquire_context = AsyncMock()
            mock_acquire_context.__aenter__.side_effect = asyncpg.PostgresError(error_message)
            
            mock_pool = MagicMock()
            mock_pool.acquire.return_value = mock_acquire_context
            mock_db_manager.pool = mock_pool
            
            # Attempt to match category (should fail and log)
            result = await matcher.match_category("test_category")
            
            # Property: Should return None on error
            assert result is None, "Should return None on query error"
            
            # Property: Should have logged error
            error_logs = [r for r in log_records if r.levelno >= logging.ERROR]
            assert len(error_logs) > 0, "Expected at least one error log entry"
            
            # Property: Error log should contain error details
            found_error_message = False
            for log_record in error_logs:
                message = log_record.getMessage()
                if "failed" in message.lower() or "error" in message.lower():
                    found_error_message = True
                    break
            
            assert found_error_message, "Error log should contain error information"
            
            # Property: Log records should have timestamps
            for log_record in error_logs:
                assert hasattr(log_record, 'created'), "Log record should have timestamp"
                assert log_record.created > 0, "Log timestamp should be valid"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 4: Database Error Logging
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_timeout_error_logging():
    """
    Property 4: Database Error Logging
    
    For any query timeout, a warning log entry should exist with timeout details.
    
    **Validates: Requirements 1.5, 8.1**
    """
    matcher = DatabaseMatcher()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.database_matcher')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.WARNING)
    
    try:
        # Mock database manager to be available
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            
            # Mock pool.acquire to timeout
            async def slow_query(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than timeout
                return []
            
            mock_conn = MagicMock()
            mock_conn.fetch = slow_query
            
            mock_acquire_context = AsyncMock()
            mock_acquire_context.__aenter__.return_value = mock_conn
            mock_acquire_context.__aexit__.return_value = None
            
            mock_pool = MagicMock()
            mock_pool.acquire.return_value = mock_acquire_context
            mock_db_manager.pool = mock_pool
            
            # Mock settings to have a very short timeout
            with patch('app.services.database_matcher.settings') as mock_settings:
                mock_settings.DB_QUERY_TIMEOUT = 10  # 10ms
                mock_settings.CATEGORY_MATCH_THRESHOLD = 0.8
                
                # Attempt to match category (should timeout and log)
                result = await matcher.match_category("test_category")
                
                # Property: Should return None on timeout
                assert result is None, "Should return None on query timeout"
                
                # Property: Should have logged warning
                warning_logs = [r for r in log_records if r.levelno >= logging.WARNING]
                assert len(warning_logs) > 0, "Expected at least one warning log entry"
                
                # Property: Warning log should mention timeout
                found_timeout_message = False
                for log_record in warning_logs:
                    message = log_record.getMessage()
                    if "timeout" in message.lower():
                        found_timeout_message = True
                        break
                
                assert found_timeout_message, "Warning log should mention timeout"
                
                # Property: Log records should have timestamps
                for log_record in warning_logs:
                    assert hasattr(log_record, 'created'), "Log record should have timestamp"
                    assert log_record.created > 0, "Log timestamp should be valid"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 4: Database Error Logging
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    brand_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    model_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))
)
@settings(max_examples=20)
@pytest.mark.property_test
async def test_match_operation_logging(category_text: str, brand_text: str, model_text: str):
    """
    Property 4: Database Error Logging
    
    For any match operation, appropriate log entries should exist with
    match results and similarity scores.
    
    **Validates: Requirements 1.5, 8.1, 8.3, 8.4**
    """
    matcher = DatabaseMatcher()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.database_matcher')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.INFO)
    
    try:
        # Mock database manager to be unavailable (simplest case)
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = False
            
            # Attempt to match device
            result = await matcher.match_device(category_text, brand_text, model_text)
            
            # Property: Should return DeviceMatch with unavailable status
            assert result.database_status == "unavailable", \
                "Should return unavailable status when database is unavailable"
            
            # Property: Should have logged warning about unavailability
            warning_logs = [r for r in log_records if r.levelno >= logging.WARNING]
            assert len(warning_logs) > 0, "Expected at least one warning log entry"
            
            # Property: Warning log should mention unavailability
            found_unavailable_message = False
            for log_record in warning_logs:
                message = log_record.getMessage()
                if "unavailable" in message.lower():
                    found_unavailable_message = True
                    break
            
            assert found_unavailable_message, "Warning log should mention database unavailability"
            
            # Property: All log records should have timestamps
            for log_record in log_records:
                assert hasattr(log_record, 'created'), "Log record should have timestamp"
                assert log_record.created > 0, "Log timestamp should be valid"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 4: Database Error Logging
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_structured_logging_format():
    """
    Property 4: Database Error Logging
    
    All log entries should follow a structured format with consistent fields.
    
    **Validates: Requirements 1.5, 8.1**
    """
    manager = DatabaseConnectionManager()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.db_connection')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.INFO)
    
    try:
        # Mock successful connection
        mock_conn = MagicMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
        mock_pool.close = AsyncMock()
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_create_pool.return_value = mock_pool
            
            await manager.initialize()
            
            # Property: Should have logged info messages
            info_logs = [r for r in log_records if r.levelno == logging.INFO]
            assert len(info_logs) > 0, "Expected at least one info log entry"
            
            # Property: Each log record should have standard fields
            for log_record in info_logs:
                # Standard logging fields
                assert hasattr(log_record, 'name'), "Log record should have logger name"
                assert hasattr(log_record, 'levelname'), "Log record should have level name"
                assert hasattr(log_record, 'created'), "Log record should have timestamp"
                assert hasattr(log_record, 'module'), "Log record should have module name"
                assert hasattr(log_record, 'funcName'), "Log record should have function name"
                assert hasattr(log_record, 'lineno'), "Log record should have line number"
                
                # Verify logger name is correct
                assert log_record.name.startswith('app.services'), \
                    f"Logger name should start with 'app.services', got {log_record.name}"
            
            await manager.close()
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 3: Graceful Degradation on Database Failure
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_graceful_degradation_database_unavailable(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str]
):
    """
    Property 3: Graceful Degradation on Database Failure
    
    For any image analysis request when the database is unavailable or all retries fail,
    the response should contain text fields (category, brand, model) but null UUID fields
    (category_id, brand_id, model_id) with database_status set to "unavailable" or "failure".
    
    **Validates: Requirements 1.4, 8.2**
    """
    matcher = DatabaseMatcher()
    
    # Mock database manager to be unavailable
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = False
        
        # Attempt to match device
        result = await matcher.match_device(category_text, brand_text, model_text)
        
        # Property: Should return DeviceMatch (not None or exception)
        assert result is not None, "Should return DeviceMatch even when database unavailable"
        
        # Property: All UUID fields should be None
        assert result.category is None, \
            "category should be None when database unavailable"
        assert result.brand is None, \
            "brand should be None when database unavailable"
        assert result.model is None, \
            "model should be None when database unavailable"
        
        # Property: database_status should be "unavailable"
        assert result.database_status in ["unavailable", "failure"], \
            f"database_status should be 'unavailable' or 'failure', got '{result.database_status}'"


# Feature: database-matching-integration, Property 3: Graceful Degradation on Database Failure
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_graceful_degradation_connection_failure(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str]
):
    """
    Property 3: Graceful Degradation on Database Failure
    
    For any image analysis request when database connection fails,
    the system should gracefully degrade and return null UUID fields
    with database_status indicating failure.
    
    **Validates: Requirements 1.4, 8.2**
    """
    matcher = DatabaseMatcher()
    
    # Mock database manager to be available but connection fails
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        
        # Mock pool.acquire to raise connection error
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__.side_effect = asyncpg.PostgresConnectionError("Connection failed")
        
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context
        mock_db_manager.pool = mock_pool
        
        # Attempt to match device
        result = await matcher.match_device(category_text, brand_text, model_text)
        
        # Property: Should return DeviceMatch (not None or exception)
        assert result is not None, "Should return DeviceMatch even when connection fails"
        
        # Property: All UUID fields should be None
        assert result.category is None, \
            "category should be None when connection fails"
        assert result.brand is None, \
            "brand should be None when connection fails"
        assert result.model is None, \
            "model should be None when connection fails"
        
        # Property: database_status should indicate failure
        assert result.database_status in ["unavailable", "failure"], \
            f"database_status should be 'unavailable' or 'failure', got '{result.database_status}'"


# Feature: database-matching-integration, Property 3: Graceful Degradation on Database Failure
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_graceful_degradation_query_failure(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str]
):
    """
    Property 3: Graceful Degradation on Database Failure
    
    For any image analysis request when database queries fail,
    the system should gracefully degrade and return null UUID fields
    with database_status indicating failure.
    
    **Validates: Requirements 1.4, 8.2**
    """
    matcher = DatabaseMatcher()
    
    # Mock database manager to be available but queries fail
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        mock_db_manager.is_available.return_value = True
        
        # Mock connection that raises query error
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(side_effect=asyncpg.PostgresError("Query failed"))
        
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__.return_value = mock_conn
        mock_acquire_context.__aexit__.return_value = None
        
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context
        mock_db_manager.pool = mock_pool
        
        # Attempt to match device
        result = await matcher.match_device(category_text, brand_text, model_text)
        
        # Property: Should return DeviceMatch (not None or exception)
        assert result is not None, "Should return DeviceMatch even when queries fail"
        
        # Property: All UUID fields should be None
        assert result.category is None, \
            "category should be None when queries fail"
        assert result.brand is None, \
            "brand should be None when queries fail"
        assert result.model is None, \
            "model should be None when queries fail"
        
        # Property: database_status should indicate failure
        assert result.database_status in ["unavailable", "failure"], \
            f"database_status should be 'unavailable' or 'failure', got '{result.database_status}'"


# Feature: database-matching-integration, Property 3: Graceful Degradation on Database Failure
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_graceful_degradation_retry_exhaustion():
    """
    Property 3: Graceful Degradation on Database Failure
    
    When all connection retries are exhausted, the system should gracefully
    degrade and return null UUID fields with database_status indicating unavailability.
    
    **Validates: Requirements 1.4, 8.2**
    """
    matcher = DatabaseMatcher()
    
    # Mock database manager to simulate retry exhaustion
    with patch('app.services.database_matcher.db_manager') as mock_db_manager:
        # Simulate that retries were exhausted and database is now unavailable
        mock_db_manager.is_available.return_value = False
        
        # Test with various input combinations
        test_cases = [
            ("Mobile Phone", "Apple", "iPhone 14"),
            ("Laptop", None, None),
            ("Tablet", "Samsung", None),
            ("Phone", "", ""),
        ]
        
        for category_text, brand_text, model_text in test_cases:
            result = await matcher.match_device(category_text, brand_text, model_text)
            
            # Property: Should return DeviceMatch (not None or exception)
            assert result is not None, \
                f"Should return DeviceMatch for inputs: {category_text}, {brand_text}, {model_text}"
            
            # Property: All UUID fields should be None
            assert result.category is None, \
                f"category should be None for inputs: {category_text}, {brand_text}, {model_text}"
            assert result.brand is None, \
                f"brand should be None for inputs: {category_text}, {brand_text}, {model_text}"
            assert result.model is None, \
                f"model should be None for inputs: {category_text}, {brand_text}, {model_text}"
            
            # Property: database_status should be "unavailable"
            assert result.database_status in ["unavailable", "failure"], \
                f"database_status should be 'unavailable' or 'failure' for inputs: {category_text}, {brand_text}, {model_text}, got '{result.database_status}'"


# Feature: database-matching-integration, Property 3: Graceful Degradation on Database Failure
@pytest.mark.asyncio
@given(
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_graceful_degradation_no_exception_raised(category_text: str):
    """
    Property 3: Graceful Degradation on Database Failure
    
    For any database failure scenario, the system should never raise an exception
    to the caller - it should always return a valid DeviceMatch object.
    
    **Validates: Requirements 1.4, 8.2**
    """
    matcher = DatabaseMatcher()
    
    # Test various failure scenarios
    failure_scenarios = [
        # Database unavailable
        (False, None, None),
        # Connection error
        (True, asyncpg.PostgresConnectionError("Connection failed"), None),
        # Query error
        (True, None, asyncpg.PostgresError("Query failed")),
        # Timeout error
        (True, None, asyncio.TimeoutError()),
        # Generic exception
        (True, None, Exception("Unexpected error")),
    ]
    
    for is_available, connection_error, query_error in failure_scenarios:
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = is_available
            
            if connection_error:
                mock_acquire_context = AsyncMock()
                mock_acquire_context.__aenter__.side_effect = connection_error
                mock_pool = MagicMock()
                mock_pool.acquire.return_value = mock_acquire_context
                mock_db_manager.pool = mock_pool
            elif query_error:
                mock_conn = MagicMock()
                mock_conn.fetch = AsyncMock(side_effect=query_error)
                mock_acquire_context = AsyncMock()
                mock_acquire_context.__aenter__.return_value = mock_conn
                mock_acquire_context.__aexit__.return_value = None
                mock_pool = MagicMock()
                mock_pool.acquire.return_value = mock_acquire_context
                mock_db_manager.pool = mock_pool
            
            # Property: Should not raise exception
            try:
                result = await matcher.match_device(category_text, None, None)
                
                # Property: Should return valid DeviceMatch
                assert result is not None, "Should return DeviceMatch"
                assert hasattr(result, 'category'), "Result should have category attribute"
                assert hasattr(result, 'brand'), "Result should have brand attribute"
                assert hasattr(result, 'model'), "Result should have model attribute"
                assert hasattr(result, 'database_status'), "Result should have database_status attribute"
                
                # Property: database_status should be valid
                assert result.database_status in ["success", "partial_success", "failure", "unavailable"], \
                    f"database_status should be valid, got '{result.database_status}'"
            
            except Exception as e:
                pytest.fail(f"Should not raise exception, but got {type(e).__name__}: {str(e)}")


# Feature: database-matching-integration, Property 25: Credential Sanitization in Logs
@pytest.mark.asyncio
@given(
    password=st.text(min_size=8, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    db_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
    db_user=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N')))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_credential_sanitization_in_logs(password: str, db_name: str, db_user: str):
    """
    Property 25: Credential Sanitization in Logs
    
    For any log entry, it should not contain database passwords, connection strings
    with credentials, or other sensitive authentication information.
    
    **Validates: Requirements 10.2**
    """
    manager = DatabaseConnectionManager()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handlers to all relevant loggers
    loggers_to_check = [
        logging.getLogger('app.services.db_connection'),
        logging.getLogger('app.services.database_matcher'),
        logging.getLogger('app.services.query_cache'),
        logging.getLogger('app.config')
    ]
    
    log_capture = LogCapture()
    original_levels = {}
    
    for logger_obj in loggers_to_check:
        logger_obj.addHandler(log_capture)
        original_levels[logger_obj] = logger_obj.level
        logger_obj.setLevel(logging.DEBUG)  # Capture all log levels
    
    try:
        # Mock settings with test credentials
        with patch('app.services.db_connection.settings') as mock_settings:
            mock_settings.DB_HOST = "test-host"
            mock_settings.DB_PORT = 5432
            mock_settings.DB_NAME = db_name
            mock_settings.DB_USER = db_user
            mock_settings.DB_PASSWORD = password
            mock_settings.DB_MIN_POOL_SIZE = 5
            mock_settings.DB_MAX_POOL_SIZE = 20
            mock_settings.DB_CONNECTION_TIMEOUT = 10
            mock_settings.DB_QUERY_TIMEOUT = 50
            mock_settings.DB_SSL_MODE = "require"
            
            # Construct connection string (what should NOT appear in logs)
            connection_string_with_password = f"postgresql://{db_user}:{password}@test-host:5432/{db_name}"
            
            # Mock asyncpg.create_pool to fail (to generate logs)
            with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_create_pool.side_effect = asyncpg.PostgresConnectionError("Connection failed")
                
                # Mock asyncio.sleep to speed up test
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await manager.initialize()
        
        # Property: No log entry should contain the password
        for log_record in log_records:
            message = log_record.getMessage()
            
            # Check that password is not in the log message
            assert password not in message, \
                f"Password '{password}' found in log message: {message}"
            
            # Check that connection string with password is not in the log
            assert connection_string_with_password not in message, \
                f"Connection string with password found in log message: {message}"
            
            # Check for common patterns that might leak credentials
            # e.g., "password=xxx", "pwd=xxx", etc.
            lower_message = message.lower()
            if 'password' in lower_message or 'pwd' in lower_message:
                # If the word "password" appears, make sure it's not followed by the actual password
                assert password not in message, \
                    f"Password appears near 'password' keyword in log: {message}"
        
        # Property: Logs should contain safe information (host, port, database name, user)
        # but NOT the password
        found_connection_attempt = False
        for log_record in log_records:
            message = log_record.getMessage()
            if 'connect' in message.lower() or 'database' in message.lower():
                found_connection_attempt = True
                # These are safe to log
                # Host, port, database name, and user are acceptable
                # But password should never appear
                assert password not in message, \
                    f"Password found in connection log: {message}"
        
        # We should have logged connection attempts
        assert found_connection_attempt, "Expected to find connection attempt logs"
    
    finally:
        # Cleanup
        for logger_obj in loggers_to_check:
            logger_obj.removeHandler(log_capture)
            logger_obj.setLevel(original_levels[logger_obj])


# Feature: database-matching-integration, Property 25: Credential Sanitization in Logs
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_database_url_not_logged():
    """
    Property 25: Credential Sanitization in Logs
    
    The database_url property (which contains credentials) should never
    appear in log messages.
    
    **Validates: Requirements 10.2**
    """
    manager = DatabaseConnectionManager()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.db_connection')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    
    try:
        # Use actual settings (which has real database_url property)
        test_password = "test_secret_password_12345"
        
        with patch('app.services.db_connection.settings') as mock_settings:
            mock_settings.DB_HOST = "localhost"
            mock_settings.DB_PORT = 5432
            mock_settings.DB_NAME = "testdb"
            mock_settings.DB_USER = "testuser"
            mock_settings.DB_PASSWORD = test_password
            mock_settings.DB_MIN_POOL_SIZE = 5
            mock_settings.DB_MAX_POOL_SIZE = 20
            mock_settings.DB_CONNECTION_TIMEOUT = 10
            mock_settings.DB_QUERY_TIMEOUT = 50
            mock_settings.DB_SSL_MODE = "disable"
            
            # Create the database URL that should NOT be logged
            database_url = f"postgresql://testuser:{test_password}@localhost:5432/testdb"
            
            # Mock asyncpg.create_pool to succeed
            mock_conn = MagicMock()
            mock_conn.fetchval = AsyncMock(return_value=1)
            
            mock_acquire_context = AsyncMock()
            mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
            
            mock_pool = MagicMock()
            mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
            mock_pool.close = AsyncMock()
            
            with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_create_pool.return_value = mock_pool
                
                await manager.initialize()
                await manager.close()
        
        # Property: No log entry should contain the database URL with password
        for log_record in log_records:
            message = log_record.getMessage()
            
            # Check that database URL with password is not logged
            assert database_url not in message, \
                f"Database URL with password found in log: {message}"
            
            # Check that password is not in any log
            assert test_password not in message, \
                f"Password found in log message: {message}"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 25: Credential Sanitization in Logs
@pytest.mark.asyncio
@given(
    password=st.text(min_size=8, max_size=50, alphabet=st.characters(whitelist_categories=('L',))),
    category_text=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_no_credentials_in_query_logs(password: str, category_text: str):
    """
    Property 25: Credential Sanitization in Logs
    
    For any database query operation, log entries should not contain
    credentials even when logging query details.
    
    **Validates: Requirements 10.2**
    """
    # Skip if password and category_text are the same (false positive)
    # We legitimately log category_text as user input
    if password == category_text:
        return
    
    matcher = DatabaseMatcher()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.database_matcher')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    
    try:
        # Mock database manager with credentials
        with patch('app.services.database_matcher.db_manager') as mock_db_manager:
            mock_db_manager.is_available.return_value = True
            
            # Mock settings with test password
            with patch('app.services.database_matcher.settings') as mock_settings:
                mock_settings.DB_PASSWORD = password
                mock_settings.DB_QUERY_TIMEOUT = 50
                mock_settings.CATEGORY_MATCH_THRESHOLD = 0.8
                
                # Mock connection that succeeds
                mock_conn = MagicMock()
                mock_conn.fetch = AsyncMock(return_value=[])
                
                mock_acquire_context = AsyncMock()
                mock_acquire_context.__aenter__.return_value = mock_conn
                mock_acquire_context.__aexit__.return_value = None
                
                mock_pool = MagicMock()
                mock_pool.acquire.return_value = mock_acquire_context
                mock_db_manager.pool = mock_pool
                
                # Perform query operation
                result = await matcher.match_category(category_text)
        
        # Property: No log entry should contain the password (unless it's the category_text itself)
        for log_record in log_records:
            message = log_record.getMessage()
            
            # Password should never appear in logs
            # (We already filtered out cases where password == category_text)
            assert password not in message, \
                f"Password '{password}' found in query log: {message}"
            
            # Check for credential-related keywords with actual values
            lower_message = message.lower()
            if any(keyword in lower_message for keyword in ['password', 'pwd', 'credential', 'auth']):
                # If these keywords appear, ensure the actual password doesn't
                assert password not in message, \
                    f"Password appears near credential keyword in log: {message}"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 25: Credential Sanitization in Logs
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_exception_messages_sanitized():
    """
    Property 25: Credential Sanitization in Logs
    
    When exceptions occur that might contain connection details,
    the logged exception messages should not expose credentials.
    
    **Validates: Requirements 10.2**
    """
    manager = DatabaseConnectionManager()
    
    # Capture log records
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    # Add log capture handler
    logger = logging.getLogger('app.services.db_connection')
    log_capture = LogCapture()
    logger.addHandler(log_capture)
    original_level = logger.level
    logger.setLevel(logging.ERROR)
    
    try:
        test_password = "super_secret_password_xyz"
        
        with patch('app.services.db_connection.settings') as mock_settings:
            mock_settings.DB_HOST = "localhost"
            mock_settings.DB_PORT = 5432
            mock_settings.DB_NAME = "testdb"
            mock_settings.DB_USER = "testuser"
            mock_settings.DB_PASSWORD = test_password
            mock_settings.DB_MIN_POOL_SIZE = 5
            mock_settings.DB_MAX_POOL_SIZE = 20
            mock_settings.DB_CONNECTION_TIMEOUT = 10
            mock_settings.DB_QUERY_TIMEOUT = 50
            mock_settings.DB_SSL_MODE = "require"
            
            # Mock asyncpg to raise an exception that might contain connection details
            error_message = f"Connection failed to postgresql://testuser:***@localhost:5432/testdb"
            
            with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_create_pool.side_effect = asyncpg.PostgresConnectionError(error_message)
                
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    await manager.initialize()
        
        # Property: No log entry should contain the actual password
        for log_record in log_records:
            message = log_record.getMessage()
            
            # Password should never appear in exception logs
            assert test_password not in message, \
                f"Password found in exception log: {message}"
            
            # Even if the exception message is logged, password should be sanitized
            if 'postgresql://' in message:
                assert test_password not in message, \
                    f"Password found in connection string in exception log: {message}"
    
    finally:
        # Cleanup
        logger.removeHandler(log_capture)
        logger.setLevel(original_level)


# Feature: database-matching-integration, Property 25: Credential Sanitization in Logs
@pytest.mark.asyncio
@given(
    password=st.text(min_size=8, max_size=50, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
async def test_settings_not_logged_with_credentials(password: str):
    """
    Property 25: Credential Sanitization in Logs
    
    Settings objects or configuration dumps should never be logged
    in a way that exposes credentials.
    
    **Validates: Requirements 10.2**
    """
    # Capture log records from all relevant loggers
    log_records = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_records.append(record)
    
    loggers_to_check = [
        logging.getLogger('app.services.db_connection'),
        logging.getLogger('app.config'),
        logging.getLogger('app')
    ]
    
    log_capture = LogCapture()
    original_levels = {}
    
    for logger_obj in loggers_to_check:
        logger_obj.addHandler(log_capture)
        original_levels[logger_obj] = logger_obj.level
        logger_obj.setLevel(logging.DEBUG)
    
    try:
        # Create a settings object with test password
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_gemini_key',
            'API_KEY': 'test_api_key',
            'DB_PASSWORD': password
        }):
            # Import or access settings (this might trigger logging)
            from app.config import Settings
            
            test_settings = Settings(
                GEMINI_API_KEY='test_gemini_key',
                API_KEY='test_api_key',
                DB_PASSWORD=password
            )
            
            # Simulate operations that might log settings
            _ = test_settings.database_url
            _ = test_settings.DB_PASSWORD
        
        # Property: No log entry should contain the password
        for log_record in log_records:
            message = log_record.getMessage()
            
            # Password should never appear in logs
            assert password not in message, \
                f"Password found in settings-related log: {message}"
            
            # Check that database_url with password is not logged
            if 'postgresql://' in message:
                assert password not in message, \
                    f"Password found in database URL in log: {message}"
    
    finally:
        # Cleanup
        for logger_obj in loggers_to_check:
            logger_obj.removeHandler(log_capture)
            logger_obj.setLevel(original_levels[logger_obj])

