"""
Gemini Vision API integration service.
Handles communication with Google's Gemini Vision API for device image analysis.
"""

import logging
import json
import io
import time
import asyncio
from typing import Dict, Any, Optional
from PIL import Image
import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


# Prompt for Gemini Vision API
DEVICE_ANALYSIS_PROMPT = """
Analyze this image of an electronic device and extract the following information in JSON format:

1. category: The primary device category. Choose from: mobile, laptop, tablet, charger, battery, cable, appliance, accessory, other
2. brand: The brand name visible on the device. Return null if not clearly visible or uncertain.
3. model: The specific model name or number. Return null if not clearly visible or uncertain.
4. deviceType: A more specific device type or sub-category (e.g., "smartphone", "laptop charger", "lithium-ion battery")
5. attributes: An object containing visible characteristics such as:
   - color
   - condition (new, good, fair, poor)
   - visiblePorts (USB-C, Lightning, HDMI, etc.)
   - screenSize (if applicable)
   - visibleMarkings (any text, logos, or identifiers)
   - physicalDamage (if any)
6. confidenceScore: Your confidence in this identification from 0.0 to 1.0
7. info_note: Contextual information about the device relevant to recycling (max 500 characters). Include notable characteristics, recycling tips, or special handling requirements.
8. severity: Disposal risk severity level. Choose from: "low", "medium", "high", "critical"
   - "low": Minimal environmental impact if disposed improperly (e.g., simple cables, basic accessories)
   - "medium": Moderate environmental concern (e.g., small electronics without batteries)
   - "high": Significant environmental or health risk (e.g., devices with lithium-ion batteries like smartphones, laptops, tablets)
   - "critical": Severe danger if disposed improperly (e.g., CRT displays/monitors/TVs, large batteries, devices with mercury)
9. contains_precious_metals: Boolean indicating if the device contains valuable metals (gold, silver, palladium, copper)
10. precious_metals_info: Details about precious metal content (max 300 characters). Only provide if contains_precious_metals is true.
11. contains_hazardous_materials: Boolean indicating if the device contains dangerous substances (batteries, mercury, lead, cadmium)
12. hazardous_materials_info: Details about hazardous materials and associated risks (max 300 characters). Only provide if contains_hazardous_materials is true.

IMPORTANT RULES FOR BASIC IDENTIFICATION:
- If you cannot clearly see the brand name, set brand to null
- If you cannot clearly see the model name, set model to null
- Do not guess or fabricate information
- Be conservative with confidence scores
- If this is not an electronic device, return an error

IMPORTANT RULES FOR PRECIOUS METALS IDENTIFICATION:
- Circuit boards typically contain gold, silver, palladium, and copper
- Devices with visible circuit boards should have contains_precious_metals set to true
- Connectors, pins, and contacts often contain gold plating
- Larger devices generally contain more precious metals

IMPORTANT RULES FOR HAZARDOUS MATERIALS IDENTIFICATION:
- ALL batteries (lithium-ion, lithium-polymer, NiMH, alkaline) are hazardous
- Smartphones, laptops, tablets, and portable devices contain lithium batteries
- CRT displays contain lead and mercury
- Power supplies and displays may contain hazardous components
- Batteries pose fire risk and should be flagged as hazardous

IMPORTANT RULES FOR SEVERITY ASSESSMENT:
- ALWAYS set severity to "critical" for CRT displays, monitors, or TVs
- ALWAYS set severity to at least "high" for devices with lithium-ion batteries (smartphones, laptops, tablets, power banks)
- Devices with both batteries and circuit boards should be "high" severity minimum
- Simple accessories without batteries or hazardous materials can be "low" or "medium"

SEVERITY EXAMPLES:
- Smartphone: "high" or "critical" (lithium battery + fire risk)
- Laptop: "high" or "critical" (lithium battery + precious metals)
- Tablet: "high" (lithium battery)
- CRT Monitor/TV: "critical" (lead, mercury, implosion risk)
- Power bank: "high" or "critical" (large lithium battery)
- USB cable: "low" (minimal risk)
- Charger without battery: "medium" (electronic components)
- Battery (standalone): "high" or "critical" (fire/chemical risk)

Return ONLY valid JSON in this exact format:
{
  "category": "string",
  "brand": "string or null",
  "model": "string or null",
  "deviceType": "string",
  "confidenceScore": 0.0-1.0,
  "attributes": {},
  "info_note": "string or null",
  "severity": "low|medium|high|critical",
  "contains_precious_metals": true|false,
  "precious_metals_info": "string or null",
  "contains_hazardous_materials": true|false,
  "hazardous_materials_info": "string or null"
}
"""


class GeminiAPIError(Exception):
    """Exception raised for Gemini API errors."""
    pass


