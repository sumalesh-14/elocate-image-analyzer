"""
Gemini Vision API integration service.

Two-pass grounded analysis:
  Pass 1 – Category identification using the exact list from DB.
  Pass 2 – Brand + model + all other device attributes using the
            brand list filtered by the matched category.

Gemini signals "NEW:<name>" when a value is not in the provided list,
allowing the auto-seed pipeline in DatabaseMatcher to insert new records.
"""

import logging
import json
import io
import asyncio
from typing import Dict, Any, List, Optional
from PIL import Image
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pass-1 prompt template – category only
# ---------------------------------------------------------------------------

PASS1_CATEGORY_PROMPT_TEMPLATE = """
You are analyzing an image of an electronic device for an e-waste recycling system.

AVAILABLE CATEGORIES (from our database):
{category_list}

TASK:
- Identify the device category from the image.
- If the device EXACTLY matches one of the categories above, return that exact name.
- If the device does NOT match any category above, return "NEW: <your category name>".
  Use short, clean category names (e.g. "NEW: Pen Drive", "NEW: Smart Watch").

Return ONLY valid JSON – no markdown fences:
{{
  "category": "<exact category name from the list, OR NEW: <name>>",
  "deviceType": "<specific device type, e.g. USB Flash Drive, Android Smartphone>",
  "confidenceScore": <0.0 to 1.0>
}}

RULES:
- If you cannot identify the device at all, set category to "other" and confidenceScore below 0.3.
- Do NOT guess. If uncertain, lower the confidenceScore.
- Return ONLY the JSON object, nothing else.
"""

# ---------------------------------------------------------------------------
# Pass-2 prompt template – brand, model, and all other fields
# ---------------------------------------------------------------------------

PASS2_BRAND_MODEL_PROMPT_TEMPLATE = """
You are analyzing an image of a {category} for an e-waste recycling system.

AVAILABLE BRANDS for {category} (from our database):
{brand_list}

AVAILABLE MODELS for the identified brand (from our database):
{model_list}

TASK:
1. BRAND: Pick the brand from the list above, or return "NEW: <brand>" if not in the list.
   Return null if the brand is not visible in the image.

2. MODEL: Examine the image carefully and identify the model using visual features.
   - For iPhones, the camera module shape is the most reliable differentiator:
     * PILL/CAPSULE shaped elongated housing with 2 vertical lenses = iPhone 16 / 16 Plus
     * Two SEPARATE CIRCULAR lens bumps (not in a pill) + Dynamic Island + USB-C = iPhone 15 / 15 Plus
     * Two SEPARATE CIRCULAR lens bumps + NOTCH + Lightning = iPhone 14 / 14 Plus
     * DIAGONAL dual-camera in square bump + notch = iPhone 13 / 13 mini
     * THREE lenses + large square bump + LiDAR + Dynamic Island + USB-C = iPhone 15 Pro or 16 Pro
     * THREE lenses + large square bump + LiDAR + Dynamic Island + Lightning = iPhone 14 Pro
     * Camera Control button (extra thin button on right side) = iPhone 16 series ONLY
   - Pick the model from the models list above, or return "NEW: <model>" if not found.
   - Return null only if the model is genuinely not determinable.

3. Fill in all other fields accurately from the image.

Return ONLY valid JSON – no markdown fences:
{{
  "brand": "<exact brand name from list, OR NEW: <name>, OR null>",
  "model": "<exact model name from list, OR NEW: <name>, OR null>",
  "attributes": {{
    "color": "<color>",
    "condition": "<new|good|fair|poor>",
    "visiblePorts": "<USB-C, Lightning, HDMI, etc.>",
    "screenSize": "<if applicable>",
    "visibleMarkings": "<any text, logos, or identifiers>",
    "physicalDamage": "<if any>"
  }},
  "info_note": "<contextual info about this device relevant to recycling, max 500 chars>",
  "severity": "<low|medium|high|critical>",
  "contains_precious_metals": <true|false>,
  "precious_metals_info": "<details about precious metal content, max 300 chars, or null>",
  "contains_hazardous_materials": <true|false>,
  "hazardous_materials_info": "<details about hazardous materials, max 300 chars, or null>"
}}

SEVERITY RULES:
- "critical" → CRT displays, monitors, TVs, large batteries with mercury
- "high" → any device with lithium-ion battery (smartphones, laptops, tablets, power banks)
- "medium" → small electronics without batteries
- "low" → simple cables, basic accessories

PRECIOUS METALS:
- Circuit boards typically contain gold, silver, palladium, copper.

HAZARDOUS MATERIALS:
- ALL batteries are hazardous. CRTs contain lead and mercury.

Return ONLY the JSON object, nothing else.
"""

