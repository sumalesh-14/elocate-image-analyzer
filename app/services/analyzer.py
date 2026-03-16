"""
Analyzer orchestration service.

This module orchestrates the device identification workflow:
1. Validates images using the image_validator service
2. Pass 1 Gemini call – identifies category from the exact DB category list
3. Auto-seeds new category into DB if Gemini signals "NEW:<name>"
4. Pass 2 Gemini call – identifies brand + model + all metadata using
   brand list filtered by the matched category
5. Auto-seeds new brand/model into DB if Gemini signals "NEW:<name>"
6. Applies confidence-based logic for uncertain fields
7. Handles temporary files with automatic cleanup
8. Logs all analysis requests
"""

import tempfile
import os
import logging
from typing import Optional
from fastapi import UploadFile

from app.services.image_validator import validate_image, ValidationResult
from app.services.llm_router import llm_service, LLMAPIError
from app.services.database_matcher import database_matcher
from app.models.response import DeviceData, ErrorData
import app.utils.orchestration_log as olog


# Configure logger
logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Exception raised during device analysis."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class AnalyzerService:
    """Service for orchestrating device image analysis."""
    
    async def analyze_device(self, file: UploadFile) -> DeviceData:
        """
        Orchestrate the two-pass device analysis workflow.

        Pass 1: Fetch DB categories → Gemini picks exact category (or signals NEW:)
                → auto-seed new category if needed
        Pass 2: Fetch brands for matched category → Gemini picks brand + model
                + all other metadata → auto-seed new brand/model if needed

        Args:
            file: Uploaded image file

        Returns:
            DeviceData containing extracted device information

        Raises:
            AnalysisError: If validation or analysis fails
        """
        temp_file_path = None

        try:
            # Read file bytes
            file_bytes = await file.read()

            # ── Console banner ─────────────────────────────────────────────
            start_time = olog.log_request_received(
                file.filename or "unknown",
                len(file_bytes),
                file.content_type or "unknown",
            )

            logger.info(
                "Image analysis request received",
                extra={
                    "upload_filename": file.filename,
                    "file_size": len(file_bytes),
                    "content_type": file.content_type,
                }
            )

            # ── Image validation ───────────────────────────────────────────
            validation_result = validate_image(file_bytes, file.filename)
            if not validation_result.is_valid:
                olog.log_image_invalid(validation_result.error_code, validation_result.message)
                logger.warning(
                    "Image validation failed",
                    extra={
                        "filename": file.filename,
                        "error_code": validation_result.error_code,
                        "error_message": validation_result.message,
                    }
                )
                raise AnalysisError(validation_result.error_code, validation_result.message)

            olog.log_image_valid(file.filename or "unknown")

            # Save to temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(file_bytes)

            # ------------------------------------------------------------------
            # Pass 1 – Category identification (DB-grounded)
            # ------------------------------------------------------------------
            try:
                categories = await database_matcher.get_all_categories()
                category_names = [c['name'] for c in categories]
                olog.log_pass1_start(len(categories), category_names)

                pass1_result = await llm_service.analyze_pass1_category(
                    file_bytes, categories
                )
            except TimeoutError as e:
                olog.log_error("PASS-1", "ANALYSIS_TIMEOUT", str(e))
                raise AnalysisError("ANALYSIS_TIMEOUT", str(e))
            except LLMAPIError as e:
                olog.log_error("PASS-1", "SERVICE_UNAVAILABLE", str(e))
                raise AnalysisError("SERVICE_UNAVAILABLE", str(e))
            except Exception as e:
                olog.log_error("PASS-1", "INTERNAL_ERROR", str(e))
                logger.error(
                    "Unexpected error during Pass-1 Gemini analysis",
                    extra={"filename": file.filename, "error": str(e)},
                    exc_info=True,
                )
                raise AnalysisError("INTERNAL_ERROR", "An unexpected error occurred during analysis")

            olog.log_pass1_result(
                pass1_result.get("category", "unknown"),
                pass1_result.get("deviceType", "unknown"),
                pass1_result.get("confidenceScore", 0.0),
            )

            # Check if it's a device at all
            if not self._is_device(pass1_result):
                olog.log_error(
                    "DEVICE CHECK", "NOT_A_DEVICE",
                    "The uploaded image does not appear to be an e-waste or electronic device"
                )
                logger.warning(
                    "Non-device image detected",
                    extra={"filename": file.filename, "category": pass1_result.get("category")},
                )
                raise AnalysisError(
                    "NOT_A_DEVICE",
                    "The uploaded image does not appear to be an e-waste or electronic device. Please upload a clear image of an electronic device such as a smartphone, laptop, tablet, or other electronic equipment.",
                )

            # ------------------------------------------------------------------
            # Resolve category (exact pick or auto-seed NEW)
            # ------------------------------------------------------------------
            pass1_confidence = pass1_result.get("confidenceScore", 0.5)
            category_pick = pass1_result.get("category", "other")
            device_type = pass1_result.get("deviceType", "unknown")

            category_match = await database_matcher._resolve_category(
                category_pick, categories, pass1_confidence
            )

            # Determine the resolved category name for Pass 2 prompt and display
            if category_match:
                resolved_category = category_match.name
                olog.log_category_resolved(
                    category_match.name, category_match.is_new, category_match.similarity_score
                )
            else:
                from app.services.database_matcher import DatabaseMatcher
                _, resolved_category = DatabaseMatcher._parse_new_prefix(category_pick)
                if not resolved_category:
                    resolved_category = "Other"
                olog.log_category_failed(category_pick)

            logger.info(
                f"Pass-1 complete: category='{resolved_category}' "
                f"(confidence={pass1_confidence:.2f}, "
                f"new={category_match.is_new if category_match else 'N/A'})"
            )

            # ------------------------------------------------------------------
            # Pass 2 – Brand + model + metadata (DB-grounded)
            # ------------------------------------------------------------------
            try:
                if category_match:
                    brands = await database_matcher.get_brands_for_category(category_match.id)
                else:
                    brands = []

                brand_names = [b['name'] for b in brands]
                olog.log_pass2_start(resolved_category, len(brands), brand_names)

                pass2_result = await llm_service.analyze_pass2_brand_model(
                    file_bytes, resolved_category, brands, models=[]
                )
            except TimeoutError as e:
                olog.log_error("PASS-2", "ANALYSIS_TIMEOUT", str(e))
                raise AnalysisError("ANALYSIS_TIMEOUT", str(e))
            except LLMAPIError as e:
                olog.log_error("PASS-2", "SERVICE_UNAVAILABLE", str(e))
                raise AnalysisError("SERVICE_UNAVAILABLE", str(e))
            except Exception as e:
                olog.log_error("PASS-2", "INTERNAL_ERROR", str(e))
                logger.error(
                    "Unexpected error during Pass-2 Gemini analysis",
                    extra={"filename": file.filename, "error": str(e)},
                    exc_info=True,
                )
                raise AnalysisError("INTERNAL_ERROR", "An unexpected error occurred during analysis")

            olog.log_pass2_result(
                pass2_result.get("brand")
            )

            # ------------------------------------------------------------------
            # Resolve brand (exact pick or auto-seed NEW)
            # ------------------------------------------------------------------
            brand_pick = pass2_result.get("brand")
            brand_match = None
            if category_match and brand_pick:
                brand_match = await database_matcher._resolve_brand(
                    brand_pick, brands, category_match.id, pass1_confidence
                )

            if brand_match:
                olog.log_brand_resolved(
                    brand_match.name, brand_match.is_new, brand_match.similarity_score
                )
            else:
                olog.log_brand_failed(brand_pick)

            # ------------------------------------------------------------------
            # Pass 3 – Model Identification (DB-grounded based on Brand)
            # ------------------------------------------------------------------
            model_pick = pass2_result.get("model") # Fallback from pass 2
            model_match = None
            models = []
            model_uncertainty_reason = None  # Initialize to avoid UnboundLocalError
            
            if category_match and brand_match:
                models = await database_matcher.get_models_for_brand_category(
                    brand_match.id, category_match.id
                )
                
                model_names = [m['name'] for m in models]
                olog.log_pass3_start(brand_match.name, len(models), model_names)
                
                try:
                    pass3_result = await llm_service.analyze_pass3_model(
                        file_bytes, resolved_category, brand_match.name, models, pass2_model=model_pick
                    )
                    
                    if pass3_result and pass3_result.get("model"):
                        model_pick = pass3_result.get("model")
                    
                    # Extract uncertainty reason if provided
                    model_uncertainty_reason = pass3_result.get("uncertainty_reason") if pass3_result else None
                    
                    # Extract confidence level and convert to numeric score
                    confidence_level = pass3_result.get("confidence", "medium") if pass3_result else "medium"
                    model_confidence = self._convert_confidence_level_to_score(confidence_level)
                        
                    olog.log_pass3_result(model_pick, model_uncertainty_reason)
                    
                except TimeoutError as e:
                    olog.log_error("PASS-3", "ANALYSIS_TIMEOUT", str(e))
                except LLMAPIError as e:
                    olog.log_error("PASS-3", "SERVICE_UNAVAILABLE", str(e))
                except Exception as e:
                    olog.log_error("PASS-3", "INTERNAL_ERROR", str(e))
                    logger.error(
                        "Unexpected error during Pass-3 Gemini analysis",
                        extra={"filename": file.filename, "error": str(e)},
                        exc_info=True,
                    )
                
                # Resolve Model
                if model_pick:
                    model_match = await database_matcher._resolve_model(
                        model_pick, models, brand_match.id, category_match.id, 
                        model_confidence if 'model_confidence' in locals() else pass1_confidence,
                        metadata=pass3_result if 'pass3_result' in locals() else None
                    )

            if model_match:
                olog.log_model_resolved(
                    model_match.name, model_match.is_new,
                    model_match.similarity_score, len(models)
                )
            else:
                olog.log_model_failed(model_pick)

            # ------------------------------------------------------------------
            # Build final confidence + uncertainty logic
            # ------------------------------------------------------------------
            confidence = self._calculate_confidence_two_pass(
                pass1_confidence, pass2_result
            )

            brand_text = self._apply_uncertainty_logic(
                brand_match.name if brand_match else brand_pick,
                confidence
            )
            model_text = self._apply_uncertainty_logic(
                model_match.name if model_match else model_pick,
                confidence
            )

            sanitized_attributes = self._sanitize_attributes(
                pass2_result.get("attributes", {})
            )

            enhanced_fields = self._process_enhanced_fields(
                pass2_result, resolved_category, device_type
            )
            
            # Add model uncertainty reason if available
            if model_uncertainty_reason:
                enhanced_fields["model_uncertainty_reason"] = model_uncertainty_reason

            db_status = database_matcher._determine_status(
                category_match, brand_match, model_match, brand_pick, model_pick
            )
            database_match_fields = {
                "category_id": category_match.id if category_match else None,
                "brand_id": brand_match.id if brand_match else None,
                "model_id": model_match.id if model_match else None,
                "category_match_score": category_match.similarity_score if category_match else None,
                "brand_match_score": brand_match.similarity_score if brand_match else None,
                "model_match_score": model_match.similarity_score if model_match else None,
                "database_status": db_status,
            }

            # ------------------------------------------------------------------
            # Assemble DeviceData
            # ------------------------------------------------------------------
            device_data = DeviceData(
                category=resolved_category,
                brand=brand_text,
                model=model_text,
                deviceType=device_type,
                confidenceScore=confidence,
                accuracy=confidence,
                attributes=sanitized_attributes,
                lowConfidence=confidence < 0.5,
                **enhanced_fields,
                **database_match_fields,
            )

            # ── Final console summary ──────────────────────────────────────
            olog.log_final_result(
                start_time=start_time,
                category=resolved_category,
                brand=brand_text,
                model=model_text,
                device_type=device_type,
                confidence=confidence,
                db_status=db_status,
                category_id=database_match_fields["category_id"],
                brand_id=database_match_fields["brand_id"],
                model_id=database_match_fields["model_id"],
                category_new=category_match.is_new if category_match else False,
                brand_new=brand_match.is_new if brand_match else False,
                model_new=model_match.is_new if model_match else False,
                severity=enhanced_fields.get("severity", "low"),
                contains_hazardous=enhanced_fields.get("contains_hazardous_materials", False),
                contains_precious=enhanced_fields.get("contains_precious_metals", False),
                model_uncertainty_reason=enhanced_fields.get("model_uncertainty_reason"),
            )

            logger.info(
                "Two-pass analysis completed successfully",
                extra={
                    "upload_filename": file.filename,
                    "category": device_data.category,
                    "brand": device_data.brand,
                    "model": device_data.model,
                    "confidence": device_data.confidenceScore,
                    "db_status": db_status,
                    "category_new": category_match.is_new if category_match else False,
                    "brand_new": brand_match.is_new if brand_match else False,
                    "model_new": model_match.is_new if model_match else False,
                    "model_uncertainty_reason": device_data.model_uncertainty_reason if hasattr(device_data, 'model_uncertainty_reason') else None,
                }
            )

            return device_data

        finally:
            # Always cleanup temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.error(f"Failed to cleanup temporary file: {e}")
    

    def _calculate_confidence_two_pass(
        self, pass1_confidence: float, pass2_result: dict
    ) -> float:
        """
        Calculate overall confidence score from two-pass results.

        Args:
            pass1_confidence: Confidence returned by Pass-1 (category)
            pass2_result: Raw result from Pass-2 (brand, model, attributes)

        Returns:
            Final confidence score between 0.0 and 1.0
        """
        base_confidence = pass1_confidence
        adjustments = 0.0

        brand = pass2_result.get("brand")
        model = pass2_result.get("model")
        attributes = pass2_result.get("attributes", {})

        if not brand or str(brand).lower() in ("null", "none", ""):
            adjustments -= 0.1
        if not model or str(model).lower() in ("null", "none", ""):
            adjustments -= 0.1
        if len(attributes) > 2:
            adjustments += 0.05

        final_confidence = max(0.0, min(1.0, base_confidence + adjustments))
        logger.debug(
            f"Two-pass confidence: base={base_confidence}, "
            f"adjustments={adjustments}, final={final_confidence}"
        )
        return final_confidence
    
    def _convert_confidence_level_to_score(self, confidence_level: str) -> float:
        """
        Convert confidence level string to numeric score.
        
        Args:
            confidence_level: Confidence level from LLM ("high", "medium", "low")
            
        Returns:
            Numeric confidence score between 0.0 and 1.0
        """
        level_map = {
            "high": 0.9,      # High confidence -> auto-seed enabled
            "medium": 0.6,    # Medium confidence -> no auto-seed
            "low": 0.3        # Low confidence -> no auto-seed
        }
        score = level_map.get(confidence_level.lower(), 0.6)
        logger.debug(f"Converted confidence level '{confidence_level}' to score {score}")
        return score

    # Keep legacy method name so any other callers don't break
    def _calculate_confidence(self, gemini_result: dict) -> float:
        """Legacy single-pass confidence calculation (kept for compatibility)."""
        return self._calculate_confidence_two_pass(
            gemini_result.get("confidenceScore", 0.5), gemini_result
        )
    
    def _apply_uncertainty_logic(
        self, 
        field_value: Optional[str], 
        confidence: float
    ) -> Optional[str]:
        """
        Determine if a field should be returned as null based on confidence.
        
        Args:
            field_value: The field value from Gemini
            confidence: Overall confidence score
            
        Returns:
            Field value or None if uncertain
        """
        # If field is already null, keep it null
        if field_value is None or field_value == "null":
            return None
        
        # If confidence is very low, return null for uncertain fields
        if confidence < 0.4:
            logger.debug(f"Returning null for field due to low confidence: {confidence}")
            return None
        
        # If field value looks uncertain (contains words like "unknown", "unclear")
        uncertain_indicators = ["unknown", "unclear", "uncertain", "not visible", "n/a"]
        if any(indicator in field_value.lower() for indicator in uncertain_indicators):
            logger.debug(f"Returning null for uncertain field value: {field_value}")
            return None
        
        return field_value
    
    def _sanitize_attributes(self, attributes: dict) -> dict:
        """
        Sanitize attributes to ensure all values are strings.
        
        Converts lists to comma-separated strings and removes None values.
        
        Args:
            attributes: Raw attributes from Gemini
            
        Returns:
            Sanitized attributes dictionary with string values only
        """
        sanitized = {}
        
        for key, value in attributes.items():
            if value is None:
                # Skip None values
                continue
            elif isinstance(value, list):
                # Convert list to comma-separated string, filtering out None
                filtered_list = [str(v) for v in value if v is not None]
                if filtered_list:
                    sanitized[key] = ", ".join(filtered_list)
            elif isinstance(value, (str, int, float, bool)):
                # Convert to string
                sanitized[key] = str(value)
            else:
                # For other types, try to convert to string
                try:
                    sanitized[key] = str(value)
                except:
                    # Skip if conversion fails
                    logger.debug(f"Skipping attribute {key} - failed to convert to string")
                    continue
        
        return sanitized
    
    def _process_enhanced_fields(
        self,
        gemini_result: dict,
        category: str,
        device_type: str
    ) -> dict:
        """
        Process and validate enhanced safety and material information fields.
        
        Applies validation, defaults, and business rules for:
        - Severity levels
        - Precious metals information
        - Hazardous materials information
        - Contextual notes
        
        Args:
            gemini_result: Raw result from Gemini API
            category: Normalized device category
            device_type: Device type/sub-category
            
        Returns:
            Dictionary with enhanced field values
        """
        # Extract raw values from Gemini result
        raw_severity = gemini_result.get("severity")
        raw_info_note = gemini_result.get("info_note")
        raw_contains_precious = gemini_result.get("contains_precious_metals")
        raw_precious_info = gemini_result.get("precious_metals_info")
        raw_contains_hazardous = gemini_result.get("contains_hazardous_materials")
        raw_hazardous_info = gemini_result.get("hazardous_materials_info")
        
        # Validate and set severity with defaults
        severity = self._determine_severity(
            raw_severity,
            category,
            device_type
        )
        
        # Validate and truncate string fields
        info_note = self._validate_string_length(raw_info_note, 500)
        
        # Process precious metals information
        contains_precious_metals = bool(raw_contains_precious) if raw_contains_precious is not None else self._has_precious_metals_default(category)
        precious_metals_info = None
        if contains_precious_metals:
            precious_metals_info = self._validate_string_length(
                raw_precious_info or self._get_default_precious_metals_info(category),
                300
            )
        
        # Process hazardous materials information
        contains_hazardous_materials = bool(raw_contains_hazardous) if raw_contains_hazardous is not None else self._has_hazardous_materials_default(category, device_type)
        hazardous_materials_info = None
        if contains_hazardous_materials:
            hazardous_materials_info = self._validate_string_length(
                raw_hazardous_info or self._get_default_hazardous_materials_info(category, device_type),
                300
            )
        
        logger.debug(
            f"Enhanced fields processed: severity={severity}, "
            f"precious_metals={contains_precious_metals}, "
            f"hazardous={contains_hazardous_materials}"
        )
        
        return {
            "info_note": info_note,
            "severity": severity,
            "contains_precious_metals": contains_precious_metals,
            "precious_metals_info": precious_metals_info,
            "contains_hazardous_materials": contains_hazardous_materials,
            "hazardous_materials_info": hazardous_materials_info
        }
    
    def _determine_severity(
        self,
        raw_severity: Optional[str],
        category: str,
        device_type: str
    ) -> str:
        """
        Determine severity level with validation and business rules.
        
        Business rules:
        - CRT displays must be "critical"
        - Lithium battery devices (smartphones, laptops, tablets) must be at least "high"
        - Invalid severity values trigger default logic
        
        Args:
            raw_severity: Severity from Gemini (may be invalid)
            category: Normalized device category
            device_type: Device type/sub-category
            
        Returns:
            Valid severity level: "low", "medium", "high", or "critical"
        """
        valid_severities = ["low", "medium", "high", "critical"]
        
        # Check for CRT displays - always critical
        if self._is_crt_display(device_type):
            logger.debug("CRT display detected - setting severity to critical")
            return "critical"
        
        # Check for lithium battery devices - at least high
        if self._has_lithium_battery(category, device_type):
            # If raw severity is provided and valid, ensure it's at least "high"
            if raw_severity and raw_severity.lower() in valid_severities:
                severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                if severity_order[raw_severity.lower()] >= severity_order["high"]:
                    return raw_severity.lower()
            logger.debug("Lithium battery device detected - setting severity to high")
            return "high"
        
        # Validate raw severity
        if raw_severity and raw_severity.lower() in valid_severities:
            return raw_severity.lower()
        
        # Apply default severity based on category
        default_severity = self._get_default_severity(category)
        logger.debug(f"Using default severity '{default_severity}' for category '{category}'")
        return default_severity
    
    def _is_crt_display(self, device_type: str) -> bool:
        """Check if device is a CRT display."""
        device_type_lower = device_type.lower()
        crt_indicators = ["crt", "cathode ray", "tube monitor", "tube tv", "tube television"]
        return any(indicator in device_type_lower for indicator in crt_indicators)
    
    def _has_lithium_battery(self, category: str, device_type: str) -> bool:
        """Check if device likely contains lithium battery."""
        category_lower = category.lower()
        device_type_lower = device_type.lower()
        
        # Categories that typically have lithium batteries
        lithium_categories = ["mobile phone", "laptop", "tablet"]
        if any(cat in category_lower for cat in lithium_categories):
            return True
        
        # Device types that indicate lithium batteries
        lithium_types = ["smartphone", "phone", "laptop", "notebook", "tablet", "portable", "lithium"]
        return any(dtype in device_type_lower for dtype in lithium_types)
    
    def _get_default_severity(self, category: str) -> str:
        """
        Get default severity level based on device category.
        
        Args:
            category: Normalized device category
            
        Returns:
            Default severity level
        """
        category_lower = category.lower()
        
        # High severity categories
        if any(cat in category_lower for cat in ["mobile phone", "laptop", "tablet", "battery"]):
            return "high"
        
        # Medium severity categories
        if any(cat in category_lower for cat in ["charger", "appliance"]):
            return "medium"
        
        # Low severity categories (cables, accessories)
        return "low"
    
    def _validate_string_length(self, value: Optional[str], max_length: int) -> Optional[str]:
        """
        Validate and truncate string to maximum length.
        
        Args:
            value: String value to validate
            max_length: Maximum allowed length
            
        Returns:
            Validated string or None
        """
        if value is None:
            return None
        
        # Convert to string if not already
        str_value = str(value).strip()
        
        # Return None for empty strings
        if not str_value:
            return None
        
        # Truncate if exceeds max length
        if len(str_value) > max_length:
            logger.warning(f"String truncated from {len(str_value)} to {max_length} characters")
            return str_value[:max_length]
        
        return str_value
    
    def _has_precious_metals_default(self, category: str) -> bool:
        """
        Determine if device category typically contains precious metals.
        
        Args:
            category: Normalized device category
            
        Returns:
            True if category typically contains precious metals
        """
        category_lower = category.lower()
        
        # Categories with circuit boards typically have precious metals
        precious_metal_categories = [
            "mobile phone", "laptop", "tablet", "appliance"
        ]
        
        return any(cat in category_lower for cat in precious_metal_categories)
    
    def _get_default_precious_metals_info(self, category: str) -> str:
        """
        Get default precious metals information based on category.
        
        Args:
            category: Normalized device category
            
        Returns:
            Default precious metals information
        """
        category_lower = category.lower()
        
        if "mobile phone" in category_lower or "tablet" in category_lower:
            return "Circuit boards contain gold, silver, copper, and palladium in connectors and chips"
        elif "laptop" in category_lower:
            return "Motherboard and components contain gold, silver, copper, and palladium"
        elif "appliance" in category_lower:
            return "Circuit boards may contain copper and small amounts of precious metals"
        
        return "May contain recoverable precious metals in electronic components"
    
    def _has_hazardous_materials_default(self, category: str, device_type: str) -> bool:
        """
        Determine if device typically contains hazardous materials.
        
        Args:
            category: Normalized device category
            device_type: Device type/sub-category
            
        Returns:
            True if device typically contains hazardous materials
        """
        category_lower = category.lower()
        device_type_lower = device_type.lower()
        
        # Categories/types with batteries or displays
        hazardous_categories = [
            "mobile phone", "laptop", "tablet", "battery", "appliance"
        ]
        
        hazardous_types = [
            "battery", "display", "monitor", "tv", "television", "screen"
        ]
        
        return (
            any(cat in category_lower for cat in hazardous_categories) or
            any(dtype in device_type_lower for dtype in hazardous_types)
        )
    
    def _get_default_hazardous_materials_info(self, category: str, device_type: str) -> str:
        """
        Get default hazardous materials information.
        
        Args:
            category: Normalized device category
            device_type: Device type/sub-category
            
        Returns:
            Default hazardous materials information
        """
        category_lower = category.lower()
        device_type_lower = device_type.lower()
        
        # Check for CRT
        if self._is_crt_display(device_type):
            return "Contains lead and mercury in CRT tube - requires specialized disposal"
        
        # Check for lithium battery devices
        if self._has_lithium_battery(category, device_type):
            return "Contains lithium-ion battery - fire risk if damaged, requires proper recycling"
        
        # Battery category
        if "battery" in category_lower:
            return "Battery contains hazardous chemicals - must not be disposed in regular trash"
        
        # Appliances and other electronics
        if "appliance" in category_lower:
            return "May contain hazardous materials in components - requires e-waste recycling"
        
        return "Contains electronic components that require proper e-waste disposal"
    
    
    def _is_device(self, gemini_result: dict) -> bool:
        """
        Check if the analyzed image contains an electronic device.

        With the grounded two-pass approach, Gemini returns exact DB category
        names or "NEW:<name>". We only reject the image when confidence is
        very low (Gemini itself signals it cannot identify an electronic device).

        Args:
            gemini_result: Pass-1 result dict

        Returns:
            True if it's a device, False otherwise
        """
        category = gemini_result.get("category", "").lower().strip()
        confidence = gemini_result.get("confidenceScore", 0.0)

        # Definitely not a device
        if category == "other" and confidence < 0.3:
            return False

        # Gemini returned very low confidence – trust that signal
        if confidence < 0.2:
            return False

        return True


# Global analyzer instance
analyzer_service = AnalyzerService()
