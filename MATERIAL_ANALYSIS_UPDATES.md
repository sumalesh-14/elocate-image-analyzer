# Material Analysis API Updates

## Overview
Enhanced the material analysis API with realistic e-waste recycling rates, condition-based pricing, recycling estimates, and device pricing information.

## Changes Made

### 1. Realistic E-Waste Scrap Rates
Updated the LLM prompt to use actual e-waste recycling market rates instead of pure commodity prices:

**Precious Metals** (70-80% of pure market rate):
- Gold: ₹4,500-5,000/g (was ₹6,500/g)
- Silver: ₹50-60/g (was ₹750/g)
- Platinum: ₹2,000-2,500/g (was ₹5,000/g)
- Palladium: ₹3,500-4,000/g (was ₹6,000/g)

**Base Metals** (scrap rates per gram):
- Copper: ₹0.40-0.50/g (was ₹550/g)
- Aluminum: ₹0.15-0.18/g (was ₹180/g)
- Steel/Iron: ₹0.03-0.05/g

**Battery Materials** (recovery rates):
- Lithium: ₹80-120/g (was ₹3,500/g)
- Cobalt: ₹300-400/g (was ₹2,500/g)
- Nickel: ₹150-200/g (was ₹2,500/g)

**Rare Earth Elements** (recovery rates):
- Neodymium: ₹100-150/g (was ₹800/g)
- Praseodymium: ₹120-180/g (was ₹1,000/g)
- Tantalum: ₹50-80/g (was ₹400/g)

### 2. Recovery Efficiency Factor
The analysis now accounts for 60-80% recovery efficiency, as mentioned in the analysis description.

### 3. Device Condition Assessment (NEW!)

#### Request Fields
```json
{
  "deviceCondition": "good",
  "functionalStatus": "fully_functional",
  "conditionNotes": "Minor scratches on back, screen is perfect, battery health 85%"
}
```

**Device Condition Options:**
- `excellent`: Like new, no visible wear
- `good`: Minor cosmetic wear, fully functional
- `fair`: Moderate wear, some cosmetic damage
- `poor`: Heavy wear, significant cosmetic damage
- `broken`: Physical damage (cracked screen, dents, etc.)

**Functional Status Options:**
- `fully_functional`: All features work perfectly
- `partially_functional`: Some features don't work (e.g., camera, speaker)
- `not_functional`: Device doesn't power on or major functions broken

**Condition Notes:** Free text field for detailed condition description

### 4. Condition-Based Pricing

#### Recycling Price Multipliers
Based on device condition (% of material value):
- Excellent: 60%
- Good: 55%
- Fair: 50%
- Poor: 40%
- Broken: 30%

Additional adjustments:
- Not functional: -10%
- Partially functional: -5%

#### Buyback Price Multipliers
For functional devices (% of market price):

**Fully Functional:**
- Excellent: 70%
- Good: 60%
- Fair: 45%
- Poor: 30%
- Broken: 15%

**Partially Functional:**
- Excellent: 50%
- Good: 40%
- Fair: 30%
- Poor: 20%
- Broken: 10%

**Not Functional:**
- Excellent: 25% (good for parts)
- Good: 20%
- Fair: 15%
- Poor: 10%
- Broken: 5%

### 5. Enhanced Response Fields

#### `recyclingEstimate` (Required)
```json
{
  "totalMaterialValue": 19797.00,
  "suggestedRecyclingPrice": 10888.35,
  "suggestedBuybackPrice": 174993.00,
  "conditionImpact": "Device condition 'good' and functional status 'fully_functional' result in 55% of material value. Good condition ensures efficient material extraction.",
  "currency": "INR",
  "priceBreakdown": "Material value: 19797.00 | Recycling price: 10888.35 (Device condition 'good' and functional status 'fully_functional' result in 55% of material value. Good condition ensures efficient material extraction.) | Buyback price: 174993.00 (Buyback price is 70% of market price based on 'good' condition and 'fully_functional' status.) | Recommendation: Consider buyback if device is reusable, otherwise recycle for materials."
}
```

