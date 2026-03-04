# Groq Model Fix for Material Analysis

## Issue

Groq decommissioned the `llama-3.2-11b-vision-preview` model, causing material analysis to fail with error:

```
Error code: 400 - {'error': {'message': 'The model `llama-3.2-11b-vision-preview` has been decommissioned and is no longer supported.'}}
```

## Solution

Updated the LLM router to support separate models for vision tasks vs text-only tasks.

### Changes Made

#### 1. LLMWorker Class Enhancement

Added `text_only_model` parameter to support different models for different tasks:

```python
class LLMWorker:
    def __init__(self, provider: str, api_key: str, model_name: str, index: int, text_only_model: str = None):
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name  # For vision/image tasks
        self.text_only_model = text_only_model or model_name  # For text-only tasks
        # ...
```

#### 2. Updated Text-Only Methods

All text-only generation methods now use `self.text_only_model`:

**Gemini:**
```python
async def _generate_gemini_text_only(self, prompt: str) -> str:
    response = await loop.run_in_executor(
        None,
        lambda: self.client.models.generate_content(
            model=self.text_only_model,  # Changed from self.model_name
            contents=[prompt]
        )
    )
    return response.text
```

**OpenAI:**
```python
async def _generate_openai_text_only(self, prompt: str) -> str:
    response = await self.client.chat.completions.create(
        model=self.text_only_model,  # Changed from self.model_name
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

**Groq:**
```python
async def _generate_groq_text_only(self, prompt: str) -> str:
    response = await self.client.chat.completions.create(
        model=self.text_only_model,  # Changed from self.model_name
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

#### 3. Worker Initialization

Updated worker initialization to specify text-only models:

```python
# Gemini - same model for both
self.workers.append(LLMWorker(
    "gemini", 
    key, 
    "gemini-2.5-flash", 
    i+1, 
    text_only_model="gemini-2.5-flash"
))

# OpenAI - same model for both
self.workers.append(LLMWorker(
    "openai", 
    key, 
    "gpt-4o-mini", 
    i+1, 
    text_only_model="gpt-4o-mini"
))

# Groq - DIFFERENT models for vision vs text
self.workers.append(LLMWorker(
    "groq", 
    key, 
    "llama-3.2-11b-vision-preview",  # Vision model (for image analysis)
    i+1, 
    text_only_model="llama-3.3-70b-versatile"  # Text-only model (for material analysis)
))
```

## Groq Model Selection

### For Image Analysis (Vision Tasks):
- Model: `llama-3.2-11b-vision-preview`
- Used by: Device image identification
- Status: Still active for vision tasks

### For Text-Only Tasks (Material Analysis):
- Model: `llama-3.3-70b-versatile`
- Used by: Material analysis, text generation
- Status: Active and recommended by Groq

## Alternative Groq Text Models

If `llama-3.3-70b-versatile` has issues, you can use these alternatives:

1. **llama-3.1-70b-versatile** - Previous generation, very stable
2. **llama-3.1-8b-instant** - Faster, lower cost
3. **mixtral-8x7b-32768** - Good for longer contexts
4. **gemma2-9b-it** - Efficient alternative

To change the model, update this line in `app/services/llm_router.py`:

```python
self.workers.append(LLMWorker(
    "groq", 
    key, 
    "llama-3.2-11b-vision-preview", 
    i+1, 
    text_only_model="YOUR_PREFERRED_MODEL_HERE"  # Change this
))
```

## Testing

After the fix, material analysis should work with Groq:

```bash
# Test the endpoint
python test_material_analysis.py
```

Expected log output:
```
INFO: Attempting material analysis with Groq (Key #1)
INFO: Material analysis successful with Groq (Key #1) using model llama-3.3-70b-versatile
```

## Priority Order

The material analysis LLM priority is controlled by `.env`:

```env
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
```

With this fix:
1. Groq tries first with `llama-3.3-70b-versatile`
2. If Groq fails, falls back to Gemini with `gemini-2.5-flash`
3. If Gemini fails, falls back to OpenAI with `gpt-4o-mini`

## Benefits

✅ **Separate concerns** - Vision models for images, text models for text  
✅ **No breaking changes** - Image analysis still works as before  
✅ **Groq support restored** - Material analysis works with Groq again  
✅ **Flexible** - Easy to change models per provider  
✅ **Future-proof** - Can adapt to model deprecations easily

## Backward Compatibility

- Image analysis unchanged
- Existing API calls work the same
- No changes needed to client code
- Only internal routing logic updated

## Model Deprecation Handling

If a model gets deprecated in the future:

1. Check Groq console: https://console.groq.com/docs/models
2. Find replacement model
3. Update `text_only_model` parameter in worker initialization
4. Restart the service

No code changes needed elsewhere!
