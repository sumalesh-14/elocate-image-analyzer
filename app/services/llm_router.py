import logging
import json
import io
import asyncio
import base64
from typing import Dict, Any, List, Optional
from PIL import Image

# LLM Providers
from google import genai
from google.genai import types
import openai
import groq

from app.config import settings
from app.utils.orchestration_log import log_llm_attempt, log_llm_switched

logger = logging.getLogger(__name__)

# --- Prompt Templates ---
# Re-use the existing prompts from gemini_service.py
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

PASS2_BRAND_MODEL_PROMPT_TEMPLATE = """
You are analyzing an image of a {category} for an e-waste recycling system.

AVAILABLE BRANDS for {category} (from our database):
{brand_list}

AVAILABLE MODELS for the identified brand (from our database):
{model_list}

TASK:
1. BRAND: Pick the brand from the list above, or return "NEW: <brand>" if not in the list.
   Return null if the brand is not visible in the image.

2. MODEL: Pick the model from the models list above, or return "NEW: <model>" if not found.
   Return null if not clearly visible.

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
- "critical" -> CRT displays, monitors, TVs, large batteries with mercury
- "high" -> any device with lithium-ion battery (smartphones, laptops, tablets, power banks)
- "medium" -> small electronics without batteries
- "low" -> simple cables, basic accessories

PRECIOUS METALS:
- Circuit boards typically contain gold, silver, palladium, copper.

HAZARDOUS MATERIALS:
- ALL batteries are hazardous. CRTs contain lead and mercury.

Return ONLY the JSON object, nothing else.
"""

PASS3_MODEL_PROMPT_TEMPLATE = """
You are identifying the exact model of a {brand} {category} for an e-waste recycling system.

PREVIOUS ANALYSIS identified the model as: "{pass2_model}"

AVAILABLE MODELS for {brand} {category} (from our database):
{model_list}

TASK:
- If "{pass2_model}" (or the visually identifiable model) EXACTLY matches or is a close variation of a name in the list above, return that exact name from the list.
- If the model is clearly identifiable (visually or from context) but NOT in the list, return "NEW: <model name>".
- Only return null if you cannot reasonably identify the model at all.
- If you return a NEW model, list down all recycle items that a recycling facility would consider (e.g., gold, silver, lithium battery, copper). Estimate the grams, market price in Indian Rupees, and whether it is precious.

Return ONLY valid JSON – no markdown fences:
{{
  "model": "<exact model from list, OR NEW: <name>, OR null>",
  "recycle_items": [
    {{
      "type": "<material name, e.g., gold>",
      "grams": <number>,
      "market_price": "<estimated price, e.g., 10 in Indian rupees>",
      "is_precious": <boolean>
    }}
  ]
}}

Return ONLY the JSON object, nothing else.
"""

class LLMAPIError(Exception):
    """Exception raised for LLM API errors."""
    pass

