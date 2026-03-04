# Text-Only LLM Implementation

## Overview

Added text-only generation capability to the LLM Router Service to support material analysis and other text-based tasks without requiring image input.

## Changes Made

### 1. LLMWorker Class (`app/services/llm_router.py`)

Added text-only generation methods for each provider:

#### New Methods:
- `generate_text_only(prompt: str)` - Main dispatcher for text-only generation
- `_generate_gemini_text_only(prompt: str)` - Gemini text-only implementation
- `_generate_openai_text_only(prompt: str)` - OpenAI text-only implementation
- `_generate_groq_text_only(prompt: str)` - Groq text-only implementation

#### Implementation Details:

**Gemini:**
```python
async def _generate_gemini_text_only(self, prompt: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt]
        )
    )
    return response.text
```

**OpenAI:**
```python
async def _generate_openai_text_only(self, prompt: str) -> str:
    response = await self.client.chat.completions.create(
        model=self.model_name,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

**Groq:**
```python
async def _generate_groq_text_only(self, prompt: str) -> str:
    response = await self.client.chat.completions.create(
        model=self.model_name,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

### 2. LLMRouterService Class (`app/services/llm_router.py`)

Added text-only routing with fallback support:

#### New Methods:
- `_call_llm_text_only_with_fallback(prompt: str)` - Internal method with fallback logic
- `generate_text_only(prompt: str)` - Public API for text-only generation

#### Implementation:
```python
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
```

### 3. Material Analyzer Service (`app/services/material_analyzer.py`)

Updated to use the new text-only generation method:

#### Before:
```python
# Created dummy 1x1 pixel image
img = Image.new('RGB', (1, 1), color='white')
img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
image_bytes = img_bytes.getvalue()

# Used internal method with dummy image
response_data = await llm_service._call_llm_with_fallback(image_bytes, prompt)
```

#### After:
```python
# Direct text-only generation
response_data = await llm_service.generate_text_only(prompt)
```

## Benefits

### 1. Cleaner Architecture
- No need for dummy images
- Separate concerns: image analysis vs text analysis
- Clear API for different use cases

### 2. Better Performance
- No image encoding/decoding overhead
- Faster for text-only tasks
- Reduced memory usage

### 3. Provider Compatibility
- Works with all three providers (Gemini, OpenAI, Groq)
- Proper fallback and retry logic
- Consistent error handling

### 4. Maintainability
- Existing image analysis code untouched
- New functionality in separate methods
- Easy to extend for future text-only tasks

## Usage

### For Material Analysis:
```python
from app.services.llm_router import llm_service

prompt = "Analyze materials in Samsung Galaxy S21..."
response = await llm_service.generate_text_only(prompt)
# Returns parsed JSON dict
```

### For Other Text Tasks:
```python
# Any text-based LLM task can now use this
prompt = "Your text prompt here..."
response = await llm_service.generate_text_only(prompt)
```

## Fallback Behavior

The text-only generation follows the same fallback pattern as image analysis:

1. Try current worker
2. If fails (rate limit, timeout, error), switch to next worker
3. Log the switch with reason
4. Retry with new worker
5. Continue until success or all workers exhausted

## Testing

All three providers should now work for material analysis:

### Gemini:
- Uses `generate_content` with text-only prompt
- No image part in contents

### OpenAI:
- Uses `chat.completions.create` with text message
- No image_url in content
- JSON response format enforced

### Groq:
- Uses `chat.completions.create` with text message
- No image_url in content
- JSON response format enforced

## Backward Compatibility

- All existing image analysis code unchanged
- Existing methods still work as before
- New methods are additive only
- No breaking changes

## Future Enhancements

This text-only capability can be used for:
- Price estimation
- Device specifications lookup
- Recycling guidelines generation
- Material composition analysis
- Market rate queries
- Any other text-based LLM tasks
