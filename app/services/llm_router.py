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

CRITICAL TASK:
You MUST return a model name. DO NOT return null unless the image is completely blank or corrupted.

1. HIGH CONFIDENCE: If you can see clear model identifiers (text, numbers, unique features):
   - If it EXACTLY matches a model from the list above → return that exact name
   - If it's NOT in the list → return "NEW: <specific model name>"

2. MEDIUM CONFIDENCE: If you can make an educated guess but aren't certain:
   - Pick the MOST LIKELY model from the list above
   - Provide a 2-line explanation of why identification is difficult

3. LOW CONFIDENCE: If the image is unclear but you can see it's a {brand} {category}:
   - Pick the MOST COMMON or GENERIC model from the list above
   - Provide a 2-line explanation of the difficulty

IMPORTANT RULES:
- NEVER return null unless the image is completely unreadable
- Use "NEW:" ONLY when you can see specific model identifiers (text/numbers)
- When uncertain, ALWAYS pick from the provided list and explain why
- Your explanation should be max 2 lines and describe what makes identification difficult

Return ONLY valid JSON – no markdown fences:
{{
  "model": "<exact model from list, OR NEW: <specific name>, OR best guess from list>",
  "confidence": "<high|medium|low>",
  "uncertainty_reason": "<2-line explanation if confidence is medium/low, otherwise null>",
  "recycle_items": [
    {{
      "type": "<material name, e.g., gold>",
      "grams": <number>,
      "market_price": "<estimated price, e.g., 10 in Indian rupees>",
      "is_precious": <boolean>
    }}
  ]
}}

Examples:
- High confidence with NEW model: {{"model": "NEW: MacBook Pro 16-inch 2021", "confidence": "high", "uncertainty_reason": null}}
- High confidence from list: {{"model": "MacBook Pro", "confidence": "high", "uncertainty_reason": null}}
- Medium confidence: {{"model": "MacBook Pro", "confidence": "medium", "uncertainty_reason": "Image angle obscures model year markings. Screen size and design suggest Pro model."}}
- Low confidence: {{"model": "MacBook Air", "confidence": "low", "uncertainty_reason": "Poor lighting and image quality. Guessing Air based on thin profile visible."}}

