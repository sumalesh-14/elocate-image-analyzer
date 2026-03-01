"""
Logging utility for the Image Device Identification Service.
Provides structured JSON logging for production and human-readable logs for development.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from app.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging in production.
    Outputs log records as JSON objects with timestamp, level, message, and extra fields.
    """
    
    # Sensitive field names to exclude from logs
    SENSITIVE_FIELDS = {
        'api_key', 'apikey', 'api-key',
        'token', 'access_token', 'refresh_token',
        'password', 'passwd', 'pwd',
        'secret', 'api_secret',
        'authorization', 'auth',
        'gemini_api_key', 'gemini-api-key'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        if hasattr(record, 'extra_data'):
            extra_data = self._sanitize_sensitive_data(record.extra_data)
            log_data.update(extra_data)
        
        return json.dumps(log_data)
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove or mask sensitive data from log fields.
        
        Args:
            data: Dictionary of extra log data
            
        Returns:
            Sanitized dictionary with sensitive fields masked
        """
        sanitized = {}
        for key, value in data.items():
            # Check if field name indicates sensitive data
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized


class DevelopmentFormatter(logging.Formatter):
    """
    Human-readable formatter for development environments.
    Provides colored output and clear formatting for debugging.
    """
    
    # ANSI color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with colors and human-readable structure.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string with colors
        """
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{level_color}{record.levelname}{self.RESET}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build log message
        log_message = f"{timestamp} | {record.levelname:20s} | {record.name} | {record.getMessage()}"
        
        # Add extra data if present
        if hasattr(record, 'extra_data'):
            extra_str = " | " + " | ".join(f"{k}={v}" for k, v in record.extra_data.items())
            log_message += extra_str
        
        # Add exception info if present
        if record.exc_info:
            log_message += "\n" + self.formatException(record.exc_info)
        
        return log_message


def setup_logger(name: str = "image_analyzer") -> logging.Logger:
    """
    Configure and return a logger instance with appropriate formatting.
    
    Uses JSON formatting for production (LOG_LEVEL=INFO or higher) and
    human-readable formatting for development (LOG_LEVEL=DEBUG).
    
    Args:
        name: Name of the logger (default: "image_analyzer")
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Set log level from environment variable
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Choose formatter based on log level (DEBUG = development, others = production)
    if log_level == logging.DEBUG:
        formatter = DevelopmentFormatter()
    else:
        formatter = JSONFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs) -> None:
    """
    Log a message with additional context data.
    
    This helper function makes it easy to add structured data to log messages
    while ensuring sensitive data is filtered out.
    
    Args:
        logger: Logger instance to use
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        **kwargs: Additional context data to include in the log
        
    Example:
        log_with_context(logger, "INFO", "Image analysis complete",
                        filename="device.jpg", confidence=0.87, processing_time_ms=3456)
    """
    log_method = getattr(logger, level.lower())
    
    # Create a log record with extra data
    extra = {'extra_data': kwargs}
    log_method(message, extra=extra)


def configure_logging() -> None:
    """
    Configure logging for the application.
    
    This function should be called once at application startup to set up
    the logging system with appropriate formatters and handlers.
    """
    # Set up the root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Set log level from environment variable
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Choose formatter based on log level
    if log_level == logging.DEBUG:
        formatter = DevelopmentFormatter()
    else:
        formatter = JSONFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


# Create default logger instance
logger = setup_logger()


# Convenience functions for common logging patterns
def log_request(filename: str, file_size: int, content_type: str, ip_address: str = None) -> None:
    """Log an incoming image analysis request."""
    log_with_context(
        logger, "INFO", "Image analysis request received",
        filename=filename,
        file_size_bytes=file_size,
        content_type=content_type,
        ip_address=ip_address or "unknown"
    )


def log_analysis_complete(category: str, brand: str, model: str, 
                         confidence: float, processing_time_ms: int) -> None:
    """Log successful completion of image analysis."""
    log_with_context(
        logger, "INFO", "Image analysis completed successfully",
        category=category,
        brand=brand or "null",
        model=model or "null",
        confidence_score=confidence,
        processing_time_ms=processing_time_ms
    )


def log_analysis_error(error_code: str, error_message: str, 
                      filename: str = None, processing_time_ms: int = None) -> None:
    """Log an error during image analysis."""
    log_with_context(
        logger, "ERROR", "Image analysis failed",
        error_code=error_code,
        error_message=error_message,
        filename=filename or "unknown",
        processing_time_ms=processing_time_ms or 0
    )


def log_validation_error(error_code: str, filename: str, file_size: int = None) -> None:
    """Log a file validation error."""
    log_with_context(
        logger, "WARNING", "File validation failed",
        error_code=error_code,
        filename=filename,
        file_size_bytes=file_size or 0
    )


def log_gemini_api_call(processing_time_ms: int, success: bool, error: str = None) -> None:
    """Log a Gemini API call with timing and status."""
    level = "INFO" if success else "ERROR"
    message = "Gemini API call completed" if success else "Gemini API call failed"
    
    context = {
        "gemini_api_latency_ms": processing_time_ms,
        "success": success
    }
    
    if error:
        context["error"] = error
    
    log_with_context(logger, level, message, **context)


def log_performance_metric(metric_name: str, value: float, unit: str = None) -> None:
    """Log a performance metric."""
    context = {
        "metric_name": metric_name,
        "metric_value": value
    }
    
    if unit:
        context["unit"] = unit
    
    log_with_context(logger, "INFO", "Performance metric recorded", **context)
