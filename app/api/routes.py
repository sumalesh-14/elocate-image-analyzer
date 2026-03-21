"""
FastAPI routes and endpoints for the Image Device Identification API.

This module implements:
- POST /api/v1/analyze: Device image analysis endpoint
- GET /health: Health check endpoint
- GET /test: Test interface endpoint
"""

import time
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List
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
    AnalysisMetadata,
    RecyclingEstimate,
    DevicePricing
)
from app.models.chat import ChatRequest, ChatResponse, ChatError
from app.services.analyzer import analyzer_service, AnalysisError
from app.services.material_analyzer import material_analyzer_service, MaterialAnalysisError
from app.services.device_pricing import device_pricing_service
from app.services.pricing_calculator import pricing_calculator
from app.services.llm_router import llm_service
from app.api.middleware import limiter


# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# In-memory session store: session_id -> list of ChatMessageHistory dicts
# Each entry: {"role": "user"|"model", "parts": [{"text": "..."}]}
_chat_sessions: Dict[str, List[dict]] = {}


def _parse_bot_response(raw: str):
    """Parse RESPONSE:/SUGGESTIONS: format from the LLM output.
    Returns (text, suggestions_list). Falls back gracefully if format is missing."""
    text_out = raw
    suggestions = []
    if "RESPONSE:" in raw:
        parts = raw.split("RESPONSE:", 1)[1]
        if "SUGGESTIONS:" in parts:
            text_part, sug_part = parts.split("SUGGESTIONS:", 1)
            text_out = text_part.strip()
            suggestions = [s.strip() for s in sug_part.strip().split("|") if s.strip()]
        else:
            text_out = parts.strip()
    return text_out, suggestions or None


async def _generate_suggestions(user_message: str, bot_reply: str):
    """
    Generate 3 contextual follow-up suggestions based on the bot's reply content.
    Covers both e-waste recycling topics and ELocate platform features.
    """
    # Match against the bot reply (what was just explained) for maximum relevance
    ctx = (bot_reply + " " + user_message).lower()

    # --- ELocate platform flows ---
    if any(w in ctx for w in ["sign up", "register", "create account", "registration"]):
        return ["How do I sign in after registering?", "Where can I view my profile?", "How do I book my first recycle request?"]
    if any(w in ctx for w in ["sign in", "login", "log in", "forgot password", "credentials"]):
        return ["How do I book a recycle request?", "Where can I see my past requests?", "How do I update my profile?"]
    if any(w in ctx for w in ["book recycle", "recycle request", "schedule pickup", "pickup", "drop-off", "book-recycle"]):
        return ["How do I track my recycle request?", "What device types can I recycle?", "Can I cancel a recycle request?"]
    if any(w in ctx for w in ["track", "status", "my requests", "pending", "in transit", "completed"]):
        return ["What does 'In Transit' status mean?", "How long does a pickup take?", "How do I contact support about my request?"]
    if any(w in ctx for w in ["analyze", "material", "composition", "value", "condition", "scrap", "working"]):
        return ["How do I choose the right condition for my device?", "What does the analysis result show?", "Can I analyze a device not in the list?"]
    if any(w in ctx for w in ["e-facilities", "facility", "map", "nearby", "recycling center", "drop-off point", "location"]):
        return ["What items do recycling centers accept?", "How do I find the nearest facility?", "Do recycling centers charge a fee?"]
    if any(w in ctx for w in ["education", "learn", "rules", "guidelines", "regulation", "law"]):
        return ["What items are accepted for recycling?", "How do I prepare my device before recycling?", "Why is e-waste recycling important?"]
    if any(w in ctx for w in ["profile", "account", "impact score", "co2", "edit profile", "settings"]):
        return ["How do I edit my profile?", "What is the impact score?", "How do I change my password?"]
    if any(w in ctx for w in ["contact", "support", "help", "reach", "team"]):
        return ["How do I report an issue with my request?", "Where is the contact form?", "What is ELocate's support email?"]
    if any(w in ctx for w in ["intermediary", "partner", "become", "apply", "application", "approved", "facility owner"]):
        return ["What does an intermediary do on ELocate?", "How long does partner approval take?", "What features does the intermediary dashboard have?"]
    if any(w in ctx for w in ["intermediary dashboard", "collections", "assign driver", "schedule", "clients"]):
        return ["How do I assign a driver to a pickup?", "Where can I view my collection schedule?", "How do I generate a report?"]
    if any(w in ctx for w in ["admin", "administrator", "manage", "approve partner", "citizen management"]):
        return ["How does admin approve a partner?", "What can admins see in the dashboard?", "How does admin manage citizens?"]

    # --- E-waste device topics ---
    if any(w in ctx for w in ["phone", "mobile", "smartphone", "iphone", "samsung", "android"]):
        return ["How do I wipe my data before recycling?", "What about the battery inside my phone?", "Where can I drop off my old phone?"]
    if any(w in ctx for w in ["laptop", "computer", "pc", "macbook", "notebook"]):
        return ["How do I wipe my hard drive before recycling?", "Can I recycle laptop batteries separately?", "How do I find a laptop recycling center?"]
    if any(w in ctx for w in ["battery", "batteries", "lithium"]):
        return ["Can I throw batteries in regular trash?", "What types of batteries are recyclable?", "Where are battery drop-off points?"]
    if any(w in ctx for w in ["tv", "television", "monitor", "screen", "display", "crt"]):
        return ["Are old CRT TVs more hazardous than LCDs?", "How do I prepare my TV for recycling?", "Where can I recycle large electronics?"]
    if any(w in ctx for w in ["environment", "impact", "harmful", "toxic", "hazard", "pollution", "soil", "water"]):
        return ["Which e-waste items are most toxic?", "How does e-waste affect soil and water?", "What materials are recovered from recycled electronics?"]
    if any(w in ctx for w in ["data", "wipe", "privacy", "personal", "reset", "factory reset"]):
        return ["How do I factory reset my phone?", "Is a factory reset enough to protect my data?", "What else should I remove before recycling?"]

    # Generic fallback
    return ["How do I book a recycle request?", "How do I find a nearby e-waste facility?", "How do I analyze my device?"]