# ---------------------------------------------------------------------------
# Pass-3 prompt template – model identification only (lightweight)
# ---------------------------------------------------------------------------

PASS3_MODEL_PROMPT_TEMPLATE = """
You are a visual device identification expert analyzing an image for an e-waste recycling system.

Your job: identify the exact model of the {brand} {category} shown in the image.

AVAILABLE MODELS for {brand} {category} (from our database):
{model_list}

INSTRUCTIONS:
1. Look at the image carefully and identify the device model based on its visual appearance.
2. Use your knowledge of {brand} product design history — camera layout, port types, frame design, front cutout style, button placement, and any visible text or markings.
3. A previous analysis suggested "{pass2_model}" — treat this as a low-weight hint only. Trust your visual analysis over it.
4. If the model matches one in the AVAILABLE MODELS list, return that exact name.
5. If you can clearly identify the model but it is NOT in the list, return "NEW: <model name>".
6. Only return null if the model is genuinely impossible to determine from the image.

Return ONLY valid JSON – no markdown fences:
{{
  "model": "<exact model from list, OR NEW: <name>, OR null>",
  "confidence": "<high|medium|low>",
  "uncertainty_reason": "<brief reason if confidence is not high, else null>",
  "visual_evidence": "<what specific visual features led to this identification>",
  "recycle_items": [
    {{
      "type": "<material name, e.g., gold>",
      "grams": <number>,
      "market_price": "<estimated price in Indian Rupees>",
      "is_precious": <boolean>
    }}
  ]
}}

Return ONLY the JSON object, nothing else.
"""

class GeminiAPIError(Exception):
    """Exception raised for Gemini API errors."""
    pass


