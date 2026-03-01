"""
Unit tests for the logging utility.
Tests JSON formatting, sensitive data filtering, and log level configuration.
"""

import logging
import json
import pytest
from unittest.mock import patch
from app.utils.logger import (
    JSONFormatter,
    DevelopmentFormatter,
    setup_logger,
    log_with_context,
    log_request,
    log_analysis_complete,
    log_analysis_error,
    log_validation_error,
    log_gemini_api_call,
    log_performance_metric
)


class TestJSONFormatter:
    """Test the JSON formatter for structured logging."""
    
    def test_basic_formatting(self):
        """Test that basic log records are formatted as valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        log_data = json.loads(output)
        
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
    
    def test_sensitive_data_filtering(self):
        """Test that sensitive fields are redacted from logs."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add sensitive data
        record.extra_data = {
            "filename": "device.jpg",
            "api_key": "secret_key_12345",
            "confidence": 0.87,
            "gemini_api_key": "another_secret",
            "token": "bearer_token_xyz"
        }
        
        output = formatter.format(record)
        log_data = json.loads(output)
        
        # Non-sensitive data should be present
        assert log_data["filename"] == "device.jpg"
        assert log_data["confidence"] == 0.87
        
        # Sensitive data should be redacted
        assert log_data["api_key"] == "***REDACTED***"
        assert log_data["gemini_api_key"] == "***REDACTED***"
        assert log_data["token"] == "***REDACTED***"
    
    def test_exception_formatting(self):
        """Test that exceptions are included in JSON output."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        output = formatter.format(record)
        log_data = json.loads(output)
        
        assert "exception" in log_data
        assert "ValueError: Test exception" in log_data["exception"]


class TestDevelopmentFormatter:
    """Test the development formatter for human-readable logs."""
    
    def test_basic_formatting(self):
        """Test that development logs are human-readable."""
        formatter = DevelopmentFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        
        assert "INFO" in output
        assert "test_logger" in output
        assert "Test message" in output
    
    def test_extra_data_formatting(self):
        """Test that extra data is included in development logs."""
        formatter = DevelopmentFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        record.extra_data = {
            "filename": "device.jpg",
            "confidence": 0.87
        }
        
        output = formatter.format(record)
        
        assert "filename=device.jpg" in output
        assert "confidence=0.87" in output


class TestSetupLogger:
    """Test logger setup and configuration."""
    
    def test_logger_creation(self):
        """Test that setup_logger creates a configured logger."""
        logger = setup_logger("test_logger_1")
        
        assert logger.name == "test_logger_1"
        assert len(logger.handlers) > 0
        assert not logger.propagate
    
    def test_logger_reuse(self):
        """Test that calling setup_logger twice doesn't add duplicate handlers."""
        logger1 = setup_logger("test_logger_2")
        handler_count = len(logger1.handlers)
        
        logger2 = setup_logger("test_logger_2")
        
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count
    
    @patch('app.utils.logger.settings')
    def test_log_level_from_config(self, mock_settings):
        """Test that log level is set from configuration."""
        mock_settings.LOG_LEVEL = "DEBUG"
        
        logger = setup_logger("test_logger_3")
        
        assert logger.level == logging.DEBUG
    
    @patch('app.utils.logger.settings')
    def test_json_formatter_for_production(self, mock_settings):
        """Test that JSON formatter is used for production log levels."""
        mock_settings.LOG_LEVEL = "INFO"
        
        logger = setup_logger("test_logger_4")
        
        # Check that handler uses JSONFormatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)
    
    @patch('app.utils.logger.settings')
    def test_development_formatter_for_debug(self, mock_settings):
        """Test that development formatter is used for DEBUG level."""
        mock_settings.LOG_LEVEL = "DEBUG"
        
        logger = setup_logger("test_logger_5")
        
        # Check that handler uses DevelopmentFormatter
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, DevelopmentFormatter)


class TestLogWithContext:
    """Test the log_with_context helper function."""
    
    def test_log_with_context(self, capsys):
        """Test that log_with_context adds extra data to logs."""
        logger = setup_logger("test_logger_6")
        
        log_with_context(
            logger, "INFO", "Test message",
            filename="device.jpg",
            confidence=0.87
        )
        
        # Capture stdout output
        captured = capsys.readouterr()
        
        # Verify log was created and contains expected data
        assert "Test message" in captured.out
        assert "device.jpg" in captured.out
        assert "0.87" in captured.out


class TestConvenienceFunctions:
    """Test convenience logging functions."""
    
    def test_log_request(self):
        """Test log_request function executes without error."""
        # Should not raise any exceptions
        log_request(
            filename="device.jpg",
            file_size=1024000,
            content_type="image/jpeg",
            ip_address="192.168.1.1"
        )
    
    def test_log_analysis_complete(self):
        """Test log_analysis_complete function executes without error."""
        # Should not raise any exceptions
        log_analysis_complete(
            category="mobile",
            brand="Samsung",
            model="Galaxy S21",
            confidence=0.87,
            processing_time_ms=3456
        )
    
    def test_log_analysis_error(self):
        """Test log_analysis_error function executes without error."""
        # Should not raise any exceptions
        log_analysis_error(
            error_code="INVALID_FILE_TYPE",
            error_message="File is not a valid image",
            filename="test.txt"
        )
    
    def test_log_validation_error(self):
        """Test log_validation_error function executes without error."""
        # Should not raise any exceptions
        log_validation_error(
            error_code="INVALID_FILE_SIZE",
            filename="large_file.jpg",
            file_size=15000000
        )
    
    def test_log_gemini_api_call_success(self):
        """Test log_gemini_api_call for successful calls."""
        # Should not raise any exceptions
        log_gemini_api_call(
            processing_time_ms=2500,
            success=True
        )
    
    def test_log_gemini_api_call_failure(self):
        """Test log_gemini_api_call for failed calls."""
        # Should not raise any exceptions
        log_gemini_api_call(
            processing_time_ms=5000,
            success=False,
            error="API timeout"
        )
    
    def test_log_performance_metric(self):
        """Test log_performance_metric function executes without error."""
        # Should not raise any exceptions
        log_performance_metric(
            metric_name="image_processing_time",
            value=3456.78,
            unit="milliseconds"
        )

