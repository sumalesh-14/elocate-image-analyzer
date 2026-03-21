"""
Material analysis service for estimating recyclable materials in devices.

This service uses LLM to analyze device specifications and estimate
the quantity and market value of precious and recyclable materials.
"""

import logging
import json
from typing import Dict, Any, List, Tuple
from app.services.llm_router import llm_service, LLMWorker, LLMAPIError
from app.models.material_analysis import MaterialAnalysisRequest, MaterialData
from app.config import settings
from app.utils.orchestration_log import (
    log_material_analysis_start,
    log_material_llm_priority,
    log_material_llm_attempt,
    log_material_llm_success,
    log_material_llm_failed,
    log_material_results,
    log_material_analysis_error
)
import asyncio


logger = logging.getLogger(__name__)


class MaterialAnalysisError(Exception):
    """Custom exception for material analysis errors."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)


class MaterialAnalyzerService:
    """Service for analyzing device materials using LLM."""
    
    def __init__(self):
        """Initialize the material analyzer service."""
        self.logger = logging.getLogger(__name__)
        self._text_only_workers = None
    
    def _get_text_only_workers(self) -> List[LLMWorker]:
        """
        Get LLM workers ordered by material analysis priority.
        This creates a separate worker list specifically for text-only material analysis.
        """
        if self._text_only_workers is not None:
            return self._text_only_workers
        
        # Get priority order from config
        priority_order = settings.material_analysis_llm_priority_list
        
        # Get all available workers from the main LLM service
        all_workers = llm_service.workers
        
        # Create a map of provider -> workers
        provider_workers = {
            "gemini": [],
            "openai": [],
            "groq": []
        }
        
        for worker in all_workers:
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
        
        self._text_only_workers = ordered_workers
        
        # Log the priority order (only once)
        log_material_llm_priority(
            priority_order,
            [w.display_name for w in ordered_workers]
        )
        
        return self._text_only_workers
    
    async def _call_text_llm_with_priority(self, prompt: str) -> Tuple[Dict[str, Any], str]:
        """
        Call LLM for text-only generation with custom priority order.
        
        Args:
            prompt: The text prompt
            
        Returns:
            Tuple of (parsed response dict, model name used)
            
        Raises:
            MaterialAnalysisError: If all workers fail
        """
        workers = self._get_text_only_workers()
        
        if not workers:
            raise MaterialAnalysisError(
                "NO_LLM_WORKERS",
                "No LLM workers available for material analysis"
            )
        
        for idx, worker in enumerate(workers):
            try:
                log_material_llm_attempt(worker.display_name, worker.text_only_model)
                
                response_text = await asyncio.wait_for(
                    worker.generate_text_only(prompt),
                    timeout=settings.REQUEST_TIMEOUT
                )
                
                # Parse response
                text = response_text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                elif text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                
                parsed_data = json.loads(text.strip())
                
                # Count materials for logging
                material_count = len(parsed_data.get('materials', []))
                log_material_llm_success(worker.display_name, worker.text_only_model, material_count)
                
                return parsed_data, worker.text_only_model
                
            except asyncio.TimeoutError:
                next_worker = workers[idx + 1].display_name if idx + 1 < len(workers) else None
                log_material_llm_failed(worker.display_name, "Timeout", next_worker)
                continue
            except json.JSONDecodeError as e:
                next_worker = workers[idx + 1].display_name if idx + 1 < len(workers) else None
                log_material_llm_failed(worker.display_name, f"JSON parse error: {str(e)[:50]}", next_worker)
                continue
            except Exception as e:
                next_worker = workers[idx + 1].display_name if idx + 1 < len(workers) else None
                log_material_llm_failed(worker.display_name, str(e)[:50], next_worker)
                continue
        
        raise MaterialAnalysisError(
            "ALL_WORKERS_FAILED",
            "All LLM providers failed for material analysis"
        )
    
    def _check_llm_ewaste_response(self, analysis_description: str, materials: list) -> None:
        """Check if the LLM response indicates the input is not an e-waste device.
        
        The LLM sometimes processes non-electronic inputs and returns materials
        like PVC, foam, rubber — this catches that case.
        
        Args:
            analysis_description: The LLM's analysis description
            materials: The list of material dicts from the LLM
            
        Raises:
            MaterialAnalysisError: If the response indicates a non-electronic device
        """
        non_ewaste_signals = [
            "non-electronic", "not an electronic", "no circuit board", "no electronic component",
            "not applicable", "footwear", "clothing", "apparel", "food", "not e-waste",
            "no precious metal", "no recyclable electronic",
        ]
        
        desc_lower = analysis_description.lower()
        for signal in non_ewaste_signals:
            if signal in desc_lower:
                log_material_analysis_error(
                    "NOT_AN_EWASTE_DEVICE",
                    "The provided item does not appear to be an electronic device"
                )
                raise MaterialAnalysisError(
                    "NOT_AN_EWASTE_DEVICE",
                    "Material analysis is only available for electronic devices (e-waste). "
                    "The provided item does not appear to be an electronic device. "
                    "Please provide a valid electronic device such as a smartphone, laptop, tablet, or other electronic equipment."
                )
        
        # Also check if all materials are non-electronic (PVC, foam, rubber, fabric, etc.)
        non_electronic_materials = {
            "pvc", "eva foam", "foam", "rubber", "fabric", "leather", "cotton",
            "polyester", "nylon", "plastic resin", "silicone rubber",
        }
        material_names = [
            (m.get("materialName") or m.get("material_name") or "").lower()
            for m in materials
        ]
        if material_names and all(
            any(ne in name for ne in non_electronic_materials)
            for name in material_names
            if name
        ):
            log_material_analysis_error(
                "NOT_AN_EWASTE_DEVICE",
                "No electronic materials found — item does not appear to be an e-waste device"
            )
            raise MaterialAnalysisError(
                "NOT_AN_EWASTE_DEVICE",
                "Material analysis is only available for electronic devices (e-waste). "
                "No electronic materials were identified in the provided item. "
                "Please provide a valid electronic device such as a smartphone, laptop, tablet, or other electronic equipment."
            )

    def _validate_ewaste_category(self, category_name: str, brand_name: str, model_name: str) -> None:
        """Validate that the provided category is an electronic/e-waste device.
        
        Args:
            category_name: The device category name
            brand_name: The brand name
            model_name: The model name
            
        Raises:
            MaterialAnalysisError: If the input does not represent an e-waste device
        """
        # Known non-electronic categories that should be rejected
        non_ewaste_keywords = {
            # Footwear / apparel
            "shoe", "shoes", "slipper", "slippers", "sandal", "sandals", "boot", "boots",
            "sneaker", "sneakers", "footwear", "clothing", "apparel", "shirt", "pants",
            "dress", "jacket", "coat", "hat", "cap", "bag", "purse", "wallet",
            # Food / nature
            "food", "fruit", "vegetable", "animal", "plant", "flower", "tree",
            "nature", "landscape", "outdoor",
            # Furniture / household
            "furniture", "chair", "table", "sofa", "bed", "desk", "shelf",
            # Vehicles
            "car", "vehicle", "bike", "bicycle", "motorcycle", "truck",
            # Stationery / misc
            "toy", "book", "paper", "wood", "stone", "rock",
            # People
            "human", "person", "face", "body",
            # Buildings
            "building", "architecture", "house", "room",
            # Art / jewelry
            "art", "painting", "sculpture", "jewelry", "jewellery",
            # Medical / chemical
            "medicine", "drug", "chemical",
            # Weapons / sports
            "weapon", "gun", "knife", "sport", "ball",
        }
        
        category_lower = category_name.lower().strip()
        brand_lower = brand_name.lower().strip()
        model_lower = model_name.lower().strip()

        # Known valid e-waste categories — skip validation entirely for these
        ewaste_categories = {
            "smartphone", "mobile phone", "phone", "laptop", "notebook", "tablet",
            "television", "tv", "monitor", "display", "desktop", "computer", "pc",
            "printer", "scanner", "camera", "dslr", "mirrorless", "camcorder",
            "smartwatch", "wearable", "headphone", "earphone", "speaker",
            "router", "modem", "networking", "ups", "inverter", "power supply",
            "set-top box", "set top box", "stb", "gaming console", "console",
            "refrigerator", "washing machine", "air conditioner", "microwave",
            "small appliance", "iron", "mixer", "grinder", "vacuum cleaner",
            "projector", "hard drive", "ssd", "storage", "keyboard", "mouse",
            "server", "workstation",
        }

        if any(cat in category_lower for cat in ewaste_categories):
            return  # Valid e-waste category, skip further checks

        for keyword in non_ewaste_keywords:
            if keyword in category_lower or keyword in brand_lower or keyword in model_lower:
                log_material_analysis_error(
                    "NOT_AN_EWASTE_DEVICE",
                    f"'{category_name}' is not a recognized e-waste or electronic device category"
                )
                raise MaterialAnalysisError(
                    "NOT_AN_EWASTE_DEVICE",
                    f"Material analysis is only available for electronic devices (e-waste). "
                    f"'{category_name}' does not appear to be an electronic device category. "
                    f"Please provide a valid electronic device such as a smartphone, laptop, tablet, or other electronic equipment."
                )

    def _build_analysis_prompt(self, request: MaterialAnalysisRequest) -> str:
        """Build the LLM prompt for material analysis.
        
        Args:
            request: Material analysis request data
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert in electronic device recycling and material recovery. Analyze the following device and provide a detailed breakdown of recyclable and precious materials.

