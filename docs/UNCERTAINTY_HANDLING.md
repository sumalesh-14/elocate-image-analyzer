# Model Uncertainty Handling Feature

## Overview

The system now intelligently handles model identification uncertainty. Instead of always auto-seeding new models when uncertain, the LLM can pick from existing models and explain why identification was difficult.

## How It Works

### Three Confidence Levels

1. **High Confidence (0.9)** → Auto-seed new model
   - LLM can clearly see model identifiers (text, numbers, unique features)
   - Returns: `"NEW: MacBook Pro 16-inch 2021"` or exact match from list
   - Action: Creates new model in database (if using "NEW:" prefix)
   - Auto-seeding: ✅ ENABLED (0.9 >= 0.70 threshold)

2. **Medium Confidence (0.6)** → Pick from list + explain
   - LLM can make educated guess from provided models
   - Returns: Existing model name + uncertainty reason
   - Action: Uses existing model, no DB seeding
   - Auto-seeding: ❌ DISABLED (0.6 < 0.70 threshold)

3. **Low Confidence (0.3)** → Pick best guess + explain
   - Image quality poor or no clear identifiers
   - Returns: Best guess from list + uncertainty reason
   - Action: Uses existing model, no DB seeding
   - Auto-seeding: ❌ DISABLED (0.3 < 0.70 threshold)

### Auto-Seeding Threshold

- **Threshold**: 0.70 (defined in `database_matcher.py`)
- **High confidence** (0.9) triggers auto-seeding
- **Medium** (0.6) and **low** (0.3) confidence prevent database pollution
- Only models with "NEW:" prefix AND confidence >= 0.70 are auto-seeded

### Response Format

The LLM now returns:

```json
{
  "model": "MacBook Pro",
  "confidence": "medium",
  "uncertainty_reason": "Image angle obscures model year markings. Screen size and design suggest Pro model.",
  "recycle_items": [...]
}
```

## API Response

The `DeviceData` response now includes:

```json
{
  "category": "Laptop",
  "brand": "Apple",
  "model": "MacBook Pro",
  "model_uncertainty_reason": "Image angle obscures model year markings. Screen size and design suggest Pro model.",
  "confidenceScore": 0.93,
  ...
}
```

## Console Logging

### During Pass 3
```
📱  PASS 3 — Model Identification  (4 models offered)
────────────────────────────────────────────────────────────────────
For brand             Apple
🤖  Routing task to LLM: Gemini (Key #1)
Model (raw)           MacBook Pro
    ⚠️  Uncertainty: Image angle obscures model year markings. Screen size and design suggest Pro model.
```

### In Final Summary
```
📦  DEVICE IDENTITY
────────────────────────────────────────────────────────────────────
Category              Laptop
Brand                 Apple
Model                 MacBook Pro
    ⚠️  Why uncertain: Image angle obscures model year markings. Screen size and design suggest Pro model.
Device type           Apple MacBook
Confidence            93%
```

## Benefits

### 1. Prevents Bad Auto-Seeding
- No more creating duplicate models with slight variations
- No more seeding when LLM is guessing
- Only high-confidence identifications create new models

### 2. Provides Context
- Users understand why exact model couldn't be identified
- Helps improve image quality for future submissions
- 2-line explanations are concise and actionable

### 3. Better Database Quality
- Only confident identifications create new models
- Reduces database pollution with uncertain entries
- Maintains data integrity

## Examples

### Example 1: High Confidence (Auto-Seed)

**Image**: Clear photo showing "MacBook Pro 16-inch M1 Max 2021" on screen

**LLM Response**:
```json
{
  "model": "NEW: MacBook Pro 16-inch M1 Max 2021",
  "confidence": "high",
  "uncertainty_reason": null
}
```

**Confidence Score**: 0.9  
**Result**: ✅ New model created in database (0.9 >= 0.70)

---

### Example 2: Medium Confidence (Pick from List)

**Image**: Angled photo, can see it's a MacBook Pro but not the exact year

**Available Models**: 
- MacBook Pro 13-inch 2020
- MacBook Pro 16-inch 2021
- MacBook Air 2022

**LLM Response**:
```json
{
  "model": "MacBook Pro 16-inch 2021",
  "confidence": "medium",
  "uncertainty_reason": "Image angle obscures model year markings. Screen size and design suggest Pro model."
}
```

**Confidence Score**: 0.6  
**Result**: ✅ Uses existing model, shows uncertainty reason (0.6 < 0.70, no auto-seed)

---

### Example 3: Low Confidence (Best Guess)

