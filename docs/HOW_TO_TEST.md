# How to Test Your Deployed API

## Quick Start

Your API is deployed at: **https://elocate-python-production.up.railway.app**

---

## Current Status: 502 Error

The app is starting successfully but Railway can't reach it. See `RAILWAY_TROUBLESHOOTING.md` for fixes.

---

## Testing Methods

### Method 1: PowerShell Test Script (Automated)

```powershell
cd elocate-image-analyzer
.\test_railway_deployment.ps1
```

This tests:
- Root endpoint
- Health check
- Authentication
- API documentation

### Method 2: Manual curl Commands

```bash
# Health check
curl https://elocate-python-production.up.railway.app/health

# Root endpoint
curl https://elocate-python-production.up.railway.app/

# Test with API key
curl -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  https://elocate-python-production.up.railway.app/test
```

### Method 3: Browser Testing

Open these URLs in your browser:

1. **API Documentation:**
   https://elocate-python-production.up.railway.app/docs

2. **Test Interface:**
   https://elocate-python-production.up.railway.app/test-ui

3. **Health Check:**
   https://elocate-python-production.up.railway.app/health

### Method 4: Postman/Insomnia

Import this collection:

```json
{
  "name": "Elocate Image Analyzer",
  "requests": [
    {
      "name": "Health Check",
      "method": "GET",
      "url": "https://elocate-python-production.up.railway.app/health"
    },
    {
      "name": "Analyze Image",
      "method": "POST",
      "url": "https://elocate-python-production.up.railway.app/api/v1/analyze",
      "headers": {
        "X-API-Key": "XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk"
      },
      "body": {
        "type": "formdata",
        "formdata": [
          {
            "key": "image",
            "type": "file",
            "src": "path/to/image.jpg"
          }
        ]
      }
    }
  ]
}
```

---

## Test Endpoints

### 1. Health Check
```bash
GET /health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-01T...",
  "gemini_api_available": true,
  "database_available": true
}
```

**Status Codes:**
- `200 OK` - Service healthy
- `503 Service Unavailable` - Service degraded

### 2. Root Endpoint
```bash
GET /
```

**Expected Response:**
```json
{
  "service": "Image Device Identification API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "analyze": "/api/v1/analyze",
    "health": "/health",
    "test": "/test",
    "test_interface": "/test-ui",
    "docs": "/docs"
  }
}
```

### 3. Test Endpoint (Requires API Key)
```bash
GET /test
Headers: X-API-Key: your-api-key
```

**Expected Response:**
```json
{
  "success": true,
  "message": "API is working correctly",
  "timestamp": "2026-03-01T..."
}
```

**Status Codes:**
- `200 OK` - Test successful
- `401 Unauthorized` - Missing API key
- `403 Forbidden` - Invalid API key

### 4. Image Analysis (Requires API Key)
```bash
POST /api/v1/analyze
Headers: X-API-Key: your-api-key
Body: multipart/form-data with image file
```

**Example with curl:**
```bash
curl -X POST \
  https://elocate-python-production.up.railway.app/api/v1/analyze \
  -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  -F "image=@phone.jpg"
```

**Expected Response:**
```json
{
  "success": true,
  "timestamp": "2026-03-01T...",
  "processingTimeMs": 1234,
  "data": {
    "category": "Smartphone",
    "brand": "Apple",
    "model": "iPhone 14 Pro",
    "confidence": 0.95,
    "database_match": {
      "category_id": "uuid",
      "brand_id": "uuid",
      "model_id": "uuid",
      "recyclability_score": 85
    }
  }
}
```

---

## Testing with Different Images

### Test Image 1: Smartphone
```bash
curl -X POST \
  https://elocate-python-production.up.railway.app/api/v1/analyze \
  -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  -F "image=@smartphone.jpg"
```

### Test Image 2: Laptop
```bash
curl -X POST \
  https://elocate-python-production.up.railway.app/api/v1/analyze \
  -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  -F "image=@laptop.jpg"
```

### Test Image 3: Tablet
```bash
curl -X POST \
  https://elocate-python-production.up.railway.app/api/v1/analyze \
  -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  -F "image=@tablet.jpg"
```

---

## Testing from Frontend

### JavaScript/TypeScript Example

```typescript
const API_URL = 'https://elocate-python-production.up.railway.app';
const API_KEY = 'XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk';

// Health check
async function checkHealth() {
  const response = await fetch(`${API_URL}/health`);
  const data = await response.json();
  console.log('Health:', data);
}

// Analyze image
async function analyzeImage(imageFile) {
  const formData = new FormData();
  formData.append('image', imageFile);

  const response = await fetch(`${API_URL}/api/v1/analyze`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY
    },
    body: formData
  });

  const data = await response.json();
  return data;
}

// Usage
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const result = await analyzeImage(file);
  console.log('Analysis:', result);
});
```

### React Example

```tsx
import { useState } from 'react';

const API_URL = 'https://elocate-python-production.up.railway.app';
const API_KEY = 'XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk';

function ImageAnalyzer() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch(`${API_URL}/api/v1/analyze`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_KEY
        },
        body: formData
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input type="file" onChange={handleImageUpload} accept="image/*" />
      {loading && <p>Analyzing...</p>}
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}
```

---

## Monitoring & Debugging

### Check Railway Logs
```bash
railway logs
```

### Check Service Status
```bash
railway status
```

### Check Environment Variables
```bash
railway variables
```

### View Metrics
Go to Railway dashboard → Your service → Metrics

---

## Expected Response Times

| Endpoint | Expected Time |
|----------|---------------|
| `/health` | <100ms |
| `/` | <50ms |
| `/test` | <100ms |
| `/api/v1/analyze` | 1-3 seconds |

---

## Troubleshooting

### 502 Bad Gateway
- **Cause:** App not responding or wrong port
- **Fix:** See `RAILWAY_TROUBLESHOOTING.md`
- **Check:** `railway logs` for errors

### 401 Unauthorized
- **Cause:** Missing or invalid API key
- **Fix:** Add `X-API-Key` header with correct key

### 413 Payload Too Large
- **Cause:** Image file too large
- **Fix:** Resize image to < 10MB

### 429 Too Many Requests
- **Cause:** Rate limit exceeded
- **Fix:** Wait 1 minute, then retry

### 500 Internal Server Error
- **Cause:** Server error (Gemini API, database, etc.)
- **Fix:** Check logs, verify API key and database

---

## Success Checklist

- [ ] Health endpoint returns "healthy"
- [ ] Root endpoint returns service info
- [ ] Test endpoint works with API key
- [ ] Test endpoint fails without API key
- [ ] Image analysis returns device info
- [ ] Database matching works
- [ ] Response times are acceptable
- [ ] CORS works from frontend
- [ ] API documentation accessible
- [ ] No errors in Railway logs

---

## Quick Test Commands

```bash
# Test everything at once
.\test_railway_deployment.ps1

# Or manually:
curl https://elocate-python-production.up.railway.app/health
curl https://elocate-python-production.up.railway.app/
curl -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  https://elocate-python-production.up.railway.app/test
```

---

## Support

- **Railway Logs:** `railway logs`
- **Railway Status:** `railway status`
- **API Docs:** https://elocate-python-production.up.railway.app/docs
- **Troubleshooting:** See `RAILWAY_TROUBLESHOOTING.md`

---

**Once the 502 error is fixed, all these tests should pass!**
