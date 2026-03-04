"""
FastAPI routes and endpoints for the Image Device Identification API.

This module implements:
- POST /api/v1/analyze: Device image analysis endpoint
- GET /health: Health check endpoint
- GET /test: Test interface endpoint
"""

import time
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request
from fastapi.responses import HTMLResponse, FileResponse

from app.models.response import IdentificationResponse, ErrorData, HealthResponse, DeviceData
from app.models.material_analysis import (
    MaterialAnalysisRequest,
    MaterialAnalysisResponse,
    MaterialAnalysisData,
    BrandInfo,
    CategoryInfo,
    ModelInfo,
    AnalysisMetadata
)
from app.services.analyzer import analyzer_service, AnalysisError
from app.services.material_analyzer import material_analyzer_service, MaterialAnalysisError
from app.services.llm_router import llm_service
from app.api.middleware import limiter


# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/api/v1/analyze",
    response_model=IdentificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze device image",
    description="Upload a device image for identification and analysis"
)
@limiter.limit("10/minute")
async def analyze_device(
    request: Request,
    file: UploadFile = File(..., description="Device image file (JPEG, PNG, or WebP, max 10MB)")
) -> IdentificationResponse:
    """
    Analyze an uploaded device image and extract device information.
    
    Accepts multipart/form-data with an image file.
    Returns structured device identification data with confidence scores.
    
    Args:
        request: FastAPI request object (required for rate limiting)
        file: Uploaded image file
        
    Returns:
        IdentificationResponse with device data or error information
        
    Raises:
        HTTPException: For various error conditions (handled and returned as JSON)
    """
    start_time = time.time()
    
    try:
        # Check if file was provided
        if not file:
            processing_time = int((time.time() - start_time) * 1000)
            return IdentificationResponse(
                success=False,
                processingTimeMs=processing_time,
                error=ErrorData(
                    code="MISSING_FILE",
                    message="No image file provided"
                )
            )
        
        # Analyze the device
        device_data = await analyzer_service.analyze_device(file)
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Return success response
        return IdentificationResponse(
            success=True,
            processingTimeMs=processing_time,
            data=device_data
        )
        
    except AnalysisError as e:
        # Handle known analysis errors
        processing_time = int((time.time() - start_time) * 1000)
        
        # Map error codes to HTTP status codes
        status_code_map = {
            "INVALID_FILE_TYPE": status.HTTP_400_BAD_REQUEST,
            "INVALID_FILE_SIZE": status.HTTP_400_BAD_REQUEST,
            "INVALID_FILE_HEADERS": status.HTTP_400_BAD_REQUEST,
            "MALICIOUS_FILE": status.HTTP_400_BAD_REQUEST,
            "NOT_A_DEVICE": status.HTTP_400_BAD_REQUEST,
            "MISSING_FILE": status.HTTP_400_BAD_REQUEST,
            "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
            "ANALYSIS_TIMEOUT": status.HTTP_504_GATEWAY_TIMEOUT,
        }
        
        http_status = status_code_map.get(e.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.warning(
            f"Analysis error: {e.error_code}",
            extra={
                "error_code": e.error_code,
                "error_message": e.message,
                "processing_time_ms": processing_time
            }
        )
        
        return IdentificationResponse(
            success=False,
            processingTimeMs=processing_time,
            error=ErrorData(
                code=e.error_code,
                message=e.message
            )
        )
        
    except TimeoutError:
        # Handle timeout errors
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Analysis timeout",
            extra={"processing_time_ms": processing_time}
        )
        
        return IdentificationResponse(
            success=False,
            processingTimeMs=processing_time,
            error=ErrorData(
                code="ANALYSIS_TIMEOUT",
                message="Image analysis timed out. Please try again."
            )
        )
        
    except Exception as e:
        # Handle unexpected errors
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Unexpected error during analysis",
            extra={
                "error": str(e),
                "processing_time_ms": processing_time
            },
            exc_info=True
        )
        
        return IdentificationResponse(
            success=False,
            processingTimeMs=processing_time,
            error=ErrorData(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred during analysis"
            )
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check service health and Gemini API availability"
)
async def health_check() -> HealthResponse:
    """
    Check the health status of the service and its dependencies.
    
    Returns:
        HealthResponse with service status and Gemini API availability
    """
    try:
        llm_available = await llm_service.check_availability()
        
        # Check database availability
        from app.services.db_connection import db_manager
        database_available = await db_manager.health_check()
        
        # Determine overall status
        if llm_available and database_available:
            service_status = "healthy"
        elif llm_available or database_available:
            service_status = "degraded"
        else:
            service_status = "unhealthy"
        
        logger.info(
            "Health check performed",
            extra={
                "status": service_status,
                "gemini_available": llm_available,
                "database_available": database_available
            }
        )
        
        return HealthResponse(
            status=service_status,
            gemini_api_available=llm_available,
            database_available=database_available
        )
        
    except Exception as e:
        logger.error(
            "Health check failed",
            extra={"error": str(e)},
            exc_info=True
        )
        
        return HealthResponse(
            status="unhealthy",
            gemini_api_available=False,
            database_available=False
        )


