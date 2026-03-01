# Deployment Guide: E-locate Image Device Identification Service

This guide provides step-by-step instructions for deploying the Image Device Identification Service to various platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Variables](#environment-variables)
3. [Docker Deployment](#docker-deployment)
4. [Railway Deployment](#railway-deployment)
5. [Render Deployment](#render-deployment)
6. [Google Cloud Run Deployment](#google-cloud-run-deployment)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:

1. **Google Gemini API Key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Save it securely

2. **Service API Key**
   - Generate a secure random key for service authentication
   - Example: `openssl rand -hex 32`

3. **Frontend URL**
   - Know your Next.js frontend URL for CORS configuration
   - Example: `https://your-app.vercel.app`

## Environment Variables

All deployment methods require these environment variables:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key | `AIzaSy...` |
| `API_KEY` | Yes | Service authentication key | `a1b2c3d4...` |
| `ALLOWED_ORIGINS` | Yes | CORS allowed origins (comma-separated) | `https://app.vercel.app,https://app.com` |
| `MAX_FILE_SIZE_MB` | No | Maximum upload size in MB | `10` (default) |
| `LOG_LEVEL` | No | Logging level | `INFO` (default) |
| `REQUEST_TIMEOUT` | No | Request timeout in seconds | `30` (default) |
| `RATE_LIMIT` | No | Rate limit per IP | `10/minute` (default) |
| `PORT` | No | Server port (set by platform) | `8000` (default) |

## Docker Deployment

### Local Docker

1. Build the image:
   ```bash
   docker build -t elocate-image-analyzer .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -p 8000:8000 \
     -e GEMINI_API_KEY=your_gemini_key \
     -e API_KEY=your_api_key \
     -e ALLOWED_ORIGINS=http://localhost:3000 \
     --name image-analyzer \
     elocate-image-analyzer
   ```

3. Test the service:
   ```bash
   curl http://localhost:8000/health
   ```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  image-analyzer:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - API_KEY=${API_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
```

Run with:
```bash
docker-compose up -d
```

## Railway Deployment

Railway provides automatic deployments from Git repositories.

### Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
```

### Step 2: Login to Railway

```bash
railway login
```

### Step 3: Initialize Project

```bash
cd elocate-image-analyzer
railway init
```

Select "Create new project" and give it a name.

### Step 4: Configure Environment Variables

Option A - Via CLI:
```bash
railway variables set GEMINI_API_KEY=your_gemini_key
railway variables set API_KEY=your_api_key
railway variables set ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

Option B - Via Dashboard:
1. Go to https://railway.app/dashboard
2. Select your project
3. Click "Variables" tab
4. Add each environment variable

### Step 5: Deploy

```bash
railway up
```

Railway will:
- Detect the Dockerfile
- Build the image
- Deploy the service
- Assign a public URL

### Step 6: Get Service URL

```bash
railway domain
```

Or generate a domain:
```bash
railway domain generate
```

### Step 7: Configure Custom Domain (Optional)

1. Go to Railway dashboard
2. Select your service
3. Click "Settings" → "Domains"
4. Add your custom domain
5. Update DNS records as instructed

## Render Deployment

Render provides automatic deployments with a `render.yaml` configuration.

### Step 1: Connect Repository

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your Git repository (GitHub/GitLab)
4. Select the repository containing `elocate-image-analyzer`

### Step 2: Configure Service

Render will detect the `render.yaml` file automatically.

If not using `render.yaml`, configure manually:
- **Name**: `elocate-image-analyzer`
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` or your deployment branch
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Environment Variables

In the Render dashboard:
1. Go to "Environment" tab
2. Add each required variable:
   - `GEMINI_API_KEY`
   - `API_KEY`
   - `ALLOWED_ORIGINS`
   - `PYTHON_VERSION` = `3.11.0`

### Step 4: Deploy

Click "Create Web Service"

Render will:
- Clone your repository
- Install dependencies
- Start the service
- Assign a public URL (e.g., `https://your-service.onrender.com`)

### Step 5: Configure Health Checks

Render automatically uses the `/health` endpoint for health checks.

### Step 6: Custom Domain (Optional)

1. Go to "Settings" → "Custom Domain"
2. Add your domain
3. Update DNS records as instructed

## Google Cloud Run Deployment

Cloud Run provides serverless container deployment with automatic scaling.

### Step 1: Install Google Cloud SDK

Download from: https://cloud.google.com/sdk/docs/install

### Step 2: Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Step 3: Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 4: Build and Push Image

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/image-analyzer
```

### Step 5: Deploy to Cloud Run

```bash
gcloud run deploy image-analyzer \
  --image gcr.io/YOUR_PROJECT_ID/image-analyzer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --timeout 30s \
  --set-env-vars GEMINI_API_KEY=your_key,API_KEY=your_key,ALLOWED_ORIGINS=https://your-frontend.com
```

### Step 6: Get Service URL

The deployment output will show the service URL:
```
Service [image-analyzer] revision [image-analyzer-00001-abc] has been deployed and is serving 100 percent of traffic.
Service URL: https://image-analyzer-xxxxx-uc.a.run.app
```

### Step 7: Configure Custom Domain (Optional)

```bash
gcloud run domain-mappings create \
  --service image-analyzer \
  --domain your-domain.com \
  --region us-central1
```

### Step 8: Set Up Secret Manager (Recommended)

For better security, use Secret Manager:

```bash
# Create secrets
echo -n "your_gemini_key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your_api_key" | gcloud secrets create service-api-key --data-file=-

# Deploy with secrets
gcloud run deploy image-analyzer \
  --image gcr.io/YOUR_PROJECT_ID/image-analyzer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,API_KEY=service-api-key:latest \
  --set-env-vars ALLOWED_ORIGINS=https://your-frontend.com
```

## Post-Deployment Verification

After deploying to any platform, verify the service is working:

### 1. Health Check

```bash
curl https://your-service-url.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "gemini_api_available": true
}
```

### 2. API Documentation

Visit in browser:
- Swagger UI: `https://your-service-url.com/docs`
- ReDoc: `https://your-service-url.com/redoc`

### 3. Test Image Analysis

```bash
curl -X POST https://your-service-url.com/api/v1/analyze \
  -H "X-API-Key: your_api_key" \
  -F "file=@/path/to/device-image.jpg"
```

### 4. Test CORS

```bash
curl -X OPTIONS https://your-service-url.com/api/v1/analyze \
  -H "Origin: https://your-frontend.com" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

Check for CORS headers in response.

### 5. Monitor Logs

**Railway:**
```bash
railway logs
```

**Render:**
- View logs in dashboard under "Logs" tab

**Google Cloud Run:**
```bash
gcloud run services logs read image-analyzer --region us-central1
```

## Troubleshooting

### Issue: Health check fails

**Symptoms:** Service shows as unhealthy or doesn't start

**Solutions:**
1. Check logs for startup errors
2. Verify `GEMINI_API_KEY` is set correctly
3. Ensure port 8000 is exposed
4. Check if Gemini API is accessible from your deployment region

### Issue: CORS errors in frontend

**Symptoms:** Browser console shows CORS policy errors

**Solutions:**
1. Verify `ALLOWED_ORIGINS` includes your frontend URL
2. Ensure URL includes protocol (https://)
3. Check for trailing slashes (should not have them)
4. Restart service after updating environment variables

### Issue: 401 Unauthorized errors

**Symptoms:** API requests return 401 status

**Solutions:**
1. Verify `X-API-Key` header is included in requests
2. Check `API_KEY` environment variable matches
3. Ensure header name is exactly `X-API-Key` (case-sensitive)

### Issue: 503 Service Unavailable

**Symptoms:** Analysis requests fail with 503 status

**Solutions:**
1. Check Gemini API key is valid
2. Verify Gemini API quota hasn't been exceeded
3. Check network connectivity to Google APIs
4. Review logs for specific error messages

### Issue: Slow response times

**Symptoms:** Requests take longer than 10 seconds

**Solutions:**
1. Check Gemini API latency in logs
2. Increase `REQUEST_TIMEOUT` if needed
3. Consider deploying closer to users
4. Check image file sizes (optimize if >5MB)

### Issue: Rate limit errors

**Symptoms:** 429 Too Many Requests errors

**Solutions:**
1. Adjust `RATE_LIMIT` environment variable
2. Implement request queuing in frontend
3. Consider upgrading to higher tier plan
4. Add caching for repeated requests

### Issue: Memory errors

**Symptoms:** Service crashes or restarts frequently

**Solutions:**
1. Increase memory allocation (Cloud Run: `--memory 1Gi`)
2. Check for memory leaks in logs
3. Reduce `MAX_FILE_SIZE_MB` if needed
4. Ensure temporary files are cleaned up

## Monitoring and Maintenance

### Set Up Monitoring

**Railway:**
- Built-in metrics in dashboard
- Set up alerts for downtime

**Render:**
- View metrics in dashboard
- Configure email alerts

**Google Cloud Run:**
```bash
# View metrics
gcloud run services describe image-analyzer --region us-central1

# Set up alerts in Cloud Monitoring
```

### Regular Maintenance

1. **Update dependencies monthly:**
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   ```

2. **Monitor API usage:**
   - Check Gemini API quota usage
   - Review rate limit hits
   - Analyze error rates

3. **Review logs weekly:**
   - Check for unusual error patterns
   - Monitor processing times
   - Identify optimization opportunities

4. **Test with real images:**
   - Periodically test with various device types
   - Verify confidence scores are reasonable
   - Check database matching accuracy

## Support

For issues specific to:
- **Gemini API**: https://ai.google.dev/docs
- **Railway**: https://docs.railway.app
- **Render**: https://render.com/docs
- **Google Cloud Run**: https://cloud.google.com/run/docs

For E-locate platform issues, contact the development team.
