"""
FastAPI application entry point for the Image Device Identification Service.

This module initializes the FastAPI application, configures middleware,
registers routes, and sets up exception handlers.
"""

import logging
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api.routes import router
from app.api.middleware import configure_middleware
from app.utils.logger import configure_logging
from app.models.response import ErrorData
from google import genai


# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title="Image Device Identification API",
    description="Analyze device images using Gemini Vision API to extract structured device information",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Configure middleware (CORS, authentication, rate limiting, logging)
configure_middleware(app)


# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Static files mounted from {static_dir}")


# Register routes
app.include_router(router)


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions and return standardized error responses.
    
    Args:
        request: The incoming request
        exc: The HTTP exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "timestamp": None,
            "processingTimeMs": 0,
            "data": None,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors and return standardized error responses.
    
    Args:
        request: The incoming request
        exc: The validation error
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(
        "Request validation error",
        extra={
            "errors": exc.errors(),
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "timestamp": None,
            "processingTimeMs": 0,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Request validation failed: {exc.errors()}"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions and return standardized error responses.
    
    Args:
        request: The incoming request
        exc: The exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.error(
        "Unexpected exception",
        extra={
            "error": str(exc),
            "path": request.url.path
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "timestamp": None,
            "processingTimeMs": 0,
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )


@app.on_event("startup")
async def startup_event():
    """
    Validate configuration and dependencies on startup.
    
    Validates:
    - Required environment variables are set
    - Gemini API key is valid and API is accessible
    - Configuration values are valid
    - Database connectivity (optional - service continues if unavailable)
    """
    logger.info("Starting Image Device Identification Service")
    
    # Validate Gemini API key is set
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY environment variable is not set")
        raise ValueError("GEMINI_API_KEY is required")
    
    # Validate API key is set
    if not settings.API_KEY:
        logger.error("API_KEY environment variable is not set")
        raise ValueError("API_KEY is required")
    
    # Initialize database connection pool
    try:
        from app.services.db_connection import db_manager
        await db_manager.initialize()
        
        if db_manager.is_available():
            logger.info("Database connection pool initialized and ready")
        else:
            logger.warning("Database is not available - service will operate without database matching")
    except Exception as e:
        logger.error(
            f"Error initializing database connection: {str(e)}",
            extra={"error": str(e)}
        )
        logger.warning("Service will continue without database matching")
    
    # Validate Gemini API connectivity
    try:
        from app.services.gemini_service import gemini_service
        is_available = await gemini_service.check_availability()
        
        if is_available:
            logger.info("Gemini API connectivity verified")
        else:
            logger.warning("Gemini API is not accessible - service will start but may fail on requests")
    except Exception as e:
        logger.warning(
            f"Could not verify Gemini API connectivity: {str(e)}",
            extra={"error": str(e)}
        )
    
    logger.info(
        "Service started successfully",
        extra={
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "allowed_origins": settings.allowed_origins_list,
            "rate_limit": settings.RATE_LIMIT,
            "log_level": settings.LOG_LEVEL
        }
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Image Device Identification Service")
    
    # Close database connection pool
    try:
        from app.services.db_connection import db_manager
        await db_manager.close()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database connection pool: {e}")


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with service information."""
    return JSONResponse(
        content={
            "service": "Image Device Identification API",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "analyze": "/api/v1/analyze",
                "health": "/health",
                "test": "/test",
                "test_interface": "/test-ui",
                "docs": "/docs"
            }
        }
    )


# Test UI endpoint
@app.get("/test-ui", response_class=HTMLResponse, include_in_schema=False)
async def test_ui():
    """Serve the test interface HTML."""
    html_file = Path(__file__).parent.parent / "static" / "test_interface.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    else:
        return HTMLResponse(content="<h1>Test interface not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (Railway, Render, etc.) or default to 8000
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
