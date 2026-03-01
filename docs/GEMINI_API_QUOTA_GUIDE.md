# Gemini API Quota Guide

## How to Check Your Gemini API Quota

### Method 1: Google AI Studio Dashboard (Recommended)

1. **Visit Google AI Studio:**
   - Go to: https://aistudio.google.com/app/apikey
   - Or: https://makersuite.google.com/app/apikey

2. **View Your API Keys:**
   - You'll see all your API keys listed
   - Each key shows its status (Active, Expired, etc.)

3. **Check Quota Usage:**
   - Click on "View in Google Cloud Console" link
   - Or go directly to: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

4. **View Detailed Metrics:**
   - Go to: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics
   - This shows:
     - Requests per minute
     - Requests per day
     - Tokens used
     - Error rates

### Method 2: Google Cloud Console

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com

2. **Navigate to APIs & Services:**
   - Click "APIs & Services" → "Dashboard"
   - Search for "Generative Language API"

3. **View Quotas:**
   - Click "Quotas & System Limits"
   - Filter by "Generative Language API"
   - You'll see:
     - Requests per minute (RPM)
     - Requests per day (RPD)
     - Tokens per minute (TPM)

4. **View Usage:**
   - Click "Metrics" tab
   - Select time range (Last hour, day, week, month)
   - View graphs of API usage

### Method 3: Test Your API Key (Quick Check)

Run the test script below to check if your API key is working.

---

## Gemini API Free Tier Limits (2024-2026)

### Free Tier Quotas

| Model | RPM (Requests/Min) | RPD (Requests/Day) | TPM (Tokens/Min) |
|-------|-------------------|-------------------|------------------|
| gemini-1.5-flash | 15 | 1,500 | 1,000,000 |
| gemini-1.5-pro | 2 | 50 | 32,000 |
| gemini-pro-vision | 60 | - | 120,000 |

**Your app uses:** `gemini-1.5-flash` (best for image analysis)

### What Counts as Usage?

- ✅ Each image analysis request = 1 request
- ✅ Tokens = Input (image + prompt) + Output (JSON response)
- ✅ Failed requests also count toward quota
- ✅ Retries count as separate requests

### When Does Quota Reset?

- **Per Minute:** Resets every 60 seconds
- **Per Day:** Resets at midnight Pacific Time (PT)

---

## Common Quota Issues

### 1. "API key expired"
**Error Message:** `API key expired. Please renew the API key.`

**Solution:**
- Your API key has expired (not quota issue)
- Create a new API key at: https://aistudio.google.com/app/apikey
- Update `.env` file with new key

### 2. "Quota exceeded"
**Error Message:** `Resource has been exhausted (e.g. check quota).`

**Solution:**
- You've hit the rate limit (RPM or RPD)
- Wait for quota to reset
- Or upgrade to paid tier

### 3. "Rate limit exceeded"
**Error Message:** `429 Too Many Requests`

**Solution:**
- Too many requests in short time
- Implement exponential backoff
- Reduce request frequency

---

## How to Monitor Quota in Real-Time

### Option 1: Google Cloud Monitoring

1. Go to: https://console.cloud.google.com/monitoring
2. Create a dashboard
3. Add metrics:
   - `serviceruntime.googleapis.com/api/request_count`
   - `serviceruntime.googleapis.com/quota/exceeded`
4. Set up alerts for quota warnings

### Option 2: Check via API (Programmatic)

Use the test script below to check your API status.

---

## Quota Management Best Practices

### 1. Implement Rate Limiting
```python
# Already implemented in your app
RATE_LIMIT=10/minute  # Adjust based on your quota
```

### 2. Cache Results
```python
# Already implemented in your app
QUERY_CACHE_TTL=300  # Cache for 5 minutes
```

### 3. Handle Quota Errors Gracefully
```python
# Your app already handles this
try:
    response = gemini_api.analyze(image)
except QuotaExceeded:
    return "Service temporarily unavailable"
```

### 4. Monitor Usage
- Check dashboard daily
- Set up alerts at 80% quota
- Track usage patterns

---

## Upgrading to Paid Tier

If you need more quota:

### Pay-as-you-go Pricing (2024-2026)

| Model | Input Price | Output Price |
|-------|------------|--------------|
| gemini-1.5-flash | $0.075 / 1M tokens | $0.30 / 1M tokens |
| gemini-1.5-pro | $1.25 / 1M tokens | $5.00 / 1M tokens |

**To upgrade:**
1. Go to: https://console.cloud.google.com/billing
2. Enable billing for your project
3. Quotas automatically increase
4. You'll be charged based on usage

---

## Checking Quota Status

### Quick Status Check URLs

1. **API Keys:** https://aistudio.google.com/app/apikey
2. **Quotas:** https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
3. **Metrics:** https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics
4. **Billing:** https://console.cloud.google.com/billing

### What to Look For

✅ **Healthy Status:**
- API key shows "Active"
- Usage < 80% of quota
- No error spikes in metrics
- Response times < 2 seconds

⚠️ **Warning Signs:**
- Usage > 80% of quota
- Increasing error rates
- 429 errors in logs
- Slow response times

❌ **Critical Issues:**
- API key expired
- Quota exceeded
- All requests failing
- Billing issues

---

## Troubleshooting Quota Issues

### Issue: "Can't see my quota"

**Solution:**
1. Make sure you're logged into the correct Google account
2. Verify the API is enabled: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
3. Check you're viewing the correct project

### Issue: "Quota shows 0/0"

**Solution:**
1. API might not be enabled
2. Go to: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
3. Click "Enable"

### Issue: "Usage not updating"

**Solution:**
- Metrics can take 5-10 minutes to update
- Refresh the page
- Check "Last updated" timestamp

---

## Test Your API Key Now

Run this command to test your current API key:

```bash
cd elocate-image-analyzer
python test_gemini_quota.py
```

This will:
- ✅ Check if API key is valid
- ✅ Test API connectivity
- ✅ Show current quota status
- ✅ Estimate remaining requests

---

## Summary

### To Check Quota:
1. **Quick Check:** https://aistudio.google.com/app/apikey
2. **Detailed View:** https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
3. **Usage Metrics:** https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics

### Your Current Status:
- API Key: ⚠️ **EXPIRED** (needs renewal)
- Quota: Unknown (check after getting new key)
- Model: gemini-1.5-flash
- Free Tier: 15 RPM, 1,500 RPD

### Next Steps:
1. Get new API key from Google AI Studio
2. Update `.env` file
3. Run test script to verify
4. Monitor usage in Google Cloud Console

---

**Need Help?**
- Google AI Studio: https://aistudio.google.com
- Documentation: https://ai.google.dev/docs
- Support: https://support.google.com/ai-platform