class GeminiService:
    """Service for interacting with Google's Gemini Vision API."""

    def __init__(self):
        """Initialize the Gemini API client."""
        try:
            self.api_keys = settings.gemini_api_keys_list
            if not self.api_keys or not self.api_keys[0]:
                raise ValueError("No Gemini API keys configured")
                
            self.current_key_idx = 0
            self.client = genai.Client(api_key=self.api_keys[self.current_key_idx])
            self.model_name = 'gemini-2.5-flash'
            logger.info(f"GeminiService initialized with model: {self.model_name} and {len(self.api_keys)} API keys")
        except Exception as e:
            raise GeminiAPIError(f"Failed to initialize Gemini API: {str(e)}")

    def _rotate_api_key(self) -> None:
        """Rotate to the next API key in the list."""
        if len(self.api_keys) <= 1:
            return
            
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        logger.warning(f"Rotating to Gemini API key #{self.current_key_idx + 1}")
        self.client = genai.Client(api_key=self.api_keys[self.current_key_idx])

    # -----------------------------------------------------------------------
    # Public: three-pass analysis entry-points
    # -----------------------------------------------------------------------

    async def analyze_pass1_category(
        self,
        image_bytes: bytes,
        categories: List[dict],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Pass 1 – identify category, deviceType, and confidenceScore.

        Args:
            image_bytes: Raw image bytes
            categories: List of {"id", "name"} dicts from DB to include in prompt
            max_retries: Retry count for transient failures

        Returns:
            Dict with keys: category, deviceType, confidenceScore

        Raises:
            GeminiAPIError, TimeoutError, ValueError
        """
        if categories:
            category_list = "\n".join(
                f"  - {c['name']}" for c in categories
            )
        else:
            # Fallback list if DB unavailable
            category_list = (
                "  - Mobile Phone\n  - Laptop\n  - Tablet\n  - Charger\n"
                "  - Battery\n  - Cable\n  - Appliance\n  - Accessory"
            )

        prompt = PASS1_CATEGORY_PROMPT_TEMPLATE.format(
            category_list=category_list
        )

        logger.debug(
            f"Pass-1 prompt: {len(categories)} categories offered to Gemini"
        )

        result = await self._call_gemini_with_retry(image_bytes, prompt, max_retries)
        self._validate_pass1_response(result)
        return result

    async def analyze_pass2_brand_model(
        self,
        image_bytes: bytes,
        category: str,
        brands: List[dict],
        models: List[dict],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Pass 2 – identify brand, model, and all device metadata.

        Args:
            image_bytes: Raw image bytes (same image as Pass 1)
            category: The resolved category name (from Pass 1)
            brands: List of {"id", "name"} dicts for brands under this category
            models: List of {"id", "name"} dicts for models (may be empty if brand is new)
            max_retries: Retry count for transient failures

        Returns:
            Dict with keys: brand, model, attributes, severity, info_note,
                            contains_precious_metals, precious_metals_info,
                            contains_hazardous_materials, hazardous_materials_info

        Raises:
            GeminiAPIError, TimeoutError, ValueError
        """
        if brands:
            brand_list = "\n".join(f"  - {b['name']}" for b in brands)
        else:
            brand_list = "  (No brands in database yet for this category – use NEW: <brand> if visible)"

        if models:
            model_list = "\n".join(f"  - {m['name']}" for m in models)
        else:
            model_list = "  (No models in database yet – use NEW: <model> if visible)"

        prompt = PASS2_BRAND_MODEL_PROMPT_TEMPLATE.format(
            category=category,
            brand_list=brand_list,
            model_list=model_list,
        )

        logger.debug(
            f"Pass-2 prompt: {len(brands)} brands, {len(models)} models offered to Gemini"
        )

        result = await self._call_gemini_with_retry(image_bytes, prompt, max_retries)
        self._validate_pass2_response(result)
        return result

    async def analyze_pass3_model(
        self,
        image_bytes: bytes,
        category: str,
        brand: str,
        models: List[dict],
        pass2_model: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Pass 3 – identify exact model from filtered list.

        Args:
            image_bytes: Raw image bytes
            category: The resolved category name
            brand: The resolved brand name
            models: List of {"id", "name"} dicts for models under this brand+category
            pass2_model: Fallback model identified in pass 2 context
            max_retries: Retry count for transient failures

        Returns:
            Dict with key: model
        """
        if models:
            model_list = "\n".join(f"  - {m['name']}" for m in models)
        else:
            model_list = "  (No models in database yet for this brand – use NEW: <model> if identifiable)"

        prompt = PASS3_MODEL_PROMPT_TEMPLATE.format(
            category=category,
            brand=brand,
            model_list=model_list,
            pass2_model=pass2_model or "Unknown",
        )


        logger.debug(f"Pass-3 prompt: {len(models)} models offered to Gemini for {brand}")

        result = await self._call_gemini_with_retry(image_bytes, prompt, max_retries)
        # Validation is simple for pass 3 as we just extract the model
        if not isinstance(result, dict) or "model" not in result:
             result = {"model": result.get("model") if isinstance(result, dict) else None}
        return result

    # -----------------------------------------------------------------------
    # Legacy entry-point (kept for any existing callers)
    # -----------------------------------------------------------------------

    async def analyze_device_image(
        self,
        image_bytes: bytes,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Legacy single-pass analysis.

        NOTE: This is kept for backward compatibility but is no longer called
        by the main analyzer flow. Use analyze_pass1_category() /
        analyze_pass2_brand_model() instead.
        """
        from app.services.database_matcher import database_matcher

        categories = await database_matcher.get_all_categories()

        # Pass 1
        pass1 = await self.analyze_pass1_category(image_bytes, categories, max_retries)

        # Merge into a combined result that mimics the old single-pass format
        combined = {
            "category": pass1.get("category", "other"),
            "deviceType": pass1.get("deviceType", "unknown"),
            "confidenceScore": pass1.get("confidenceScore", 0.5),
            "brand": None,
            "model": None,
            "attributes": {},
            "info_note": None,
            "severity": "medium",
            "contains_precious_metals": False,
            "precious_metals_info": None,
            "contains_hazardous_materials": False,
            "hazardous_materials_info": None,
        }
        return combined

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _call_gemini_with_retry(
        self,
        image_bytes: bytes,
        prompt: str,
        max_retries: int,
    ) -> Dict[str, Any]:
        """Send image + prompt to Gemini and return parsed JSON dict."""
        last_error = None

        for attempt in range(max_retries):
            try:
                image = Image.open(io.BytesIO(image_bytes))

                response = await asyncio.wait_for(
                    self._generate_content(image, prompt),
                    timeout=settings.REQUEST_TIMEOUT,
                )

                result = self._parse_response(response.text)
                return result

            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Gemini API request timed out after {settings.REQUEST_TIMEOUT} seconds"
                )

            except json.JSONDecodeError as e:
                last_error = ValueError(f"Gemini returned invalid JSON: {str(e)}")
                if attempt < max_retries - 1:
                    await self._exponential_backoff(attempt)
                    continue
                raise last_error

            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limits specifically to rotate keys
                if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
                    logger.warning(f"Hit Gemini API rate limit on key #{self.current_key_idx + 1}")
                    if len(self.api_keys) > 1:
                        self._rotate_api_key()
                        
                if self._is_transient_error(e):
                    last_error = e
                    if attempt < max_retries - 1:
                        await self._exponential_backoff(attempt)
                        continue
                raise GeminiAPIError(f"Gemini API error: {str(e)}")

        if last_error:
            raise GeminiAPIError(
                f"Gemini API failed after {max_retries} attempts: {str(last_error)}"
            )

    async def _generate_content(self, image: Image.Image, prompt: str):
        """Generate content using Gemini API SDK (async wrapper)."""
        loop = asyncio.get_event_loop()

        img_bytes = io.BytesIO()
        fmt = image.format if image.format else 'JPEG'
        image.save(img_bytes, format=fmt)
        img_bytes.seek(0)
        raw_bytes = img_bytes.read()
        mime = f"image/{fmt.lower()}"

        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=raw_bytes, mime_type=mime),
                    prompt,
                ]
            )
        )
        return response

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response text into JSON."""
        text = response_text.strip()

        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        return json.loads(text.strip())

    def _validate_pass1_response(self, result: Dict[str, Any]) -> None:
        """Validate Pass-1 response structure."""
        for field in ["category", "deviceType", "confidenceScore"]:
            if field not in result:
                raise ValueError(f"Missing required field in Pass-1 response: {field}")

        confidence = result.get("confidenceScore")
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"Invalid confidenceScore in Pass-1: {confidence}"
            )

    def _validate_pass2_response(self, result: Dict[str, Any]) -> None:
        """Validate Pass-2 response structure."""
        required = [
            "brand", "model", "attributes",
            "severity", "contains_precious_metals", "contains_hazardous_materials"
        ]
        for field in required:
            if field not in result:
                raise ValueError(f"Missing required field in Pass-2 response: {field}")

        severity = result.get("severity")
        if severity not in ["low", "medium", "high", "critical"]:
            raise ValueError(f"Invalid severity in Pass-2: {severity}")

        if not isinstance(result.get("contains_precious_metals"), bool):
            raise ValueError("contains_precious_metals must be a boolean")

        if not isinstance(result.get("contains_hazardous_materials"), bool):
            raise ValueError("contains_hazardous_materials must be a boolean")

        if not isinstance(result.get("attributes"), dict):
            result["attributes"] = {}

    def _is_transient_error(self, error: Exception) -> bool:
        """Determine if an error is transient and should be retried."""
        error_str = str(error).lower()
        transient_patterns = [
            'timeout', 'connection', 'network', 'temporary',
            'unavailable', 'rate limit', '429', '500', '502', '503', '504'
        ]
        return any(pattern in error_str for pattern in transient_patterns)

    async def _exponential_backoff(self, attempt: int) -> None:
        """Wait with exponential backoff before retrying."""
        wait_time = 2 ** attempt
        await asyncio.sleep(wait_time)

    async def check_api_availability(self) -> bool:
        """Check if Gemini API is available."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents="test"
                )
            )
            return True
        except Exception as e:
            logger.error(f"Gemini API availability check failed: {str(e)}", exc_info=True)
            return False

    async def check_availability(self) -> bool:
        """Alias for check_api_availability."""
        return await self.check_api_availability()


# Global service instance
gemini_service = GeminiService()
