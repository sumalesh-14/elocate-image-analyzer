# LLM Priority Configuration

## Overview

The system now supports separate LLM priority orders for different types of analysis:
- **Image Analysis**: Device identification from photos
- **Material Analysis**: Text-based material composition analysis

This allows you to optimize which LLM provider is used first based on the task type.

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Image Analysis LLM Priority (for device photo identification)
IMAGE_ANALYSIS_LLM_PRIORITY=gemini,openai,groq

# Material Analysis LLM Priority (for text-based material analysis)
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
```

### Format

- Comma-separated list of provider names
- Valid providers: `gemini`, `openai`, `groq`
- Order matters: first provider is tried first
- Case-insensitive

## Default Priorities

If not configured, the system uses these defaults:

### Image Analysis (Default)
```
gemini → openai → groq
```

**Reasoning:**
- Gemini has excellent vision capabilities
- OpenAI GPT-4o-mini is a good fallback
- Groq vision model as last resort

### Material Analysis (Default)
```
groq → gemini → openai
```

**Reasoning:**
- Groq is fast and cost-effective for text
- Gemini is reliable for structured output
- OpenAI as final fallback

## How It Works

### Image Analysis Flow

1. User uploads device image
2. System uses `IMAGE_ANALYSIS_LLM_PRIORITY` order
3. Tries first provider (e.g., Gemini)
4. If fails (rate limit, timeout, error), tries next provider
5. Continues until success or all providers exhausted

### Material Analysis Flow

1. User requests material analysis
2. System uses `MATERIAL_ANALYSIS_LLM_PRIORITY` order
3. Tries first provider (e.g., Groq)
4. If fails, tries next provider
5. Continues until success or all providers exhausted

## Example Configurations

### Cost-Optimized (Groq First)
```env
IMAGE_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
```

### Quality-Optimized (Gemini First)
```env
IMAGE_ANALYSIS_LLM_PRIORITY=gemini,openai,groq
MATERIAL_ANALYSIS_LLM_PRIORITY=gemini,openai,groq
```

### Speed-Optimized (Groq for Text, Gemini for Images)
```env
IMAGE_ANALYSIS_LLM_PRIORITY=gemini,groq,openai
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
```

### OpenAI First (If You Have Credits)
```env
IMAGE_ANALYSIS_LLM_PRIORITY=openai,gemini,groq
MATERIAL_ANALYSIS_LLM_PRIORITY=openai,gemini,groq
```

## Models Used

### Image Analysis (Vision Models)
- **Gemini**: `gemini-2.5-flash` (vision)
- **OpenAI**: `gpt-4o-mini` (vision)
- **Groq**: `llama-3.2-11b-vision-preview` (vision)

### Material Analysis (Text Models)
- **Gemini**: `gemini-2.5-flash` (text)
- **OpenAI**: `gpt-4o-mini` (text)
- **Groq**: `llama-3.3-70b-versatile` (text)

## Monitoring

The system logs which provider is being used:

### Image Analysis Logs
```
🤖  Routing task to LLM: Gemini (Key #1)
```

### Material Analysis Logs
```
🤖  Attempting with: Groq (Key #1) (llama-3.3-70b-versatile)
✅  Success! Found 13 materials
```

## Fallback Behavior

### When a Provider Fails

The system automatically tries the next provider in the priority list:

```
🤖  Attempting with: Groq (Key #1) (llama-3.3-70b-versatile)
⚠️   Groq (Key #1) failed (Timeout). Trying Gemini (Key #1)...
🤖  Attempting with: Gemini (Key #1) (gemini-2.5-flash)
✅  Success! Found 13 materials
```

### Common Failure Reasons

- **Rate Limit**: Provider's rate limit exceeded
- **Timeout**: Request took too long
- **API Error**: Provider returned an error
- **Model Decommissioned**: Model no longer available

## Best Practices

### 1. Test Your Configuration
After changing priorities, test both endpoints:
- Image analysis: Upload a device photo
- Material analysis: Request material breakdown

### 2. Monitor Costs
Different providers have different pricing:
- Groq: Generally cheapest
- Gemini: Good balance
- OpenAI: Most expensive

### 3. Consider Rate Limits
If you hit rate limits frequently:
- Add more API keys for the same provider
- Reorder priorities to use less-limited providers first

### 4. Balance Speed vs Quality
- Groq: Fastest
- Gemini: Good balance
- OpenAI: Highest quality (but slower)

## Troubleshooting

### All Providers Failing

Check:
1. API keys are valid and not expired
2. You have credits/quota remaining
3. Network connectivity is working
4. Models haven't been decommissioned

### Wrong Provider Being Used

Check:
1. `.env` file has correct priority order
2. Server was restarted after changing `.env`
3. No typos in provider names

### Inconsistent Results

This is normal - different LLMs may give slightly different results. If consistency is critical:
- Use only one provider
- Set priority to: `provider,provider,provider`

## Advanced: Per-Key Priority

If you have multiple keys for the same provider, they're all tried in order before moving to the next provider:

```
Priority: groq,gemini,openai

Workers:
1. Groq (Key #1)
2. Groq (Key #2)      ← Both Groq keys tried first
3. Gemini (Key #1)
4. Gemini (Key #2)    ← Then all Gemini keys
5. OpenAI (Key #1)    ← Finally OpenAI
```

## Summary

- Two separate priority configurations for different tasks
- Fully configurable via `.env` file
- Automatic fallback on failure
- Detailed logging for monitoring
- No code changes needed - just update `.env` and restart
