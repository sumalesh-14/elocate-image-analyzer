"""
Pricing calculator service for determining recycling and buyback prices.

This service calculates appropriate pricing based on device condition
and material value, using the backend condition codes.
"""

import logging
from typing import Optional, Tuple, Dict, Any


logger = logging.getLogger(__name__)


class PricingCalculator:
    """Service for calculating recycling and buyback prices."""
    
    # Backend condition code descriptions
    CONDITION_DESCRIPTIONS = {
        "EXCELLENT": "Pristine/Working - Fully functional, no damage",
        "GOOD": "Fair/Minor Issues - Working with cosmetic wear",
        "FAIR": "Broken/Damaged - Powers on but partial functionality",
        "POOR": "Scrap/Parts - Does not power on, non-functional"
    }
    
    # Condition multipliers for recycling price (as % of material value)
    RECYCLING_MULTIPLIERS = {
        "EXCELLENT": 0.65,      # 65% - Pristine condition, easy to extract materials
        "GOOD": 0.55,           # 55% - Minor wear, standard processing
        "FAIR": 0.45,           # 45% - Partial functionality, more processing needed
        "POOR": 0.30,           # 30% - Non-functional, complex extraction
        None: 0.50              # Default: 50% of material value
    }
    
    # Buyback multipliers (as % of market price)
    BUYBACK_MULTIPLIERS = {
        "EXCELLENT": 0.70,      # 70% - Pristine, fully functional
        "GOOD": 0.55,           # 55% - Working with cosmetic wear
        "FAIR": 0.35,           # 35% - Partial functionality, needs repair
        "POOR": None,           # No buyback - non-functional, parts only
    }
    
    def __init__(self):
        """Initialize the pricing calculator."""
        self.logger = logging.getLogger(__name__)
    
    def calculate_recycling_price(
        self,
        total_material_value: float,
        device_condition: Optional[str] = None
    ) -> Tuple[float, str]:
        """
        Calculate suggested recycling price based on material value and condition.
        
        Args:
            total_material_value: Total value of all materials
            device_condition: Device condition code (EXCELLENT, GOOD, FAIR, POOR)
            
        Returns:
            Tuple of (recycling_price, condition_impact_explanation)
        """
        # Get multiplier from condition
        multiplier = self.RECYCLING_MULTIPLIERS.get(device_condition, 0.50)
        recycling_price = total_material_value * multiplier
        
        # Build explanation
        if device_condition and device_condition in self.CONDITION_DESCRIPTIONS:
            condition_desc = self.CONDITION_DESCRIPTIONS[device_condition]
            impact_explanation = (
                f"Device condition '{device_condition}' ({condition_desc}) "
                f"results in {int(multiplier * 100)}% of material value. "
            )
            
            if device_condition == "EXCELLENT":
                impact_explanation += "Pristine condition allows for optimal material recovery with minimal processing costs."
            elif device_condition == "GOOD":
                impact_explanation += "Minor cosmetic wear does not significantly impact material extraction efficiency."
            elif device_condition == "FAIR":
                impact_explanation += "Partial functionality requires additional disassembly and processing steps."
            elif device_condition == "POOR":
                impact_explanation += "Non-functional devices require complex extraction processes, increasing costs significantly."
        else:
            impact_explanation = (
                f"Standard recycling rate of {int(multiplier * 100)}% applied. "
                "Provide device condition for more accurate pricing."
            )
        
        return recycling_price, impact_explanation
    
    def calculate_buyback_price(
        self,
        market_price: Optional[float],
        device_condition: Optional[str] = None,
        device_age_years: Optional[float] = None
    ) -> Optional[Tuple[float, str]]:
        """
        Calculate suggested buyback price for functional devices.
        
        Args:
            market_price: Current market price of the device
            device_condition: Device condition code (EXCELLENT, GOOD, FAIR, POOR)
            device_age_years: Age of device in years (for depreciation)
            
        Returns:
            Tuple of (buyback_price, explanation) or None if not applicable
        """
        if not market_price:
            return None
        
        # Get multiplier based on condition
        multiplier = self.BUYBACK_MULTIPLIERS.get(device_condition)
        
        # POOR condition devices are not eligible for buyback (parts only)
        if multiplier is None:
            if device_condition == "POOR":
                return None  # Non-functional, no buyback offered
            else:
                # Unknown condition, use conservative estimate
                multiplier = 0.40
        
        # Apply age depreciation if available (8% per year, max 40% depreciation)
        age_factor = 1.0
        if device_age_years:
            age_depreciation = min(0.08 * device_age_years, 0.40)
            age_factor = (1 - age_depreciation)
        
        buyback_price = market_price * multiplier * age_factor
        
        # Build explanation
        condition_desc = self.CONDITION_DESCRIPTIONS.get(device_condition, "Unspecified condition")
        explanation = (
            f"Buyback price is {int(multiplier * 100)}% of market price "
            f"for '{device_condition}' condition ({condition_desc})."
        )
        
        if device_age_years:
            age_depreciation_pct = int(min(0.08 * device_age_years, 0.40) * 100)
            explanation += f" Age depreciation of {age_depreciation_pct}% applied ({device_age_years:.1f} years old)."
        
        return buyback_price, explanation
    
    def get_pricing_recommendation(
        self,
        total_material_value: float,
        market_price: Optional[float],
        device_condition: Optional[str],
        device_age_years: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive pricing recommendation.
        
        Args:
            total_material_value: Total value of materials
            market_price: Current market price
            device_condition: Device condition code (EXCELLENT, GOOD, FAIR, POOR)
            device_age_years: Device age in years
            
        Returns:
            Dictionary with pricing recommendations
        """
        # Calculate recycling price
        recycling_price, condition_impact = self.calculate_recycling_price(
            total_material_value,
            device_condition
        )
        
        # Calculate buyback price if applicable
        buyback_result = self.calculate_buyback_price(
            market_price,
            device_condition,
            device_age_years
        )
        
        buyback_price = None
        buyback_explanation = None
        if buyback_result:
            buyback_price, buyback_explanation = buyback_result
        
        # Build comprehensive breakdown
        breakdown_parts = [
            f"Material value: {total_material_value:.2f}",
            f"Recycling price: {recycling_price:.2f} ({condition_impact})"
        ]
        
        if buyback_price:
            breakdown_parts.append(
                f"Buyback price: {buyback_price:.2f} ({buyback_explanation})"
            )
            # Compare buyback vs recycling
            if buyback_price > recycling_price * 2:
                breakdown_parts.append(
                    f"Recommendation: Buyback is {buyback_price/recycling_price:.1f}x better than recycling. Device is suitable for resale/reuse."
                )
            else:
                breakdown_parts.append(
                    "Recommendation: Consider buyback if device is reusable, otherwise recycle for materials."
                )
        else:
            if device_condition == "POOR":
                breakdown_parts.append(
                    "Recommendation: Device is non-functional. Best suited for material recycling and parts recovery."
                )
            else:
                breakdown_parts.append(
                    "Recommendation: Device is best suited for material recycling."
                )
        
        price_breakdown = " | ".join(breakdown_parts)
        
        return {
            "recycling_price": round(recycling_price, 2),
            "buyback_price": round(buyback_price, 2) if buyback_price else None,
            "condition_impact": condition_impact,
            "price_breakdown": price_breakdown
        }


# Global service instance
pricing_calculator = PricingCalculator()
