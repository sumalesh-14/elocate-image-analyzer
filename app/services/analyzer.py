"""
Analyzer orchestration service.

This module orchestrates the device identification workflow:
1. Validates images using the image_validator service
2. Analyzes validated images using the gemini_service
3. Normalizes categories to standard values
4. Applies confidence-based logic for uncertain fields
5. Handles temporary files with automatic cleanup
6. Logs all analysis requests
"""

import tempfile
import os
import logging
from typing import Optional
from fastapi import UploadFile

from app.services.image_validator import validate_image, ValidationResult
from app.services.gemini_service import gemini_service, GeminiAPIError
from app.services.database_matcher import database_matcher
from app.models.response import DeviceData, ErrorData


# Configure logger
logger = logging.getLogger(__name__)


# Category normalization mapping
CATEGORY_MAPPING = {
    "mobile": "Mobile Phone",
    "smartphone": "Mobile Phone",
    "phone": "Mobile Phone",
    "laptop": "Laptop",
    "notebook": "Laptop",
    "tablet": "Tablet",
    "charger": "Charger",
    "adapter": "Charger",
    "battery": "Battery",
    "cable": "Cable",
    "wire": "Cable",
    "appliance": "Appliance",
    "accessory": "Accessory",
    "other": "Other"
}


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
        Orchestrate the complete device analysis workflow.
        
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
            
            # Log analysis request
            logger.info(
                "Image analysis request received",
                extra={
                    "upload_filename": file.filename,
                    "file_size": len(file_bytes),
                    "content_type": file.content_type
                }
            )
            
            # Validate image
            validation_result = validate_image(file_bytes, file.filename)
            if not validation_result.is_valid:
                logger.warning(
                    "Image validation failed",
                    extra={
                        "filename": file.filename,
                        "error_code": validation_result.error_code,
                        "error_message": validation_result.message
                    }
                )
                raise AnalysisError(
                    validation_result.error_code,
                    validation_result.message
                )
            
            # Save to temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(file_bytes)
            
            # Analyze with Gemini
            try:
                gemini_result = await gemini_service.analyze_device_image(file_bytes)
            except TimeoutError as e:
                logger.error(
                    "Gemini API timeout",
                    extra={"filename": file.filename, "error": str(e)}
                )
                raise AnalysisError("ANALYSIS_TIMEOUT", str(e))
            except GeminiAPIError as e:
                logger.error(
                    "Gemini API error",
                    extra={"filename": file.filename, "error": str(e)}
                )
                raise AnalysisError("SERVICE_UNAVAILABLE", str(e))
            except Exception as e:
                logger.error(
                    "Unexpected error during Gemini analysis",
                    extra={"filename": file.filename, "error": str(e)},
                    exc_info=True
                )
                raise AnalysisError("INTERNAL_ERROR", "An unexpected error occurred during analysis")
            
            # Check if it's a device
            if not self._is_device(gemini_result):
                logger.warning(
                    "Non-device image detected",
                    extra={"filename": file.filename, "category": gemini_result.get("category")}
                )
                raise AnalysisError(
                    "NOT_A_DEVICE",
                    "Image does not appear to contain an electronic device"
                )
            
            # Normalize category
            normalized_category = self._normalize_category(gemini_result.get("category", "other"))
            
            # Calculate confidence score
            confidence = self._calculate_confidence(gemini_result)
            
            # Apply uncertainty logic for brand and model
            brand = self._apply_uncertainty_logic(
                gemini_result.get("brand"),
                confidence
            )
            model = self._apply_uncertainty_logic(
                gemini_result.get("model"),
                confidence
            )
            
            # Sanitize attributes to ensure all values are strings
            sanitized_attributes = self._sanitize_attributes(
                gemini_result.get("attributes", {})
            )
            
            # Process enhanced fields with validation and defaults
            enhanced_fields = self._process_enhanced_fields(
                gemini_result,
                normalized_category,
                gemini_result.get("deviceType", "unknown")
            )
            
            # Match device against database
            database_match_fields = await self._match_device_in_database(
                normalized_category,
                brand,
                model
            )
            
            # Create device data with enhanced fields and database matches
            device_data = DeviceData(
                category=normalized_category,
                brand=brand,
                model=model,
                deviceType=gemini_result.get("deviceType", "unknown"),
                confidenceScore=confidence,
                accuracy=confidence,  # accuracy equals confidenceScore
                attributes=sanitized_attributes,
                lowConfidence=confidence < 0.5,
                **enhanced_fields,  # Unpack enhanced fields
                **database_match_fields  # Unpack database matching fields
            )
            
            # Log successful analysis
            logger.info(
                "Analysis completed successfully",
                extra={
                    "upload_filename": file.filename,
                    "category": device_data.category,
                    "brand": device_data.brand,
                    "model": device_data.model,
                    "confidence": device_data.confidenceScore,
                    "lowConfidence": device_data.lowConfidence
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
    
    def _normalize_category(self, raw_category: str) -> str:
        """
        Normalize Gemini category output to database-compatible format.
        
        Args:
            raw_category: Raw category string from Gemini
            
        Returns:
            Normalized category name
        """
        normalized = CATEGORY_MAPPING.get(raw_category.lower(), raw_category)
        logger.debug(f"Normalized category '{raw_category}' to '{normalized}'")
        return normalized
    
    def _calculate_confidence(self, gemini_result: dict) -> float:
        """
        Calculate overall confidence score from Gemini response.
        
        The confidence score is based on:
        - Gemini's reported confidence
        - Presence of brand and model information
        - Quality of attributes
        
        Args:
            gemini_result: Raw result from Gemini API
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with Gemini's confidence
        base_confidence = gemini_result.get("confidenceScore", 0.5)
        
        # Adjust based on available information
        adjustments = 0.0
        
        # Penalize if brand is missing or null
        if not gemini_result.get("brand"):
            adjustments -= 0.1
        
        # Penalize if model is missing or null
        if not gemini_result.get("model"):
            adjustments -= 0.1
        
        # Bonus if attributes are rich (more than 2 attributes)
        attributes = gemini_result.get("attributes", {})
        if len(attributes) > 2:
            adjustments += 0.05
        
        # Calculate final confidence
        final_confidence = max(0.0, min(1.0, base_confidence + adjustments))
        
        logger.debug(
            f"Confidence calculation: base={base_confidence}, "
            f"adjustments={adjustments}, final={final_confidence}"
        )
        
        return final_confidence
    
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
    
    async def _match_device_in_database(
        self,
        category: str,
        brand: Optional[str],
        model: Optional[str]
    ) -> dict:
        """
        Match device information against database and return matching fields.
        
        Calls the database matcher service to find UUIDs for category, brand, and model.
        Handles database unavailability gracefully by returning null values.
        Preserves original text fields from Gemini.
        
        Args:
            category: Normalized category text from Gemini
            brand: Brand text from Gemini (may be None)
            model: Model text from Gemini (may be None)
        
        Returns:
            Dictionary with database matching fields:
            - category_id, brand_id, model_id (UUIDs or None)
            - category_match_score, brand_match_score, model_match_score (floats or None)
            - database_status (success, partial_success, failure, unavailable)
        """
        try:
            # Call database matcher service
            device_match = await database_matcher.match_device(
                category_text=category,
                brand_text=brand,
                model_text=model
            )
            
            # Extract UUIDs and scores from match results
            category_id = device_match.category.id if device_match.category else None
            brand_id = device_match.brand.id if device_match.brand else None
            model_id = device_match.model.id if device_match.model else None
            
            category_match_score = device_match.category.similarity_score if device_match.category else None
            brand_match_score = device_match.brand.similarity_score if device_match.brand else None
            model_match_score = device_match.model.similarity_score if device_match.model else None
            
            # Log database matching results
            logger.info(
                "Database matching completed",
                extra={
                    "category_id": str(category_id) if category_id else None,
                    "brand_id": str(brand_id) if brand_id else None,
                    "model_id": str(model_id) if model_id else None,
                    "category_score": category_match_score,
                    "brand_score": brand_match_score,
                    "model_score": model_match_score,
                    "database_status": device_match.database_status
                }
            )
            
            return {
                "category_id": category_id,
                "brand_id": brand_id,
                "model_id": model_id,
                "category_match_score": category_match_score,
                "brand_match_score": brand_match_score,
                "model_match_score": model_match_score,
                "database_status": device_match.database_status
            }
        
        except Exception as e:
            # Graceful degradation: log error and return null values
            logger.error(
                f"Database matching failed with unexpected error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            return {
                "category_id": None,
                "brand_id": None,
                "model_id": None,
                "category_match_score": None,
                "brand_match_score": None,
                "model_match_score": None,
                "database_status": "failure"
            }
    
    def _is_device(self, gemini_result: dict) -> bool:
        """
        Check if the analyzed image contains an electronic device.
        
        Args:
            gemini_result: Raw result from Gemini API
            
        Returns:
            True if it's a device, False otherwise
        """
        category = gemini_result.get("category", "").lower()
        
        # Check if category is valid
        valid_categories = [
            "mobile", "smartphone", "phone",
            "laptop", "notebook",
            "tablet",
            "charger", "adapter",
            "battery",
            "cable", "wire",
            "appliance",
            "accessory"
        ]
        
        # If category is "other" or not in valid categories, it might not be a device
        if category == "other" or category not in valid_categories:
            # Check confidence - if very low, likely not a device
            confidence = gemini_result.get("confidenceScore", 0.0)
            if confidence < 0.3:
                return False
        
        return True


# Global analyzer instance
analyzer_service = AnalyzerService()