# Topics that are clearly off-topic for EcoBot — checked before hitting the LLM
_OFF_TOPIC_PATTERNS = [
    r'\bpython\b', r'\bjava\b', r'\bjavascript\b', r'\bc\+\+\b', r'\bruby\b', r'\brust\b',
    r'\bprogramm', r'\bcoding\b', r'\bcode\b', r'\balgorithm\b', r'\bsort(ing)?\b',
    r'\bfunction\b', r'\bvariable\b', r'\bloop\b', r'\barray\b', r'\bclass\b',
    r'\brecipe\b', r'\bcook(ing)?\b', r'\bfood\b', r'\bsport\b', r'\bfootball\b',
    r'\bmovie\b', r'\bfilm\b', r'\bsong\b', r'\bmusic\b', r'\bjoke\b',
    r'\bweather\b', r'\bnews\b', r'\bpolitics\b', r'\bmath\b', r'\bcalcul',
    r'\bhistory\b', r'\bgeograph', r'\bcapital of\b', r'\bwho is\b', r'\bwhat is [a-z]+ programm',
]

_OFF_TOPIC_REPLY = "🌿 I'm EcoBot, your e-waste recycling assistant. I can only help with topics related to e-waste, recycling electronics, and the ELocate platform. For anything else, please use a general-purpose assistant. ♻️"
_OFF_TOPIC_SUGGESTIONS = [
    "How do I recycle my old phone?",
    "Where can I drop off old batteries?",
    "What e-waste items are most harmful?",
    "How does e-waste affect the environment?",
]


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
            "NOT_A_DEVICE": status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        
        import traceback
        print(f"\n\033[91m❌  UNEXPECTED ERROR IN ANALYZE ENDPOINT\033[0m")
        print(f"    {type(e).__name__}: {e}")
        traceback.print_exc()
        
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
        materials, analysis_description, model_used, total_material_value = await material_analyzer_service.analyze_materials(
            analysis_request
        )
        
        # Fetch device pricing (optional, non-blocking)
        device_pricing = None
        market_price = None
        try:
            device_pricing = await device_pricing_service.get_device_pricing(
                brand_name=analysis_request.brand_name,
                model_name=analysis_request.model_name,
                category_name=analysis_request.category_name,
                country=analysis_request.country
            )
            if device_pricing and device_pricing.current_market_price:
                market_price = device_pricing.current_market_price
        except Exception as e:
            logger.warning(f"Failed to fetch device pricing: {str(e)}")
        
        # Get currency from first material (all should have same currency)
        currency = materials[0].currency if materials else "INR"
        
        # Calculate pricing based on condition using pricing calculator
        pricing_recommendation = pricing_calculator.get_pricing_recommendation(
            total_material_value=total_material_value,
            market_price=market_price,
            device_condition=analysis_request.device_condition,
            device_age_years=None,  # TODO: Calculate from model release date if available
            category_name=analysis_request.category_name
        )
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Build recycling estimate with condition-based pricing
        recycling_estimate = RecyclingEstimate(
            totalMaterialValue=round(total_material_value, 2),
            suggestedRecyclingPrice=pricing_recommendation["recycling_price"],
            suggestedBuybackPrice=pricing_recommendation["buyback_price"],
            conditionImpact=pricing_recommendation["condition_impact"],
            currency=currency,
            priceBreakdown=pricing_recommendation["price_breakdown"]
        )
        
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
            devicePricing=device_pricing,
            recyclingEstimate=recycling_estimate,
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
        
        material_status_code_map = {
            "NOT_AN_EWASTE_DEVICE": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "NO_LLM_WORKERS": status.HTTP_503_SERVICE_UNAVAILABLE,
            "ALL_WORKERS_FAILED": status.HTTP_503_SERVICE_UNAVAILABLE,
        }
        
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

