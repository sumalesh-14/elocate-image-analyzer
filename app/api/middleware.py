"""
API middleware for security, rate limiting, CORS, and logging.

This module implements:
- API key authentication
- Rate limiting using slowapi
- CORS configuration
- Request/response logging
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.models.response import ErrorData

# Configure logger
logger = logging.getLogger(__name__)


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key authentication.
    
    Checks for X-API-Key header in requests to /api/ endpoints.
    Returns 401 for missing or invalid API keys.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and validate API key for API endpoints."""
        # Skip authentication for health check and test interface
        if request.url.path in ["/health", "/test", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check API key for /api/ endpoints
        if request.url.path.startswith("/api/"):
            api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                logger.warning(
                    "Missing API key",
                    extra={
                        "path": request.url.path,
                        "ip": request.client.host if request.client else "unknown"
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "timestamp": time.time(),
                        "processingTimeMs": 0,
                        "data": None,
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Missing API key. Include X-API-Key header."
                        }
                    }
                )
            
            if api_key != settings.API_KEY:
                logger.warning(
                    "Invalid API key",
                    extra={
                        "path": request.url.path,
                        "ip": request.client.host if request.client else "unknown"
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "timestamp": time.time(),
                        "processingTimeMs": 0,
                        "data": None,
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Invalid API key"
                        }
                    }
                )
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses.
    
    Logs request details, response status, and processing time.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "processing_time_ms": processing_time
            }
        )
        
        return response


def configure_cors(app) -> None:
    """Configure CORS middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    logger.info(
        "CORS configured",
        extra={"allowed_origins": settings.allowed_origins_list}
    )


def configure_rate_limiting(app) -> None:
    """Configure rate limiting for the application.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    logger.info(
        "Rate limiting configured",
        extra={"rate_limit": settings.RATE_LIMIT}
    )


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors.
    
    Args:
        request: The incoming request
        exc: The rate limit exceeded exception
        
    Returns:
        JSONResponse with 429 status and retry-after header
    """
    logger.warning(
        "Rate limit exceeded",
        extra={
            "path": request.url.path,
            "ip": request.client.host if request.client else "unknown"
        }
    )
    
    # Extract retry-after from exception if available
    retry_after = 60  # Default to 60 seconds
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "timestamp": time.time(),
            "processingTimeMs": 0,
            "data": None,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Please try again in {retry_after} seconds."
            }
        },
        headers={"Retry-After": str(retry_after)}
    )


def configure_middleware(app) -> None:
    """Configure all middleware for the application.
    
    This function should be called during application startup to set up:
    - CORS
    - Rate limiting
    - API key authentication
    - Request/response logging
    
    Args:
        app: FastAPI application instance
    """
    # Configure CORS (must be first)
    configure_cors(app)
    
    # Configure rate limiting
    configure_rate_limiting(app)
    
    # Add custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(APIKeyAuthMiddleware)
    
    logger.info("All middleware configured successfully")
