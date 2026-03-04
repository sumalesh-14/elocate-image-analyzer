# 🚂 Railway Deployment - Complete Guide

This guide will help you deploy your E-Waste Image Analyzer to Railway in minutes.

---

## 📚 Documentation Files

We've created several guides to help you:

| File | Purpose | When to Use |
|------|---------|-------------|
| **RAILWAY_QUICK_START.md** | 5-minute deployment | First-time deployment, need it fast |
| **RAILWAY_DEPLOYMENT_GUIDE.md** | Complete step-by-step guide | Detailed instructions, troubleshooting |
| **DEPLOYMENT_CHECKLIST.md** | Verification checklist | Ensure nothing is missed |
| **.env.railway** | Environment variables template | Copy to Railway Variables tab |

---

## ⚡ Quick Start (5 Minutes)

### 1. Prerequisites

- Railway account: [railway.app](https://railway.app/)
- Code in GitHub/GitLab
- API keys ready (Gemini, OpenAI, or Groq)

### 2. Deploy

```bash
# 1. Go to Railway
https://railway.app/

# 2. New Project → Deploy from GitHub repo

# 3. Select your repository

# 4. Add environment variables (see .env.railway)

# 5. Wait for deployment (2-3 minutes)

# 6. Test your app!
https://your-app.up.railway.app/test-ui
```

### 3. Required Environment Variables

Minimum required (copy to Railway Variables tab):

```bash
API_KEY=your-secure-random-key
GEMINI_API_KEYS=your-gemini-key
IMAGE_ANALYSIS_LLM_PRIORITY=gemini,openai,groq
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
MAX_FILE_SIZE_MB=10
ALLOWED_ORIGINS=*
RATE_LIMIT=100/minute
LOG_LEVEL=INFO
```

See `.env.railway` for complete template.

---

## 📖 Detailed Guides

### For First-Time Deployment

👉 **Start here:** `RAILWAY_QUICK_START.md`
- 5-minute deployment
- Minimal configuration
- Get up and running fast

### For Complete Instructions

👉 **Read this:** `RAILWAY_DEPLOYMENT_GUIDE.md`
- Step-by-step with screenshots
- Database setup
- Custom domains
- Troubleshooting
- Monitoring
- Security best practices

### For Verification

👉 **Use this:** `DEPLOYMENT_CHECKLIST.md`
- Pre-deployment checklist
- Post-deployment verification
- Testing procedures
- Security checks

---

## 🎯 What Gets Deployed

Your Railway deployment includes:

### Application
- ✅ FastAPI backend
- ✅ Image analysis API
- ✅ Material analysis API
- ✅ Test UI interfaces
- ✅ API documentation

### Features
- ✅ Multi-LLM support (Gemini, OpenAI, Groq)
- ✅ Automatic fallback between LLMs
- ✅ Database integration (optional)
- ✅ Rate limiting
- ✅ API key authentication
- ✅ CORS configuration
- ✅ Health checks
- ✅ Logging and monitoring

### Infrastructure
- ✅ Docker containerization
- ✅ Automatic HTTPS
- ✅ Auto-scaling
- ✅ Zero-downtime deployments
- ✅ Automatic restarts

---

## 🔑 Getting API Keys

### Gemini API (Recommended)
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key
4. Add to Railway: `GEMINI_API_KEYS=your-key`

### OpenAI API (Optional)
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Copy the key
4. Add to Railway: `OPENAI_API_KEYS=your-key`

### Groq API (Optional)
1. Go to [Groq Console](https://console.groq.com/keys)
2. Click "Create API Key"
3. Copy the key
4. Add to Railway: `GROQ_API_KEYS=your-key`

### Custom API Key
Generate a secure random key:

**Windows PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

**macOS/Linux:**
```bash
openssl rand -base64 32
```

**Online:**
Use [passwordsgenerator.net](https://passwordsgenerator.net/)

---

## 🧪 Testing Your Deployment

### 1. Health Check
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "gemini_api_available": true,
  "database_available": true
}
```

### 2. Test UI
Open in browser:
```
https://your-app.up.railway.app/test-ui
```

Upload a device image and verify it works!

### 3. API Documentation
```
https://your-app.up.railway.app/docs
```

### 4. Material Analysis
```
https://your-app.up.railway.app/static/material_analysis_test.html
```

---

## 🔧 Common Issues

### "No LLM API keys configured"
**Solution:** Add at least one API key:
```bash
GEMINI_API_KEYS=your-key
```

### "API Key required"
**Solution:** Add your custom API key:
```bash
API_KEY=your-secure-key
```

### Deployment fails
**Solution:** Check logs in Railway dashboard:
1. Click your service
2. Go to "Deployments" tab
3. Click latest deployment
4. View logs

### Database connection fails
**Solution:** 
1. Add PostgreSQL service in Railway
2. `DATABASE_URL` is auto-provided
3. Check database logs

---

## 📊 Monitoring

### View Logs
```bash
# Install Railway CLI
iwr https://railway.app/install.ps1 | iex  # Windows
curl -fsSL https://railway.app/install.sh | sh  # macOS/Linux

# Login
railway login

# View logs
railway logs
```

### Dashboard Metrics
1. Go to Railway dashboard
2. Click your service
3. View "Metrics" tab:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

---

## 💰 Costs

### Free Tier
- $5 credit per month
- 500 hours of usage
- 1GB RAM
- 1GB storage

### Hobby Plan
- $5/month
- More resources
- Better performance

### Monitor Usage
Check "Usage" tab in Railway dashboard

---

## 🔄 Updating Your App

Railway automatically deploys when you push to GitHub:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Railway will:
1. Detect the push
2. Build new Docker image
3. Deploy automatically
4. Zero-downtime deployment

---

## 🆘 Need Help?

### Documentation
- 📖 Quick Start: `RAILWAY_QUICK_START.md`
- 📚 Full Guide: `RAILWAY_DEPLOYMENT_GUIDE.md`
- ✅ Checklist: `DEPLOYMENT_CHECKLIST.md`

### Railway Support
- Discord: https://discord.gg/railway
- Docs: https://docs.railway.app/
- Status: https://status.railway.app/

### Application Support
- API Docs: `/docs` on your deployment
- Test UI: `/test-ui` on your deployment

---

## 🎉 Success!

Once deployed, you'll have:

✅ Live API at `https://your-app.up.railway.app`  
✅ Test UI for easy testing  
✅ API documentation  
✅ Automatic HTTPS  
✅ Auto-scaling  
✅ Monitoring and logs  

---

## 📝 Next Steps

After successful deployment:

1. ✅ Test thoroughly with various images
2. ✅ Share test UI with team
3. ✅ Monitor logs for first few days
4. ✅ Set up alerts for errors
5. ✅ Document API for users
6. ✅ Plan for scaling if needed

---

## 🚀 Ready to Deploy?

Choose your path:

- **Fast deployment (5 min):** → `RAILWAY_QUICK_START.md`
- **Detailed guide:** → `RAILWAY_DEPLOYMENT_GUIDE.md`
- **Verification:** → `DEPLOYMENT_CHECKLIST.md`

---

**Happy deploying! 🎉**
