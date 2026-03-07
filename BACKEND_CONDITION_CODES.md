# Backend Condition Codes Reference

## Device Condition Codes

The material analysis API uses the following condition codes that match your backend system:

| Code | Label | Description | Functional Status | Recycling Rate | Buyback Rate |
|------|-------|-------------|-------------------|----------------|--------------|
| `EXCELLENT` | Pristine / Working | Fully functional, no damage | Powers on, all features work | 65% | 70% |
| `GOOD` | Fair / Minor Issues | Working with cosmetic wear | Powers on, all features work | 55% | 55% |
| `FAIR` | Broken / Damaged | Powers on but partial functionality | Powers on, some features broken | 45% | 35% |
| `POOR` | Scrap / Parts | Does not power on, non-functional | Does not power on | 30% | Not offered |

## API Request Format

### Required Fields
```json
{
  "brand_id": "string",
  "brand_name": "string",
  "category_id": "string",
  "category_name": "string",
  "model_id": "string",
  "model_name": "string",
  "country": "string (e.g., 'IN')"
}
```

### Optional Fields
```json
{
  "deviceCondition": "EXCELLENT | GOOD | FAIR | POOR",
  "conditionNotes": "string (detailed condition description)"
}
```

## Pricing Logic

### Recycling Price Calculation
```
Recycling Price = Total Material Value × Condition Multiplier
```

**Condition Multipliers:**
- `EXCELLENT`: 65% (pristine condition, easy material extraction)
- `GOOD`: 55% (minor wear, standard processing)
- `FAIR`: 45% (partial functionality, more processing needed)
- `POOR`: 30% (non-functional, complex extraction)
- `Not specified`: 50% (default rate)

### Buyback Price Calculation
```
Buyback Price = Market Price × Condition Multiplier × Age Factor
```

**Condition Multipliers:**
- `EXCELLENT`: 70% (pristine, fully functional)
- `GOOD`: 55% (working with cosmetic wear)
- `FAIR`: 35% (partial functionality, needs repair)
- `POOR`: Not offered (non-functional, parts only)

**Age Factor:**
- 8% depreciation per year
- Maximum 40% depreciation

## Example Scenarios

### Scenario 1: EXCELLENT Condition MacBook Pro 16
```json
{
  "deviceCondition": "EXCELLENT",
  "conditionNotes": "Pristine, no wear, battery 98%"
}
```

**Results:**
- Material Value: ₹19,797
- Recycling Price: ₹12,868 (65%)
- Buyback Price: ₹174,993 (70% of ₹249,990)
- **Recommendation:** Buyback is 13.6x better

### Scenario 2: GOOD Condition MacBook Pro 16
```json
{
  "deviceCondition": "GOOD",
  "conditionNotes": "Minor scratches, fully functional, battery 85%"
}
```

**Results:**
- Material Value: ₹19,797
- Recycling Price: ₹10,888 (55%)
- Buyback Price: ₹137,495 (55% of ₹249,990)
- **Recommendation:** Buyback is 12.6x better

### Scenario 3: FAIR Condition MacBook Pro 16
```json
{
  "deviceCondition": "FAIR",
  "conditionNotes": "Powers on, webcam broken, battery 60%"
}
```

**Results:**
- Material Value: ₹19,797
- Recycling Price: ₹8,909 (45%)
- Buyback Price: ₹87,497 (35% of ₹249,990)
- **Recommendation:** Buyback is 9.8x better (if repairable)

### Scenario 4: POOR Condition MacBook Pro 16
```json
{
  "deviceCondition": "POOR",
  "conditionNotes": "Does not power on, liquid damage"
}
```

**Results:**
- Material Value: ₹19,797
- Recycling Price: ₹5,939 (30%)
- Buyback Price: Not offered
- **Recommendation:** Recycle for materials only

## Response Structure

```json
{
  "success": true,
  "timestamp": "2026-03-07T12:00:00.000000",
  "processingTimeMs": 2000,
  "data": {
    "recyclingEstimate": {
      "totalMaterialValue": 19797.00,
      "suggestedRecyclingPrice": 10888.35,
      "suggestedBuybackPrice": 137494.50,
      "conditionImpact": "Device condition 'GOOD' (Fair/Minor Issues - Working with cosmetic wear) results in 55% of material value. Minor cosmetic wear does not significantly impact material extraction efficiency.",
      "currency": "INR",
      "priceBreakdown": "Material value: 19797.00 | Recycling price: 10888.35 (...) | Buyback price: 137494.50 (...) | Recommendation: Buyback is 12.6x better than recycling. Device is suitable for resale/reuse."
    }
  }
}
```

## Integration Notes

### Frontend Display
When displaying condition options to users, use:
- **EXCELLENT**: "Pristine / Working - Fully functional, no damage"
- **GOOD**: "Fair / Minor Issues - Working with cosmetic wear"
- **FAIR**: "Broken / Damaged - Powers on but partial functionality"
- **POOR**: "Scrap / Parts - Does not power on, non-functional"

### Validation
- `deviceCondition` must be one of: `EXCELLENT`, `GOOD`, `FAIR`, `POOR` (uppercase)
- `conditionNotes` is optional but recommended for accurate pricing
- If `deviceCondition` is not provided, default 50% recycling rate is applied

### Recommendations Logic
The API provides intelligent recommendations:
- If buyback > 2x recycling: "Buyback is Xx better. Device is suitable for resale/reuse."
- If buyback available: "Consider buyback if device is reusable, otherwise recycle."
- If POOR condition: "Device is non-functional. Best suited for material recycling and parts recovery."

## Testing

### cURL Example
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
    "deviceCondition": "GOOD",
    "conditionNotes": "Minor scratches, fully functional, battery 85%"
  }'
```

### Expected Response Time
- Typical: 1.5-2.5 seconds
- Includes LLM analysis + pricing calculation
- Device pricing fetch is non-blocking (won't delay response)

## Error Handling

### Invalid Condition Code
If an invalid condition code is provided, the API will return a validation error:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "deviceCondition must be one of: EXCELLENT, GOOD, FAIR, POOR"
  }
}
```

### Missing Required Fields
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "brand_name is required"
  }
}
```