class LLMWorker:
    def __init__(self, provider: str, api_key: str, model_name: str, index: int):
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name
        self.display_name = f"{provider.capitalize()} (Key #{index})"
        
        # Initialize clients lazily if possible, or right away
        if self.provider == "gemini":
            self.client = genai.Client(api_key=self.api_key)
        elif self.provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        elif self.provider == "groq":
            self.client = groq.AsyncGroq(api_key=self.api_key)

    async def generate(self, image_bytes: bytes, prompt: str) -> str:
        """Adapter for generating standard responses from varying providers."""
        if self.provider == "gemini":
            return await self._generate_gemini(image_bytes, prompt)
        elif self.provider == "openai":
            return await self._generate_openai(image_bytes, prompt)
        elif self.provider == "groq":
            return await self._generate_groq(image_bytes, prompt)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _generate_gemini(self, image_bytes: bytes, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        image = Image.open(io.BytesIO(image_bytes))
        fmt = image.format if image.format else 'JPEG'
        
        img_io = io.BytesIO()
        image.save(img_io, format=fmt)
        raw_bytes = img_io.getvalue()
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
        return response.text

    def _bytes_to_b64(self, image_bytes: bytes) -> str:
        image = Image.open(io.BytesIO(image_bytes))
        # Compress image for Groq/OpenAI so it doesn't take too long
        fmt = image.format if image.format else 'JPEG'
        img_io = io.BytesIO()
        image.save(img_io, format=fmt)
        return f"data:image/{fmt.lower()};base64,{base64.b64encode(img_io.getvalue()).decode('utf-8')}"

    async def _generate_openai(self, image_bytes: bytes, prompt: str) -> str:
        base64_img = self._bytes_to_b64(image_bytes)
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": base64_img}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    async def _generate_groq(self, image_bytes: bytes, prompt: str) -> str:
        base64_img = self._bytes_to_b64(image_bytes)
        # Check image size? Groq might block large image tokens.
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": base64_img}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

class LLMRouterService:
    """Service for interacting with multiple LLMs in a fallback/router architecture."""

    def __init__(self):
        self.workers: List[LLMWorker] = []
        self.current_idx = 0
        
        # Load API keys
        gemini_keys = settings.gemini_api_keys_list
        openai_keys = settings.openai_api_keys_list
        groq_keys = settings.groq_api_keys_list

        for i, key in enumerate(gemini_keys):
            if key and "your_" not in key:
                self.workers.append(LLMWorker("gemini", key, "gemini-2.5-flash", i+1))
                
        for i, key in enumerate(openai_keys):
            if key and "your_" not in key:
                self.workers.append(LLMWorker("openai", key, "gpt-4o-mini", i+1))
                
        for i, key in enumerate(groq_keys):
            if key and "your_" not in key:
                self.workers.append(LLMWorker("groq", key, "llama-3.2-11b-vision-preview", i+1))
                
        if not self.workers:
            logger.warning("No valid LLM API keys found! System will fail!")
        else:
            logger.info(f"LLMRouterService initialized with {len(self.workers)} workers: {[w.display_name for w in self.workers]}")

    async def _call_llm_with_fallback(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """Iterates through workers until one succeeds."""
        if not self.workers:
            raise LLMAPIError("No active LLM workers available.")
            
        attempts = 0
        max_attempts = len(self.workers)
        
        while attempts < max_attempts:
            worker = self.workers[self.current_idx]
            log_llm_attempt(worker.display_name)
            
            try:
                response_text = await asyncio.wait_for(
                    worker.generate(image_bytes, prompt),
                    timeout=settings.REQUEST_TIMEOUT,
                )
                return self._parse_response(response_text)
                
            except Exception as e:
                error_str = str(e).lower()
                next_idx = (self.current_idx + 1) % len(self.workers)
                next_worker = self.workers[next_idx]
                
                reason = "Rate Limit/Timeout" if "429" in error_str or "timeout" in error_str else "API Error"
                log_llm_switched(worker.display_name, reason, next_worker.display_name)
                
                self.current_idx = next_idx
                attempts += 1
                
        raise LLMAPIError("All LLM workers failed or rate-limited.")

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response text into JSON."""
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    # -----------------------------------------------------------------------
    # Public: three-pass analysis entry-points
    # -----------------------------------------------------------------------
    async def analyze_pass1_category(self, image_bytes: bytes, categories: List[dict]) -> Dict[str, Any]:
        if categories:
            category_list = "\n".join(f"  - {c['name']}" for c in categories)
        else:
            category_list = "  - Mobile Phone\n  - Laptop\n  - Tablet\n  - Charger\n  - Battery\n  - Cable\n  - Appliance\n  - Accessory"

        prompt = PASS1_CATEGORY_PROMPT_TEMPLATE.format(category_list=category_list)
        result = await self._call_llm_with_fallback(image_bytes, prompt)
        
        # Validate
        for field in ["category", "deviceType", "confidenceScore"]:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        return result

    async def analyze_pass2_brand_model(self, image_bytes: bytes, category: str, brands: List[dict], models: List[dict]) -> Dict[str, Any]:
        brand_list = "\n".join(f"  - {b['name']}" for b in brands) if brands else "  (No brands yet)"
        model_list = "\n".join(f"  - {m['name']}" for m in models) if models else "  (No models yet)"

        prompt = PASS2_BRAND_MODEL_PROMPT_TEMPLATE.format(
            category=category,
            brand_list=brand_list,
            model_list=model_list,
        )
        result = await self._call_llm_with_fallback(image_bytes, prompt)
        
        # Validate
        for field in ["brand", "model", "severity"]:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        if not isinstance(result.get("attributes"), dict):
            result["attributes"] = {}
        return result

    async def analyze_pass3_model(self, image_bytes: bytes, category: str, brand: str, models: List[dict], pass2_model: Optional[str] = None) -> Dict[str, Any]:
        model_list = "\n".join(f"  - {m['name']}" for m in models) if models else "  (No models yet)"
        prompt = PASS3_MODEL_PROMPT_TEMPLATE.format(
            category=category,
            brand=brand,
            model_list=model_list,
            pass2_model=pass2_model or "Unknown",
        )
        result = await self._call_llm_with_fallback(image_bytes, prompt)
        if not isinstance(result, dict) or "model" not in result:
             result = {"model": result.get("model") if isinstance(result, dict) else None}
        return result

    async def check_api_availability(self) -> bool:
        return len(self.workers) > 0

    async def check_availability(self) -> bool:
        return await self.check_api_availability()

# Global service instance
llm_service = LLMRouterService()