**Image**: Blurry photo, can barely see it's an Apple laptop

**Available Models**:
- MacBook Pro 13-inch 2020
- MacBook Pro 16-inch 2021
- MacBook Air 2022

**LLM Response**:
```json
{
  "model": "MacBook Air 2022",
  "confidence": "low",
  "uncertainty_reason": "Poor lighting and image quality. Guessing based on thin profile visible."
}
```

**Confidence Score**: 0.3  
**Result**: ✅ Uses existing model, shows uncertainty reason (0.3 < 0.70, no auto-seed)

---

### Example 4: High Confidence with Existing Model

**Image**: Clear photo of MacBook Pro that matches existing model

**Available Models**:
- MacBook Pro 13-inch 2020
- MacBook Pro 16-inch 2021
- MacBook Air 2022

**LLM Response**:
```json
{
  "model": "MacBook Pro 16-inch 2021",
  "confidence": "high",
  "uncertainty_reason": null
}
```

**Confidence Score**: 0.9  
**Result**: ✅ Uses existing model (exact match, no "NEW:" prefix needed)

## Decision Logic

```
Can LLM confidently identify model?
├─ YES (high confidence) → 
│   ├─ Exact match in list? → Use existing model
│   └─ Not in list? → Use "NEW:" prefix → Auto-seed to DB (0.9 >= 0.70)
│
└─ NO (medium/low confidence) →
    ├─ Pick best match from list
    ├─ Provide 2-line uncertainty reason
    └─ No auto-seeding (0.6 or 0.3 < 0.70)
```

## Implementation Details

### Confidence Conversion

The analyzer converts LLM confidence levels to numeric scores:

```python
def _convert_confidence_level_to_score(self, confidence_level: str) -> float:
    level_map = {
        "high": 0.9,      # Auto-seed enabled
        "medium": 0.6,    # Auto-seed disabled
        "low": 0.3        # Auto-seed disabled
    }
    return level_map.get(confidence_level.lower(), 0.6)
```

### Model Resolution

The `_resolve_model` method uses the Pass 3 confidence score:

```python
# Extract confidence level and convert to numeric score
confidence_level = pass3_result.get("confidence", "medium")
model_confidence = self._convert_confidence_level_to_score(confidence_level)

# Use Pass 3 confidence for model resolution
model_match = await database_matcher._resolve_model(
    model_pick, models, brand_match.id, category_match.id, 
    model_confidence,  # From Pass 3, not Pass 1
    metadata=pass3_result
)
```

### Pass 3 Prompt

The prompt explicitly forbids returning null:

```
CRITICAL TASK:
You MUST return a model name. DO NOT return null unless the image is completely blank or corrupted.

1. HIGH CONFIDENCE: If you can see clear model identifiers...
2. MEDIUM CONFIDENCE: If you can make an educated guess but aren't certain...
3. LOW CONFIDENCE: If the image is unclear but you can see it's a {brand} {category}...

IMPORTANT RULES:
- NEVER return null unless the image is completely unreadable
- Use "NEW:" ONLY when you can see specific model identifiers
- When uncertain, ALWAYS pick from the provided list and explain why
```

## UI Display

The uncertainty reason can be displayed to users:

```
Device: Apple MacBook Pro
⚠️ Note: Image angle obscures model year markings. 
         Screen size and design suggest Pro model.
```

This helps users understand:
- Why exact model wasn't identified
- How to take better photos next time
- That the system made an educated guess

## Configuration

No configuration needed - the feature works automatically based on LLM confidence.

## Testing

Test with different image qualities:

1. **Clear image with visible text** → Should auto-seed with "NEW:" (high confidence)
2. **Clear image matching existing model** → Should use existing model (high confidence)
3. **Angled image** → Should pick from list + explain (medium confidence)
4. **Blurry image** → Should pick best guess + explain (low confidence)
5. **Completely obscured** → Should pick generic model + explain (low confidence)

## Backward Compatibility

- Existing API responses still work
- `model_uncertainty_reason` is optional (null if not provided)
- No breaking changes to existing integrations

## Summary

✅ **Smarter model identification** - Only auto-seeds when confident (>= 0.70)  
✅ **Better user feedback** - Explains why identification was difficult  
✅ **Cleaner database** - Prevents uncertain entries from polluting DB  
✅ **Improved UX** - Users understand system limitations  
✅ **Numeric confidence mapping** - High=0.9, Medium=0.6, Low=0.3  
✅ **Console logging** - Shows uncertainty reasons in real-time  
✅ **No more nulls** - LLM always provides best guess from list