@router.get(
    "/test",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="Test interface",
    description="Serve static HTML test interface for manual testing"
)
async def test_interface() -> HTMLResponse:
    """
    Serve the static HTML test interface.
    
    Returns:
        HTML content of the test interface
    """
    try:
        # Path to static test interface
        static_path = Path(__file__).parent.parent.parent / "static" / "test_interface.html"
        
        # Check if file exists
        if not static_path.exists():
            logger.warning("Test interface file not found")
            return HTMLResponse(
                content="<html><body><h1>Test interface not available</h1><p>The test interface file has not been created yet.</p></body></html>",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Read and return the HTML file
        with open(static_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        logger.debug("Test interface served")
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(
            "Error serving test interface",
            extra={"error": str(e)},
            exc_info=True
        )
        
        return HTMLResponse(
            content="<html><body><h1>Error</h1><p>Failed to load test interface</p></body></html>",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@router.post(
    "/api/v1/analyze-materials",
    response_model=MaterialAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze device materials",
    description="Analyze recyclable and precious materials in a device based on brand, model, and category"
)
@limiter.limit("10/minute")
async def analyze_materials(
    request: Request,
    analysis_request: MaterialAnalysisRequest
) -> MaterialAnalysisResponse:
    """
    Analyze device materials and estimate recyclable content with market rates.
    
    Uses LLM to identify precious metals, base metals, and other recyclable materials
    in the specified device, providing quantity estimates and current market rates
    for the specified country.
    
    Args:
        request: FastAPI request object (required for rate limiting)
        analysis_request: Material analysis request with device details
        
    Returns:
        MaterialAnalysisResponse with material breakdown and market rates
    """
    start_time = time.time()
    
    try:
        # Analyze materials using LLM
        materials, analysis_description, model_used = await material_analyzer_service.analyze_materials(
            analysis_request
        )
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Build response data
        response_data = MaterialAnalysisData(
            brand=BrandInfo(
                id=analysis_request.brand_id,
                name=analysis_request.brand_name
            ),
            category=CategoryInfo(
                id=analysis_request.category_id,
                name=analysis_request.category_name
            ),
            model=ModelInfo(
                id=analysis_request.model_id,
                name=analysis_request.model_name
            ),
            country=analysis_request.country,
            analysisDescription=analysis_description,
            materials=materials,
            metadata=AnalysisMetadata(
                llmModel=model_used
            )
        )
        
        logger.info(
            "Material analysis completed successfully",
            extra={
                "brand": analysis_request.brand_name,
                "model": analysis_request.model_name,
                "material_count": len(materials),
                "processing_time_ms": processing_time
            }
        )
        
        # Return success response
        return MaterialAnalysisResponse(
            success=True,
            processingTimeMs=processing_time,
            data=response_data
        )
        
    except MaterialAnalysisError as e:
        # Handle known material analysis errors
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.warning(
            f"Material analysis error: {e.error_code}",
            extra={
                "error_code": e.error_code,
                "error_message": e.message,
                "processing_time_ms": processing_time
            }
        )
        
        return MaterialAnalysisResponse(
            success=False,
            processingTimeMs=processing_time,
            error={
                "code": e.error_code,
                "message": e.message
            }
        )
        
    except Exception as e:
        # Handle unexpected errors
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Unexpected error during material analysis",
            extra={
                "error": str(e),
                "processing_time_ms": processing_time
            },
            exc_info=True
        )
        
        return MaterialAnalysisResponse(
            success=False,
            processingTimeMs=processing_time,
            error={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during material analysis"
            }
        )
