# Deployment Guide - Image Analyzer Service

## Option 1: Railway (RECOMMENDED)

Railway is the easiest way to deploy Python FastAPI apps.

### Steps:

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Initialize Project**
   ```bash
   cd elocate-image-analyzer
   railway init
   ```

4. **Add Environment Variables**
   
   In Railway dashboard (https://railway.app):
   - Go to your project
   - Click "Variables"
   - Add these variables:
   
   ```
   GEMINI_API_KEY=AIzaSyBZkRPsr2BGfxU3vxY_h2Pz_XYOMm5oSPA
   API_KEY=XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk
   ALLOWED_ORIGINS=https://elocate.vercel.app,http://localhost:3000
   DATABASE_URL=postgresql://postgres.qnnkizacregmdsfgqrsw:AL+4kWTv%A+k9DK@db.qnnkizacregmdsfgqrsw.supabase.co:5432/postgres
   DB_USER=postgres.qnnkizacregmdsfgqrsw
   DB_PASSWORD=AL+4kWTv%A+k9DK
   PORT=8000
   ```

5. **Deploy**
   ```bash
   railway up
   ```

6. **Get Your URL**
   ```bash
   railway domain
   ```

Your service will be live at: `https://your-service.railway.app`

---

## Option 2: Render

### Steps:

1. **Create `render.yaml`** (already exists in project)

2. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push
   ```

3. **Deploy on Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select `elocate-image-analyzer` directory
   - Render will auto-detect settings from `render.yaml`

4. **Add Environment Variables** in Render dashboard:
   ```
   GEMINI_API_KEY=AIzaSyBZkRPsr2BGfxU3vxY_h2Pz_XYOMm5oSPA
   API_KEY=XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk
   ALLOWED_ORIGINS=https://elocate.vercel.app
   DATABASE_URL=postgresql://postgres.qnnkizacregmdsfgqrsw:AL+4kWTv%A+k9DK@db.qnnkizacregmdsfgqrsw.supabase.co:5432/postgres
   DB_USER=postgres.qnnkizacregmdsfgqrsw
   DB_PASSWORD=AL+4kWTv%A+k9DK
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment

Your service will be live at: `https://your-service.onrender.com`

---

## Option 3: Vercel (NOT RECOMMENDED for FastAPI)

⚠️ **Warning**: Vercel is designed for serverless functions, not long-running FastAPI apps. Use Railway or Render instead.

If you must use Vercel:

1. **Create `vercel.json`**
   ```json
   {
     "builds": [
       {
         "src": "app/main.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app/main.py"
       }
     ]
   }
   ```

2. **Create `api/index.py`**
   ```python
   from app.main import app
   ```

3. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

4. **Deploy**
   ```bash
   cd elocate-image-analyzer
   vercel
   ```

**Limitations on Vercel:**
- 10 second timeout (your requests may timeout)
- Cold starts (slow first request)
- No WebSocket support
- Limited for background tasks

---

## Option 4: Google Cloud Run

### Steps:

1. **Install Google Cloud SDK**
   ```bash
   # Download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Build and Deploy**
   ```bash
   cd elocate-image-analyzer
   
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/image-analyzer
   
   gcloud run deploy image-analyzer \
     --image gcr.io/YOUR_PROJECT_ID/image-analyzer \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY=AIzaSyBZkRPsr2BGfxU3vxY_h2Pz_XYOMm5oSPA,API_KEY=XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk,DATABASE_URL=postgresql://postgres.qnnkizacregmdsfgqrsw:AL+4kWTv%A+k9DK@db.qnnkizacregmdsfgqrsw.supabase.co:5432/postgres
   ```

---

## Recommended: Railway

**Why Railway?**
- ✓ Easiest setup
- ✓ Free tier available
- ✓ Automatic HTTPS
- ✓ Great for Python/FastAPI
- ✓ Built-in database support
- ✓ Simple environment variables
- ✓ Automatic deployments from Git

**Quick Start:**
```bash
npm install -g @railway/cli
cd elocate-image-analyzer
railway login
railway init
railway up
```

---

## After Deployment

### Update Your Frontend

In your Next.js app, update the API URL:

```typescript
// .env.local
NEXT_PUBLIC_IMAGE_ANALYZER_URL=https://your-service.railway.app
NEXT_PUBLIC_IMAGE_ANALYZER_API_KEY=XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk
```

### Test Your Deployment

```bash
# Health check
curl https://your-service.railway.app/health

# Test analyze endpoint
curl -X POST https://your-service.railway.app/api/v1/analyze \
  -H "X-API-Key: XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk" \
  -F "file=@test-image.jpg"
```

### Monitor Your Service

- **Railway**: https://railway.app/dashboard
- **Render**: https://dashboard.render.com
- **Logs**: Available in each platform's dashboard

---

## Troubleshooting

### Database Connection Issues
If database still doesn't connect after deployment:
1. Check environment variables are set correctly
2. Verify DATABASE_URL format
3. Check platform logs for errors
4. Service will work without database (graceful degradation)

### Gemini API Issues
If you hit quota limits:
1. Get new API key from https://ai.google.dev/
2. Update GEMINI_API_KEY environment variable
3. Redeploy or restart service

### CORS Issues
Add your frontend URL to ALLOWED_ORIGINS:
```
ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://elocate.vercel.app
```

---

## Cost Estimates

| Platform | Free Tier | Paid |
|----------|-----------|------|
| Railway | $5 credit/month | $5/month + usage |
| Render | 750 hours/month | $7/month |
| Vercel | Limited | Not ideal for this |
| Google Cloud Run | 2M requests/month | Pay per use |

**Recommendation**: Start with Railway's free tier.