Device Information:
- Brand: {request.brand_name}
- Category: {request.category_name}
- Model: {request.model_name}
- Country: {request.country}
"""
        
        if request.description:
            prompt += f"- Additional Context: {request.description}\n"
        
        if request.device_condition:
            condition_desc = {
                "EXCELLENT": "Pristine/Working - Fully functional, no damage",
                "GOOD": "Fair/Minor Issues - Working with cosmetic wear",
                "FAIR": "Broken/Damaged - Powers on but partial functionality",
                "POOR": "Scrap/Parts - Does not power on, non-functional"
            }.get(request.device_condition, request.device_condition)
            prompt += f"- Device Condition: {request.device_condition} ({condition_desc})\n"
        
        if request.condition_notes:
            prompt += f"- Condition Notes: {request.condition_notes}\n"
        
        prompt += """
Your task:
1. Identify ALL recyclable materials in this device (precious metals, base metals, rare earth elements, etc.)
2. Estimate the quantity of each material in grams
3. Provide the REALISTIC E-WASTE RECYCLING/SCRAP market rate per gram (NOT pure commodity prices)
4. Specify WHERE each material is typically found in the device (e.g., "Circuit board", "Battery", "Display", "Motor", "Casing")
5. Be comprehensive - include materials like: Gold, Silver, Copper, Aluminum, Lithium, Cobalt, Palladium, Platinum, Tantalum, Neodymium, etc.

