# Gemini API Quota - Quick Reference Card

## 🔴 Your Current Status

**API Key:** ❌ EXPIRED  
**Action Required:** Get a new API key

---

## 🔗 Quick Links (Click to Open)

### 1. Get New API Key (START HERE)
**https://aistudio.google.com/app/apikey**
- Click "Create API Key"
- Copy the new key
- Update your `.env` file

### 2. Check Quota Usage
**https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas**
- View your rate limits
- See remaining quota
- Check when it resets

### 3. View Usage Metrics
**https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics**
- See request graphs
- Monitor usage patterns
- Track errors

### 4. Check Billing (Optional)
**https://console.cloud.google.com/billing**
- Upgrade to paid tier
- View costs
- Set budget alerts

---

## 📊 Free Tier Limits

| Metric | Limit | Your App Impact |
|--------|-------|-----------------|
| **Requests/Minute** | 15 | Can analyze 15 images/min |
| **Requests/Day** | 1,500 | Can analyze 1,500 images/day |
| **Tokens/Minute** | 1M | Plenty for image analysis |

**Quota Resets:** Midnight Pacific Time (daily)

---

## ✅ How to Fix Your API Key

### Step 1: Get New Key
```
1. Visit: https://aistudio.google.com/app/apikey
2. Click "Create API Key" button
3. Select your project (or create new)
4. Copy the API key
```

### Step 2: Update .env File
```env
# Open: elocate-image-analyzer/.env
# Replace this line:
GEMINI_API_KEY=AIzaSyBZkRPsr2BGfxU3vxY_h2Pz_XYOMm5oSPA

# With your new key:
GEMINI_API_KEY=your-new-api-key-here
```

### Step 3: Test It
```bash
cd elocate-image-analyzer
python test_gemini_quota.py
```

### Step 4: Restart Server
```bash
# Stop current server (Ctrl+C)
# Start again:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🚨 Common Error Messages

### "API key expired"
- **Cause:** Your API key has expired
- **Fix:** Get a new key from Google AI Studio
- **Link:** https://aistudio.google.com/app/apikey

### "Quota exceeded" or "Resource exhausted"
- **Cause:** Hit daily/minute limit
- **Fix:** Wait for quota reset or upgrade to paid
- **Check:** https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

### "429 Too Many Requests"
- **Cause:** Too many requests too fast
- **Fix:** Wait 1 minute, then retry
- **Prevention:** Your app has rate limiting built-in

### "API key not valid"
- **Cause:** Wrong API key or not enabled
- **Fix:** Verify key at Google AI Studio
- **Enable API:** https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com

---

## 💰 Upgrade to Paid (If Needed)

### When to Upgrade?
- Need more than 1,500 requests/day
- Need faster rate limits
- Running production service

### Pricing (gemini-1.5-flash)
- **Input:** $0.075 per 1M tokens
- **Output:** $0.30 per 1M tokens
- **Typical image analysis:** ~$0.001 per request

### How to Upgrade
1. Go to: https://console.cloud.google.com/billing
2. Enable billing for your project
3. Quotas automatically increase
4. Pay only for what you use

---

## 🧪 Test Commands

### Check API Key Status
```bash
python test_gemini_quota.py
```

### Test Full Application
```bash
# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check health
curl http://localhost:8000/health

# Should show:
# "gemini_api_available": true
```

### Test Image Analysis
```bash
# Visit in browser:
http://localhost:8000/test-ui

# Or use API:
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: your-api-key" \
  -F "image=@test-image.jpg"
```

---

## 📈 Monitor Your Usage

### Daily Check
1. Visit: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics
2. Check request count
3. Verify no errors
4. Monitor trends

### Set Up Alerts
1. Go to: https://console.cloud.google.com/monitoring
2. Create alert policy
3. Set threshold at 80% of quota
4. Get email notifications

---

## 🎯 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| API key expired | Get new key at aistudio.google.com |
| Can't see quota | Enable API at console.cloud.google.com |
| Quota not updating | Wait 5-10 minutes for metrics |
| Need more quota | Upgrade to paid tier |
| 429 errors | Reduce request rate or wait |

---

## 📞 Support Resources

- **Google AI Studio:** https://aistudio.google.com
- **Documentation:** https://ai.google.dev/docs
- **API Reference:** https://ai.google.dev/api
- **Support:** https://support.google.com/ai-platform
- **Community:** https://discuss.ai.google.dev

---

## ✨ Summary

**Current Issue:** API key expired  
**Quick Fix:** Get new key at https://aistudio.google.com/app/apikey  
**Test Command:** `python test_gemini_quota.py`  
**Free Tier:** 15 req/min, 1,500 req/day  

**After fixing, you can deploy! 🚀**
