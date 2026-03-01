# Railway Deployment Guide

## Quick Deploy - 3 Steps

### Step 1: Import Environment Variables

Railway allows you to import environment variables from a JSON file.

**File to import:** `railway-env.json`

**How to import:**

1. Go to your Railway project dashboard
2. Click on your service
3. Go to the "Variables" tab
4. Click "Raw Editor" button (top right)
5. Copy the contents of `railway-env.json` and paste it
6. Click "Deploy" or "Save"

**Or use Railway CLI:**
```bash
# Install Railway CLI if not already installed
npm i -g @railway/cli

# Login
railway login

# Link to your project (or create new)
railway link

# Set variables from JSON file
railway variables --set-from-json railway-env.json
```

### Step 2: Deploy

**Option A: Via GitHub (Recommended)**
```bash
# Push your code to GitHub
git add .
git commit -m "Deploy to Railway"
git push origin main

# On Railway dashboard:
# 1. Click "New Project"
# 2. Select "Deploy from GitHub repo"
# 3. Choose your repository
# 4. Railway will auto-detect railway.json and deploy
```

**Option B: Via Railway CLI**
```bash
# Deploy directly
railway up

# Or deploy with logs
railway up --detach
railway logs
```

### Step 3: Update CORS Origins

Once deployed, Railway will give you a URL like:
`https://your-app.railway.app`

Update the `ALLOWED_ORIGINS` variable to include your Railway URL:

```json
{
  "ALLOWED_ORIGINS": "http://localhost:3000,https://elocate.vercel.app,https://your-app.railway.app"
}
```

---

## Environment Variables Explained

### Required Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `GEMINI_API_KEY` | Your API key | Google Gemini API key for image analysis |
| `API_KEY` | Your secret key | Service authentication key |
| `DATABASE_URL` | PostgreSQL URL | Full database connection string |

### Optional Variables (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | localhost:3000 | Comma-separated CORS origins |
| `MAX_FILE_SIZE_MB` | 10 | Maximum upload file size |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `REQUEST_TIMEOUT` | 30 | Request timeout in seconds |
| `RATE_LIMIT` | 10/minute | Rate limiting configuration |
| `DB_MIN_POOL_SIZE` | 1 | Minimum database connections |
| `DB_MAX_POOL_SIZE` | 10 | Maximum database connections |
| `DB_CONNECTION_TIMEOUT` | 30 | Database connection timeout |
| `DB_QUERY_TIMEOUT` | 50 | Database query timeout (ms) |
| `DB_REQUIRED` | false | Fail if database unavailable |
| `CATEGORY_MATCH_THRESHOLD` | 0.80 | Fuzzy match threshold for categories |
| `BRAND_MATCH_THRESHOLD` | 0.80 | Fuzzy match threshold for brands |
| `MODEL_MATCH_THRESHOLD` | 0.75 | Fuzzy match threshold for models |
| `QUERY_CACHE_TTL` | 300 | Cache time-to-live (seconds) |
| `QUERY_CACHE_MAX_SIZE` | 1000 | Maximum cache entries |

---

## Important Notes

### 1. Gemini API Key

⚠️ **The current API key is expired!**

Before deploying, get a new key:
1. Visit: https://makersuite.google.com/app/apikey
2. Create or renew your API key
3. Update `GEMINI_API_KEY` in Railway variables

### 2. Database URL

✅ **Already configured correctly**

The DATABASE_URL uses Supabase Transaction Pooler which works perfectly with Railway.

Format:
```
postgresql://user:password@host:port/database
```

### 3. CORS Origins

After deployment, add your Railway URL to `ALLOWED_ORIGINS`:

```
http://localhost:3000,https://elocate.vercel.app,https://your-app.railway.app
```

### 4. API Key Security

The `API_KEY` is used for service authentication. Keep it secret!

Clients must include it in requests:
```bash
curl -H "X-API-Key: your-api-key" https://your-app.railway.app/api/v1/analyze
```

---

## Railway Configuration Files

Your project includes these Railway-specific files:

### 1. `railway.json`
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

### 2. `Procfile`
```
web: bash start.sh
```

### 3. `start.sh`
```bash
#!/bin/bash
PORT=${PORT:-8000}
echo "Starting server on port $PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
```

Railway automatically uses these files for deployment.

---

## Deployment Checklist

- [ ] Update `GEMINI_API_KEY` with valid key
- [ ] Import `railway-env.json` to Railway
- [ ] Push code to GitHub (or use Railway CLI)
- [ ] Deploy on Railway
- [ ] Get Railway URL
- [ ] Update `ALLOWED_ORIGINS` with Railway URL
- [ ] Test health endpoint: `https://your-app.railway.app/health`
- [ ] Test API docs: `https://your-app.railway.app/docs`
- [ ] Test image analysis with sample image

---

## Testing After Deployment

### 1. Health Check
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-01T...",
  "gemini_api_available": true,
  "database_available": true
}
```

### 2. Test Endpoint
```bash
curl -H "X-API-Key: your-api-key" https://your-app.railway.app/test
```

### 3. Image Analysis
```bash
curl -X POST https://your-app.railway.app/api/v1/analyze \
  -H "X-API-Key: your-api-key" \
  -F "image=@test-image.jpg"
```

### 4. API Documentation
Visit: `https://your-app.railway.app/docs`

---

## Monitoring

### View Logs
```bash
# Via Railway CLI
railway logs

# Or via Railway dashboard
# Go to your service → Deployments → Click on deployment → View logs
```

### Check Metrics
Railway dashboard shows:
- CPU usage
- Memory usage
- Network traffic
- Request count

### Health Monitoring
Set up a health check monitor (like UptimeRobot) to ping:
```
https://your-app.railway.app/health
```

---

## Troubleshooting

### Deployment fails
1. Check Railway logs: `railway logs`
2. Verify all environment variables are set
3. Check `railway.json` is in root directory
4. Ensure `requirements.txt` is up to date

### Database connection fails
1. Verify `DATABASE_URL` is correct
2. Check Supabase is accessible from Railway
3. Test connection locally first
4. Check Railway logs for connection errors

### Gemini API errors
1. Verify API key is valid and not expired
2. Check API key has proper permissions
3. Test API key locally first
4. Check Railway logs for API errors

### CORS errors
1. Add your frontend URL to `ALLOWED_ORIGINS`
2. Include Railway URL in origins
3. Restart deployment after updating

---

## Scaling

Railway automatically scales based on traffic. You can configure:

### Memory Limits
Default: 512MB
Recommended: 1GB for production

### Replicas
Default: 1
Can scale horizontally for high traffic

### Database Pool
Adjust based on traffic:
- Low traffic: `DB_MAX_POOL_SIZE=5`
- Medium traffic: `DB_MAX_POOL_SIZE=10` (current)
- High traffic: `DB_MAX_POOL_SIZE=20`

---

## Cost Estimation

Railway pricing (as of 2026):
- Free tier: $5 credit/month
- Hobby plan: $5/month + usage
- Pro plan: $20/month + usage

Estimated costs for this app:
- Low traffic: ~$5-10/month
- Medium traffic: ~$15-25/month
- High traffic: ~$30-50/month

---

## Support

### Railway Support
- Documentation: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

### Project Support
- Check logs: `railway logs`
- Review documentation in this repo
- Test locally first: `python run.py`

---

## Quick Commands Reference

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
railway link

# Set variables
railway variables --set-from-json railway-env.json

# Deploy
railway up

# View logs
railway logs

# Open in browser
railway open

# Check status
railway status
```

---

## Next Steps After Deployment

1. ✅ Verify health endpoint returns "healthy"
2. ✅ Test image analysis with sample images
3. ✅ Update frontend to use Railway URL
4. ✅ Set up monitoring/alerts
5. ✅ Configure custom domain (optional)
6. ✅ Set up CI/CD pipeline (optional)

---

**Your Railway environment is ready to import!**

File: `railway-env.json`