CRITICAL PRICING INSTRUCTIONS - USE E-WASTE SCRAP RATES:
For India (INR), use these REALISTIC SCRAP/RECYCLING rates per gram:

PRECIOUS METALS (use 70-80% of pure market rate due to recovery costs):
- Gold: ₹4,500-5,000/gram (not ₹6,500)
- Silver: ₹50-60/gram (not ₹750)
- Platinum: ₹2,000-2,500/gram (not ₹5,000)
- Palladium: ₹3,500-4,000/gram (not ₹6,000)

BASE METALS (use scrap rates, typically per kg converted to per gram):
- Copper scrap: ₹0.40-0.50/gram (₹400-500/kg)
- Aluminum scrap: ₹0.15-0.18/gram (₹150-180/kg)
- Steel/Iron scrap: ₹0.03-0.05/gram (₹30-50/kg)

BATTERY MATERIALS (e-waste recovery rates):
- Lithium (battery grade scrap): ₹80-120/gram
- Cobalt (battery scrap): ₹300-400/gram
- Nickel (battery scrap): ₹150-200/gram

RARE EARTH ELEMENTS (recovery rates):
- Neodymium: ₹100-150/gram
- Praseodymium: ₹120-180/gram
- Tantalum: ₹50-80/gram

For other countries, adjust proportionally based on local scrap market rates.

IMPORTANT COMPOSITION GUIDELINES:
- Provide realistic estimates based on typical device composition
- Include both precious metals (gold, silver, platinum, palladium) and base metals (copper, aluminum)
- For batteries, include lithium, cobalt, and other battery materials
- For circuit boards, include gold, silver, copper, and rare earth elements
- Mark materials as "precious" if they are precious metals (gold, silver, platinum, palladium)
- Specify the component/part where each material is found (be specific: "Lithium-ion battery", "Main circuit board", "Display panel", "Vibration motor", "Aluminum frame", etc.)
- Remember: rates should reflect SCRAP/RECYCLING value, not pure commodity prices
- Account for recovery efficiency (typically 60-80% of theoretical maximum)