Return ONLY the JSON object, nothing else.
"""

class LLMAPIError(Exception):
    """Exception raised for LLM API errors."""
    pass

class LLMWorker:
    def __init__(self, provider: str, api_key: str, model_name: str, index: int, text_only_model: str = None):
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name  # For vision/image tasks
        self.text_only_model = text_only_model or model_name  # For text-only tasks
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
    
    async def generate_text_only(self, prompt: str) -> str:
        """Generate text-only response without image (for material analysis, etc.)."""
        if self.provider == "gemini":
            return await self._generate_gemini_text_only(prompt)
        elif self.provider == "openai":
            return await self._generate_openai_text_only(prompt)
        elif self.provider == "groq":
            return await self._generate_groq_text_only(prompt)
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
    
    async def _generate_gemini_text_only(self, prompt: str) -> str:
        """Generate text-only response from Gemini without image."""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.text_only_model,
                contents=[prompt]
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
    
    async def _generate_groq_text_only(self, prompt: str) -> str:
        """Generate text-only response from Groq without image."""
        response = await self.client.chat.completions.create(
            model=self.text_only_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    async def _generate_openai_text_only(self, prompt: str) -> str:
        """Generate text-only response from OpenAI without image."""
        response = await self.client.chat.completions.create(
            model=self.text_only_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
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
        self._image_analysis_workers = None
        
        # Load API keys
        gemini_keys = settings.gemini_api_keys_list
        openai_keys = settings.openai_api_keys_list
        groq_keys = settings.groq_api_keys_list

        for i, key in enumerate(gemini_keys):
            if key and "your_" not in key:
                self.workers.append(LLMWorker("gemini", key, "gemini-2.5-flash", i+1, text_only_model="gemini-2.5-flash"))
                
        for i, key in enumerate(openai_keys):
            if key and "your_" not in key:
                self.workers.append(LLMWorker("openai", key, "gpt-4o-mini", i+1, text_only_model="gpt-4o-mini"))
                
        for i, key in enumerate(groq_keys):
            if key and "your_" not in key:
                # Use vision model for images, but text-only model for text tasks
                self.workers.append(LLMWorker("groq", key, "llama-3.2-11b-vision-preview", i+1, text_only_model="llama-3.3-70b-versatile"))
                
        if not self.workers:
            logger.warning("No valid LLM API keys found! System will fail!")
        else:
            logger.info(f"LLMRouterService initialized with {len(self.workers)} workers: {[w.display_name for w in self.workers]}")
    
    def _get_image_analysis_workers(self) -> List[LLMWorker]:
        """
        Get LLM workers ordered by image analysis priority.
        This creates a separate worker list specifically for image analysis.
        """
        if self._image_analysis_workers is not None:
            return self._image_analysis_workers
        
        # Get priority order from config
        priority_order = settings.image_analysis_llm_priority_list
        logger.info(f"Image Analysis LLM Priority: {priority_order}")
        
        # Create a map of provider -> workers
        provider_workers = {
            "gemini": [],
            "openai": [],
            "groq": []
        }
        
        for worker in self.workers:
            if worker.provider in provider_workers:
                provider_workers[worker.provider].append(worker)
        
        # Build ordered list based on priority
        ordered_workers = []
        for provider in priority_order:
            if provider in provider_workers:
                ordered_workers.extend(provider_workers[provider])
        
        # Add any remaining workers not in priority list
        for provider, workers in provider_workers.items():
            if provider not in priority_order:
                ordered_workers.extend(workers)
        
        self._image_analysis_workers = ordered_workers
        logger.info(
            f"Image Analysis Workers initialized: {[w.display_name for w in ordered_workers]}"
        )
        
        return self._image_analysis_workers

    async def _call_llm_with_fallback(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        """Iterates through workers until one succeeds (uses image analysis priority)."""
        workers = self._get_image_analysis_workers()
        
        if not workers:
            raise LLMAPIError("No active LLM workers available.")
            
        attempts = 0
        max_attempts = len(workers)
        
        for idx, worker in enumerate(workers):
            log_llm_attempt(worker.display_name)
            
            try:
                response_text = await asyncio.wait_for(
                    worker.generate(image_bytes, prompt),
                    timeout=settings.REQUEST_TIMEOUT,
                )
                return self._parse_response(response_text)
                
            except Exception as e:
                error_str = str(e).lower()
                next_worker = workers[idx + 1] if idx + 1 < len(workers) else None
                
                reason = "Rate Limit/Timeout" if "429" in error_str or "timeout" in error_str else "API Error"
                if next_worker:
                    log_llm_switched(worker.display_name, reason, next_worker.display_name)
                
                attempts += 1
                if attempts >= max_attempts:
                    break
                
        raise LLMAPIError("All LLM workers failed or rate-limited.")
    
    async def _call_llm_text_only_with_fallback(self, prompt: str) -> Dict[str, Any]:
        """Iterates through workers for text-only generation until one succeeds."""
        if not self.workers:
            raise LLMAPIError("No active LLM workers available.")
            
        attempts = 0
        max_attempts = len(self.workers)
        
        while attempts < max_attempts:
            worker = self.workers[self.current_idx]
            log_llm_attempt(worker.display_name)
            
            try:
                response_text = await asyncio.wait_for(
                    worker.generate_text_only(prompt),
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
    
    async def generate_text_only(self, prompt: str) -> Dict[str, Any]:
        """
        Public method for text-only generation (no image required).
        Used for material analysis and other text-based tasks.
        
        Args:
            prompt: The text prompt for the LLM
            
        Returns:
            Dict containing the parsed JSON response
            
        Raises:
            LLMAPIError: If all workers fail
        """
        return await self._call_llm_text_only_with_fallback(prompt)

    async def call_chat_with_fallback(
        self,
        messages_by_provider: Dict[str, Any],
        system_instruction: str,
    ) -> Dict[str, Any]:
        """
        Iterate through all workers for chat (text-only, conversational).
        Falls back to next worker on rate limit or any error.

        Returns:
            {"text": str, "worker_name": str}
        """
        from app.utils.orchestration_log import log_chat_llm_attempt, log_chat_llm_switched, log_chat_llm_all_failed

        if not self.workers:
            raise LLMAPIError("No active LLM workers available.")

        # Order workers by CHAT_LLM_PRIORITY env setting
        priority = settings.chat_llm_priority_list
        provider_map: Dict[str, list] = {}
        for w in self.workers:
            provider_map.setdefault(w.provider, []).append(w)
        ordered = []
        for p in priority:
            ordered.extend(provider_map.get(p, []))
        # Append any workers whose provider wasn't in the priority list
        for p, ws in provider_map.items():
            if p not in priority:
                ordered.extend(ws)

        logger.info(f"Chat LLM priority: {priority} → workers: {[w.display_name for w in ordered]}")

        history = messages_by_provider.get("history", [])
        user_message = messages_by_provider.get("user_message", "")

        for idx, worker in enumerate(ordered):
            log_chat_llm_attempt(worker.display_name)
            try:
                reply_text = await asyncio.wait_for(
                    self._chat_with_worker(worker, history, user_message, system_instruction),
                    timeout=settings.REQUEST_TIMEOUT,
                )
                return {"text": reply_text, "worker_name": worker.display_name}

            except Exception as e:
                error_str = str(e).lower()
                reason = "Rate Limit" if ("429" in error_str or "quota" in error_str) else (
                    "Timeout" if "timeout" in error_str else "API Error"
                )
                next_worker = ordered[idx + 1] if idx + 1 < len(ordered) else None
                if next_worker:
                    log_chat_llm_switched(worker.display_name, reason, next_worker.display_name)
                else:
                    log_chat_llm_all_failed()

        raise LLMAPIError("All LLM workers failed for chat.")

    async def _chat_with_worker(
        self,
        worker: "LLMWorker",
        history: list,
        user_message: str,
        system_instruction: str,
    ) -> str:
        """Send a chat message using a specific worker with full history."""
        if worker.provider == "gemini":
            from google.genai import types
            contents = []
            for h in history:
                role = h["role"] if isinstance(h, dict) else h.role
                parts_list = h["parts"] if isinstance(h, dict) else h.parts
                text_parts = "\n".join(
                    p["text"] if isinstance(p, dict) else p.text for p in parts_list
                )
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text_parts)]))
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: worker.client.models.generate_content(
                    model=worker.text_only_model,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction),
                )
            )
            return response.text

        elif worker.provider in ("openai", "groq"):
            messages = [{"role": "system", "content": system_instruction}]
            for h in history:
                role_raw = h["role"] if isinstance(h, dict) else h.role
                parts_list = h["parts"] if isinstance(h, dict) else h.parts
                text_parts = "\n".join(
                    p["text"] if isinstance(p, dict) else p.text for p in parts_list
                )
                messages.append({
                    "role": "assistant" if role_raw == "model" else "user",
                    "content": text_parts
                })
            messages.append({"role": "user", "content": user_message})

            response = await worker.client.chat.completions.create(
                model=worker.text_only_model,
                messages=messages,
            )
            return response.choices[0].message.content

        raise ValueError(f"Unknown provider: {worker.provider}")

# Global service instance
llm_service = LLMRouterService()
