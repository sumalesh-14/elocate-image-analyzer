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
        
        prompt += """
Your task:
1. Identify ALL recyclable materials in this device (precious metals, base metals, rare earth elements, etc.)
2. Estimate the quantity of each material in grams
3. Provide the current market rate per gram for each material in the local currency of the specified country
4. Specify WHERE each material is typically found in the device (e.g., "Circuit board", "Battery", "Display", "Motor", "Casing")
5. Be comprehensive - include materials like: Gold, Silver, Copper, Aluminum, Lithium, Cobalt, Palladium, Platinum, Tantalum, Neodymium, etc.

IMPORTANT INSTRUCTIONS:
- Provide realistic estimates based on typical device composition
- Use current market rates for the specified country
- Include both precious metals (gold, silver, platinum, palladium) and base metals (copper, aluminum)
- For batteries, include lithium, cobalt, and other battery materials
- For circuit boards, include gold, silver, copper, and rare earth elements
- Mark materials as "precious" if they are precious metals (gold, silver, platinum, palladium)
- Specify the component/part where each material is found (be specific: "Lithium-ion battery", "Main circuit board", "Display panel", "Vibration motor", "Aluminum frame", etc.)

Return ONLY a valid JSON object with this exact structure (no markdown, no code blocks, no additional text):
{
  "materials": [
    {
      "materialName": "Gold",
      "isPrecious": true,
      "estimatedQuantityGrams": 0.034,
      "marketRatePerGram": 6500,
      "currency": "INR",
      "foundIn": "Circuit board and connectors"
    }
  ],
  "analysisDescription": "Brief description of the analysis methodology"
}

Ensure all numeric values are realistic and based on actual device composition data."""
        
        return prompt
    
    async def analyze_materials(
        self,
        request: MaterialAnalysisRequest
    ) -> tuple[List[MaterialData], str, str]:
        """Analyze device materials using LLM.
        
        Args:
            request: Material analysis request
            
        Returns:
            Tuple of (materials list, analysis description, llm model used)
            
        Raises:
            MaterialAnalysisError: If analysis fails
        """
        # Start logging
        start_time = log_material_analysis_start(
            request.brand_name,
            request.model_name,
            request.category_name,
            request.country
        )
        
        try:
            # Build the prompt
            prompt = self._build_analysis_prompt(request)
            
            # Call LLM service using custom priority order for material analysis
            response_data, model_used = await self._call_text_llm_with_priority(prompt)
            
            if not response_data:
                log_material_analysis_error("LLM_NO_RESPONSE", "LLM did not return a valid response")
                raise MaterialAnalysisError(
                    "LLM_NO_RESPONSE",
                    "LLM did not return a valid response"
                )
            
            # The response is already parsed as JSON dict
            parsed_data = response_data
            
            # Validate response structure
            if "materials" not in parsed_data:
                log_material_analysis_error("INVALID_LLM_RESPONSE", "LLM response missing 'materials' field")
                raise MaterialAnalysisError(
                    "INVALID_LLM_RESPONSE",
                    "LLM response missing 'materials' field"
                )
            
            if not isinstance(parsed_data["materials"], list):
                log_material_analysis_error("INVALID_LLM_RESPONSE", "'materials' field must be a list")
                raise MaterialAnalysisError(
                    "INVALID_LLM_RESPONSE",
                    "'materials' field must be a list"
                )
            
            if not parsed_data["materials"]:
                log_material_analysis_error("NO_MATERIALS_FOUND", "No materials identified in the device")
                raise MaterialAnalysisError(
                    "NO_MATERIALS_FOUND",
                    "No materials identified in the device"
                )
            
            # Parse materials
            materials = []
            for material_dict in parsed_data["materials"]:
                try:
                    material = MaterialData(**material_dict)
                    materials.append(material)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse material: {e}",
                        extra={"material": material_dict}
                    )
                    continue
            
            if not materials:
                log_material_analysis_error("NO_VALID_MATERIALS", "No valid materials could be parsed from LLM response")
                raise MaterialAnalysisError(
                    "NO_VALID_MATERIALS",
                    "No valid materials could be parsed from LLM response"
                )
            
            analysis_description = parsed_data.get(
                "analysisDescription",
                "Material recovery estimation based on device specifications"
            )
            
            # Log the beautiful results
            log_material_results(
                start_time,
                parsed_data["materials"],
                analysis_description,
                model_used
            )
            
            return materials, analysis_description, model_used
            
        except MaterialAnalysisError:
            raise
        except Exception as e:
            log_material_analysis_error("ANALYSIS_FAILED", f"Material analysis failed: {str(e)}")
            raise MaterialAnalysisError(
                "ANALYSIS_FAILED",
                f"Material analysis failed: {str(e)}"
            )


# Global service instance
material_analyzer_service = MaterialAnalyzerService()
