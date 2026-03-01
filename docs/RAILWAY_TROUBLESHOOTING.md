# Railway Deployment Troubleshooting

## Current Issue: 502 Bad Gateway

**Status:** App starts successfully but returns 502 errors

### What the Logs Show

✅ **Working:**
- Container starts
- Middleware configured
- Database connected (psycopg2)
- Gemini API verified
- Service started successfully
- Uvicorn running on http://0.0.0.0:8000

❌ **Problem:**
- 502 Bad Gateway on all endpoints
- Railway can't reach the application

### Root Cause

The issue is likely that Railway assigns a dynamic `PORT` environment variable, but the app might not be using it correctly.

---

## Solution 1: Verify PORT Environment Variable

Railway automatically sets the `PORT` variable. Your app should use it.

### Check Current Configuration

Your `start.sh` already handles this:
```bash
PORT=${PORT:-8000}
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
```

### Verify in Railway Dashboard

1. Go to Railway dashboard
2. Click on your service
3. Go to "Variables" tab
4. Check if `PORT` is set (Railway sets this automatically)

---

## Solution 2: Check Railway Configuration

### Verify railway.json

Your `railway.json` should look like this:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "bash start.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Verify Procfile

Your `Procfile` should have:
```
web: bash start.sh
```

---

## Solution 3: Redeploy

Sometimes Railway needs a fresh deployment:

```bash
# Method 1: Via CLI
railway up --detach

# Method 2: Via Dashboard
# Go to Railway dashboard → Deployments → Click "Redeploy"

# Method 3: Push to GitHub
git add .
git commit -m "Fix Railway deployment"
git push origin main
```

---

## Solution 4: Check Health Timeout

Railway has a health check timeout. If your app takes too long to start, it might fail.

### Current Startup Time
From logs: ~14 seconds (database connection retries)

### Reduce Startup Time

Update `.env` or Railway variables:
```env
# Reduce connection timeout
DB_CONNECTION_TIMEOUT=10

# Reduce retries (psycopg2 works anyway)
# Or set DB_REQUIRED=false to skip if slow
```

---

## Solution 5: Force Port Binding

Update `start.sh` to explicitly use Railway's PORT:

```bash
#!/bin/bash
# Get PORT from Railway (required)
PORT=${PORT:-8000}

echo "Starting server on port $PORT"
echo "Host: 0.0.0.0"

# Start uvicorn with explicit port
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info
```

---

## Solution 6: Check Railway Service Settings

### In Railway Dashboard:

1. **Service Settings:**
   - Go to your service
   - Click "Settings"
   - Check "Start Command": should be `bash start.sh`

2. **Networking:**
   - Ensure "Public Networking" is enabled
   - Check if domain is properly configured

3. **Health Checks:**
   - Railway might be checking `/` or `/health`
   - Ensure these endpoints respond quickly

---

## Debugging Steps

### Step 1: Check Recent Logs
```bash
railway logs
```

Look for:
- Port binding messages
- Error messages after "Application startup complete"
- Connection refused errors

### Step 2: Check Environment Variables
```bash
railway variables
```

Verify:
- `PORT` is set (or not set - Railway sets it automatically)
- `GEMINI_API_KEY` is correct
- `DATABASE_URL` is correct

### Step 3: Test Locally with Railway Port
```bash
# Test with Railway-style PORT variable
$env:PORT=8080
python run.py

# Then test
curl http://localhost:8080/health
```

### Step 4: Check Railway Status
```bash
railway status
```

Should show:
- Service: Running
- Deployment: Active

---

## Quick Fixes to Try

### Fix 1: Update start.sh
```bash
#!/bin/bash
set -e  # Exit on error

# Railway sets PORT automatically
PORT=${PORT:-8000}

echo "=== Starting Elocate Image Analyzer ==="
echo "Port: $PORT"
echo "Host: 0.0.0.0"

# Start with explicit settings
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info \
  --access-log
```

### Fix 2: Update railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "bash start.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300
  }
}
```

### Fix 3: Simplify Startup

Create `railway_start.sh`:
```bash
#!/bin/bash
# Simplified Railway startup
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Update `railway.json`:
```json
{
  "deploy": {
    "startCommand": "bash railway_start.sh"
  }
}
```

---

## Testing After Fix

### 1. Wait for Deployment
```bash
railway status
# Wait until status shows "Running"
```

### 2. Check Logs
```bash
railway logs
# Look for "Uvicorn running on http://0.0.0.0:XXXX"
```

### 3. Test Endpoints
```bash
# Health check
curl https://elocate-python-production.up.railway.app/health

# Root
curl https://elocate-python-production.up.railway.app/

# Should return JSON, not 502
```

### 4. Run Test Script
```powershell
.\test_railway_deployment.ps1
```

---

## Common Railway Issues

### Issue: "Application failed to respond"
**Cause:** App not binding to correct port or host
**Fix:** Ensure `--host 0.0.0.0` and `--port $PORT`

### Issue: "502 Bad Gateway"
**Cause:** App crashed or not responding
**Fix:** Check logs for errors, verify startup

### Issue: "Service Unavailable"
**Cause:** Deployment in progress or failed
**Fix:** Wait for deployment or redeploy

### Issue: Slow startup causing timeout
**Cause:** Database connection retries taking too long
**Fix:** Reduce timeouts or set `DB_REQUIRED=false`

---

## Recommended Actions

### Immediate Actions:

1. **Update start.sh** with explicit logging
2. **Redeploy** the service
3. **Check logs** after deployment
4. **Test endpoints** once running

### If Still Failing:

1. **Simplify startup** - remove database connection temporarily
2. **Test with minimal config** - just return "Hello World"
3. **Check Railway dashboard** for any service issues
4. **Contact Railway support** if infrastructure issue

---

## Success Indicators

When working correctly, you should see:

### In Logs:
```
Starting server on port 8000
INFO: Started server process [1]
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

### In Tests:
```
✓ Status: healthy
✓ Database Available: true
✓ Gemini API Available: true
```

### In Browser:
- https://elocate-python-production.up.railway.app/ → JSON response
- https://elocate-python-production.up.railway.app/docs → Swagger UI
- https://elocate-python-production.up.railway.app/health → Health status

---

## Need Help?

### Railway Support:
- Dashboard: https://railway.app
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

### Check These:
1. Railway service logs: `railway logs`
2. Railway status: `railway status`
3. Railway variables: `railway variables`
4. Local test: `python run.py` (should work locally)

---

**Next Step:** Try redeploying with `railway up` and check logs immediately after.