@router.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with EcoBot",
    description="Send a message to the EcoBot AI assistant and get a response"
)
@limiter.limit("20/minute")
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest
) -> ChatResponse:
    try:
        if not llm_service.workers:
            return ChatResponse(success=False, error=ChatError(code="NO_API_KEY", message="No LLM API keys configured"))

        worker = llm_service.workers[0]  # Use primary worker (usually Gemini)

        # --- Session context management ---
        session_id = chat_request.session_id or str(uuid.uuid4())
        if session_id not in _chat_sessions:
            _chat_sessions[session_id] = []

        # Prefer server-stored history; fall back to client-sent history for first message
        stored_history = _chat_sessions[session_id]
        history_to_use = stored_history if stored_history else chat_request.history

        # --- Logging ---
        from app.utils.orchestration_log import (
            log_chat_request, log_chat_off_topic, log_chat_complete, log_chat_error
        )
        start_time = log_chat_request(chat_request.message, session_id, bool(history_to_use))

        # --- Off-topic guard: check before hitting the LLM ---
        msg_lower = chat_request.message.lower()
        is_off_topic = any(re.search(p, msg_lower) for p in _OFF_TOPIC_PATTERNS)
        if is_off_topic:
            log_chat_off_topic(chat_request.message)
            _chat_sessions[session_id].append({"role": "user", "parts": [{"text": chat_request.message}]})
            _chat_sessions[session_id].append({"role": "model", "parts": [{"text": _OFF_TOPIC_REPLY}]})
            return ChatResponse(
                success=True,
                text=_OFF_TOPIC_REPLY,
                session_id=session_id,
                suggestions=_OFF_TOPIC_SUGGESTIONS
            )

        # --- System instruction ---
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        system_instruction = ECOBOT_SYSTEM_PROMPT

        # --- LLM call with full fallback across all workers ---
        result = await llm_service.call_chat_with_fallback(
            messages_by_provider={"history": history_to_use, "user_message": chat_request.message},
            system_instruction=system_instruction,
        )
        reply_text = result["text"]
        worker_name = result["worker_name"]

        # --- Persist turn ---
        _chat_sessions[session_id].append({"role": "user", "parts": [{"text": chat_request.message}]})
        _chat_sessions[session_id].append({"role": "model", "parts": [{"text": reply_text}]})

        # --- Suggestions ---
        suggestions = await _generate_suggestions(chat_request.message, reply_text)

        log_chat_complete(start_time, worker_name, reply_text)
        return ChatResponse(success=True, text=reply_text, session_id=session_id, suggestions=suggestions)

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        from app.utils.orchestration_log import log_chat_error
        log_chat_error("CHAT_API_ERROR", str(e))
        return ChatResponse(
            success=False,
            error=ChatError(code="CHAT_API_ERROR", message=f"Failed to generate response: {str(e)}")
        )