Also estimate the CURRENT SECOND-HAND / USED MARKET PRICE of this specific device model in the given country.
- This is the realistic resale price a buyer would pay for this device in used condition (not brand new retail price)
- For India: check typical prices on platforms like OLX, Cashify, Flipkart Second Hand, Amazon Renewed
- Be accurate — e.g. iPhone 14 128GB used in India is around ₹40,000-55,000 in 2024-2025
- If the exact model is unknown, estimate based on similar models in the same category/brand/year

Return ONLY a valid JSON object with this exact structure (no markdown, no code blocks, no additional text):
{
  "materials": [
    {
      "materialName": "Gold",
      "isPrecious": true,
      "estimatedQuantityGrams": 0.034,
      "marketRatePerGram": 4800,
      "currency": "INR",
      "foundIn": "Circuit board and connectors"
    }
  ],
  "estimatedMarketPrice": 48000,
  "analysisDescription": "Brief description of the analysis methodology including recovery efficiency considerations"
}

Ensure all numeric values are realistic and based on actual e-waste recycling market data, not pure commodity prices."""
        
        return prompt
    
    async def analyze_materials(
        self,
        request: MaterialAnalysisRequest
    ) -> tuple[List[MaterialData], str, str, float, float | None]:
        """Analyze device materials using LLM.
        
        Returns:
            Tuple of (materials list, analysis description, llm model used, total material value, estimated market price)
        """
        start_time = log_material_analysis_start(
            request.brand_name,
            request.model_name,
            request.category_name,
            request.country
        )
        
        try:
            self._validate_ewaste_category(request.category_name, request.brand_name, request.model_name)

            prompt = self._build_analysis_prompt(request)
            response_data, model_used = await self._call_text_llm_with_priority(prompt)
            
            if not response_data:
                log_material_analysis_error("LLM_NO_RESPONSE", "LLM did not return a valid response")
                raise MaterialAnalysisError("LLM_NO_RESPONSE", "LLM did not return a valid response")
            
            parsed_data = response_data
            
            if "materials" not in parsed_data:
                log_material_analysis_error("INVALID_LLM_RESPONSE", "LLM response missing 'materials' field")
                raise MaterialAnalysisError("INVALID_LLM_RESPONSE", "LLM response missing 'materials' field")
            
            if not isinstance(parsed_data["materials"], list):
                log_material_analysis_error("INVALID_LLM_RESPONSE", "'materials' field must be a list")
                raise MaterialAnalysisError("INVALID_LLM_RESPONSE", "'materials' field must be a list")
            
            if not parsed_data["materials"]:
                log_material_analysis_error("NO_MATERIALS_FOUND", "No materials identified in the device")
                raise MaterialAnalysisError("NO_MATERIALS_FOUND", "No materials identified in the device")
            
            analysis_desc = parsed_data.get("analysisDescription", "")
            self._check_llm_ewaste_response(analysis_desc, parsed_data["materials"])
            
            materials = []
            for material_dict in parsed_data["materials"]:
                try:
                    material = MaterialData(**material_dict)
                    materials.append(material)
                except Exception as e:
                    self.logger.warning(f"Failed to parse material: {e}", extra={"material": material_dict})
                    continue
            
            if not materials:
                log_material_analysis_error("NO_VALID_MATERIALS", "No valid materials could be parsed from LLM response")
                raise MaterialAnalysisError("NO_VALID_MATERIALS", "No valid materials could be parsed from LLM response")
            
            analysis_description = parsed_data.get(
                "analysisDescription",
                "Material recovery estimation based on device specifications"
            )
            
            total_material_value = sum(
                material.estimated_quantity_grams * material.market_rate_per_gram
                for material in materials
            )

            # Extract LLM-estimated market price (used second-hand price)
            llm_market_price = parsed_data.get("estimatedMarketPrice")
            if llm_market_price:
                try:
                    llm_market_price = float(llm_market_price)
                except (TypeError, ValueError):
                    llm_market_price = None
            
            log_material_results(start_time, parsed_data["materials"], analysis_description, model_used)
            
            return materials, analysis_description, model_used, total_material_value, llm_market_price
            
        except MaterialAnalysisError:
            raise
        except Exception as e:
            log_material_analysis_error("ANALYSIS_FAILED", f"Material analysis failed: {str(e)}")
            raise MaterialAnalysisError("ANALYSIS_FAILED", f"Material analysis failed: {str(e)}")


# Global service instance
material_analyzer_service = MaterialAnalyzerService()