class GeminiService:
    """Service for interacting with Google's Gemini Vision API."""
    
    def __init__(self):
        """Initialize the Gemini API client."""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Try to list available models to pick the best supported one
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                logger.info(f"Available Gemini models: {available_models}")
                
                if 'models/gemini-1.5-flash' in available_models:
                    self.model_name = 'gemini-1.5-flash'
                elif 'models/gemini-1.5-flash-latest' in available_models:
                    self.model_name = 'gemini-1.5-flash-latest'
                elif 'models/gemini-pro-vision' in available_models:
                    self.model_name = 'gemini-pro-vision'
                else:
                    # Fallback to 1.5-flash if listing fails or none of the above are found
                    self.model_name = 'gemini-1.5-flash'
            except Exception as list_err:
                logger.warning(f"Could not list models: {str(list_err)}. Defaulting to gemini-1.5-flash")
                self.model_name = 'gemini-1.5-flash'
            
            logger.info(f"Using Gemini model: {self.model_name}")
            self.model = genai.GenerativeModel(self.model_name)
        except Exception as e:
            raise GeminiAPIError(f"Failed to initialize Gemini API: {str(e)}")
    
    async def analyze_device_image(
        self, 
        image_bytes: bytes,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze a device image using Gemini Vision API.
        
        Args:
            image_bytes: Raw image bytes
            max_retries: Maximum number of retry attempts for transient failures
            
        Returns:
            Dictionary containing device attributes extracted from the image
            
        Raises:
            GeminiAPIError: If API is unavailable or returns invalid response
            TimeoutError: If API call exceeds timeout
            ValueError: If response is not valid JSON
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Convert bytes to PIL Image
                image = Image.open(io.BytesIO(image_bytes))
                
                # Generate content with Gemini (with timeout)
                response = await asyncio.wait_for(
                    self._generate_content(image),
                    timeout=settings.REQUEST_TIMEOUT
                )
                
                # Parse JSON response
                result = self._parse_response(response.text)
                
                # Validate the response structure
                self._validate_response(result)
                
                return result
                
            except asyncio.TimeoutError:
                raise TimeoutError(f"Gemini API request timed out after {settings.REQUEST_TIMEOUT} seconds")
            
            except json.JSONDecodeError as e:
                last_error = ValueError(f"Gemini returned invalid JSON: {str(e)}")
                # Retry on JSON decode errors (might be transient)
                if attempt < max_retries - 1:
                    await self._exponential_backoff(attempt)
                    continue
                raise last_error
            
            except Exception as e:
                # Check if it's a transient error that should be retried
                if self._is_transient_error(e):
                    last_error = e
                    if attempt < max_retries - 1:
                        await self._exponential_backoff(attempt)
                        continue
                
                # Non-transient error, raise immediately
                raise GeminiAPIError(f"Gemini API error: {str(e)}")
        
        # If we exhausted all retries
        if last_error:
            raise GeminiAPIError(f"Gemini API failed after {max_retries} attempts: {str(last_error)}")
    
    async def _generate_content(self, image: Image.Image):
        """
        Generate content using Gemini API (async wrapper).
        
        Args:
            image: PIL Image object
            
        Returns:
            Gemini API response
        """
        # Run the synchronous API call in a thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content([DEVICE_ANALYSIS_PROMPT, image])
        )
        return response
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini response text into JSON.
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Try to extract JSON from response (Gemini might include markdown)
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        elif text.startswith("```"):
            text = text[3:]  # Remove ```
        
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        
        text = text.strip()
        
        # Parse JSON
        return json.loads(text)
    
    def _validate_response(self, result: Dict[str, Any]) -> None:
        """
        Validate that the response contains required fields.
        
        Args:
            result: Parsed response dictionary
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_fields = [
            'category', 'brand', 'model', 'deviceType', 'confidenceScore', 'attributes',
            'severity', 'contains_precious_metals', 'contains_hazardous_materials'
        ]
        
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field in Gemini response: {field}")
        
        # Validate confidence score range
        confidence = result.get('confidenceScore')
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Invalid confidence score: {confidence}. Must be between 0.0 and 1.0")
        
        # Validate attributes is a dictionary
        if not isinstance(result.get('attributes'), dict):
            raise ValueError("Attributes field must be a dictionary")
        
        # Validate severity is one of the allowed values
        severity = result.get('severity')
        allowed_severities = ['low', 'medium', 'high', 'critical']
        if severity not in allowed_severities:
            raise ValueError(f"Invalid severity: {severity}. Must be one of {allowed_severities}")
        
        # Validate boolean fields
        if not isinstance(result.get('contains_precious_metals'), bool):
            raise ValueError("contains_precious_metals must be a boolean")
        
        if not isinstance(result.get('contains_hazardous_materials'), bool):
            raise ValueError("contains_hazardous_materials must be a boolean")
    
    def _is_transient_error(self, error: Exception) -> bool:
        """
        Determine if an error is transient and should be retried.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if error is transient, False otherwise
        """
        error_str = str(error).lower()
        
        # Common transient error patterns
        transient_patterns = [
            'timeout',
            'connection',
            'network',
            'temporary',
            'unavailable',
            'rate limit',
            '429',
            '500',
            '502',
            '503',
            '504'
        ]
        
        return any(pattern in error_str for pattern in transient_patterns)
    
    async def _exponential_backoff(self, attempt: int) -> None:
        """
        Wait with exponential backoff before retrying.
        
        Args:
            attempt: Current attempt number (0-indexed)
        """
        # Exponential backoff: 1s, 2s, 4s, etc.
        wait_time = 2 ** attempt
        await asyncio.sleep(wait_time)
    
    async def check_api_availability(self) -> bool:
        """
        Check if Gemini API is available.
        
        Returns:
            True if API is available, False otherwise
        """
        try:
            # Try a simple API call with a minimal prompt
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content("test")
            )
            return True
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Gemini API availability check failed: {str(e)}", exc_info=True)
            return False
    
    async def check_availability(self) -> bool:
        """
        Check if Gemini API is available (alias for check_api_availability).
        
        Returns:
            True if API is available, False otherwise
        """
        return await self.check_api_availability()


# Global service instance
gemini_service = GeminiService()