- `totalMaterialValue`: Sum of all material values
- `suggestedRecyclingPrice`: Condition-adjusted recycling price
- `suggestedBuybackPrice`: Buyback price if device is functional (null if not applicable)
- `conditionImpact`: Explanation of how condition affects pricing
- `priceBreakdown`: Comprehensive pricing explanation

#### `devicePricing` (Optional)
```json
{
  "currentMarketPrice": 249990.00,
  "currency": "INR",
  "flipkartLink": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
  "amazonLink": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
  "officialLink": "https://www.apple.com/in/macbook-pro/"
}
```

### 6. Example Scenarios

#### Scenario 1: Excellent Condition, Fully Functional MacBook
```json
{
  "deviceCondition": "excellent",
  "functionalStatus": "fully_functional"
}
```
- Material value: ₹19,797
- Recycling price: ₹11,878 (60% of material value)
- Buyback price: ₹174,993 (70% of ₹249,990 market price)
- **Recommendation:** Buyback is better value

#### Scenario 2: Fair Condition, Partially Functional MacBook
```json
{
  "deviceCondition": "fair",
  "functionalStatus": "partially_functional"
}
```
- Material value: ₹19,797
- Recycling price: ₹9,404 (47.5% of material value)
- Buyback price: ₹74,997 (30% of market price)
- **Recommendation:** Buyback if repairable, otherwise recycle

#### Scenario 3: Broken, Not Functional MacBook
```json
{
  "deviceCondition": "broken",
  "functionalStatus": "not_functional"
}
```
- Material value: ₹19,797
- Recycling price: ₹5,345 (27% of material value)
- Buyback price: Not offered
- **Recommendation:** Recycle for materials only

## Implementation Details

### Files Modified
1. `app/services/material_analyzer.py` - Updated LLM prompt with realistic rates and condition info
2. `app/models/material_analysis.py` - Added condition fields and enhanced response models
3. `app/api/routes.py` - Updated endpoint to use condition-based pricing

### Files Created
1. `app/services/device_pricing.py` - Service for fetching device pricing (placeholder)
2. `app/services/pricing_calculator.py` - Condition-based pricing logic

## API Usage

### Request Example
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-materials" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_id": "mock",
    "brand_name": "Apple",
    "category_id": "mock",
    "category_name": "Laptop",
    "model_id": "test-123",
    "model_name": "MacBook Pro 16 (M4)",
    "country": "IN",
    "deviceCondition": "good",
    "functionalStatus": "fully_functional",
    "conditionNotes": "Minor scratches on bottom, screen perfect, battery 85%"
  }'
```

### Response Structure
```json
{
  "success": true,
  "timestamp": "2026-03-07T11:30:00.000000",
  "processingTimeMs": 2000,
  "data": {
    "brand": {"id": "mock", "name": "Apple"},
    "category": {"id": "mock", "name": "Laptop"},
    "model": {"id": "test-123", "name": "MacBook Pro 16 (M4)"},
    "country": "IN",
    "analysisDescription": "...",
    "materials": [...],
    "devicePricing": {
      "currentMarketPrice": 249990.00,
      "currency": "INR",
      "flipkartLink": "...",
      "amazonLink": "..."
    },
    "recyclingEstimate": {
      "totalMaterialValue": 19797.00,
      "suggestedRecyclingPrice": 10888.35,
      "suggestedBuybackPrice": 174993.00,
      "conditionImpact": "...",
      "currency": "INR",
      "priceBreakdown": "..."
    },
    "metadata": {
      "llmModel": "llama-3.3-70b-versatile",
      "analysisTimestamp": "2026-03-07T11:30:00.000000"
    }
  }
}
```

## Future Enhancements

### 1. Device Age Calculation
Automatically calculate device age from model release date:
```python
device_age_years = calculate_device_age(model_name, release_date_db)
```

### 2. Market Price Integration
Integrate with e-commerce APIs:
- Flipkart Affiliate API
- Amazon Product Advertising API
- Web scraping services

### 3. Image-Based Condition Assessment
Use computer vision to assess device condition from photos:
- Detect scratches, cracks, dents
- Assess screen condition
- Verify functional status

### 4. Historical Price Tracking
Maintain database of device prices over time for better depreciation estimates.

### 5. Regional Pricing Variations
Adjust pricing based on local market conditions and demand.
