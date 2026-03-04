# Railway Deployment - Quick Start Checklist

Use this checklist for a fast deployment. For detailed instructions, see `RAILWAY_DEPLOYMENT_GUIDE.md`.

---

## ⚡ 5-Minute Deployment

### Step 1: Prepare (2 minutes)

- [ ] Push code to GitHub/GitLab
- [ ] Have API keys ready:
  - [ ] Gemini API key
  - [ ] Your custom API key (create a random 32-char string)
  - [ ] (Optional) OpenAI/Groq keys

### Step 2: Deploy (1 minute)

1. Go to [railway.app](https://railway.app/)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Wait for initial build (will fail - that's OK!)

### Step 3: Configure (2 minutes)

1. Click your service → "Variables" tab → "Raw Editor"
2. Paste this (replace with your values):

```bash
API_KEY=your-secure-random-key-here
GEMINI_API_KEYS=your-gemini-key-here
IMAGE_ANALYSIS_LLM_PRIORITY=gemini,openai,groq
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
MAX_FILE_SIZE_MB=10
ALLOWED_ORIGINS=*
RATE_LIMIT=100/minute
LOG_LEVEL=INFO
```

3. Click "Update Variables"
4. Wait for automatic redeploy (2-3 minutes)

### Step 4: Test (30 seconds)

1. Go to "Settings" → "Networking" → "Generate Domain"
2. Open: `https://your-app.up.railway.app/test-ui`
3. Upload a device image
4. Verify it works!

---

## ✅ Verification Checklist

After deployment, verify these URLs work:

```bash
# Health check
https://your-app.up.railway.app/health

# Test UI
https://your-app.up.railway.app/test-ui

# API docs
https://your-app.up.railway.app/docs
```

---

## 🔧 Common Issues

### "No LLM API keys configured"
→ Add `GEMINI_API_KEYS` in Variables tab

### "API Key required"
→ Add `API_KEY` in Variables tab

### "Service unavailable"
→ Check logs: Deployments → Click deployment → View Logs

---

## 📚 Full Guide

For detailed instructions, troubleshooting, and advanced configuration:
→ See `RAILWAY_DEPLOYMENT_GUIDE.md`

---

## 🎯 Quick Commands

```bash
# Install Railway CLI
# Windows PowerShell:
iwr https://railway.app/install.ps1 | iex

# macOS/Linux:
curl -fsSL https://railway.app/install.sh | sh

# Login
railway login

# View logs
railway logs

# Redeploy
railway up
```

---

**That's it! Your app should be live in 5 minutes! 🚀**
