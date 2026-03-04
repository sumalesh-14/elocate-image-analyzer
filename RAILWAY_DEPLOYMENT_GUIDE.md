# Railway Deployment Guide

Complete step-by-step guide to deploy your E-Waste Image Analyzer to Railway.

---

## Prerequisites

Before you start, make sure you have:

1. ✅ A [Railway account](https://railway.app/) (free tier available)
2. ✅ Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)
3. ✅ API keys ready:
   - Gemini API key(s)
   - OpenAI API key(s) (optional)
   - Groq API key(s) (optional)
   - Your custom API key for authentication
4. ✅ PostgreSQL database credentials (if using database features)

---

## Step 1: Prepare Your Repository

### 1.1 Verify Required Files

Make sure these files exist in your repository:

```
✅ Dockerfile              (already exists)
✅ requirements.txt        (already exists)
✅ run.py                  (already exists)
✅ .dockerignore           (already exists)
✅ app/                    (your application code)
✅ static/                 (HTML test interfaces)
```

### 1.2 Update .gitignore

Make sure your `.gitignore` includes:

```gitignore
# Environment variables (NEVER commit these!)
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
venv/
.pytest_cache/
.hypothesis/

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

### 1.3 Commit and Push

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

---

## Step 2: Create Railway Project

### 2.1 Sign Up / Log In

1. Go to [railway.app](https://railway.app/)
2. Click "Login" or "Start a New Project"
3. Sign in with GitHub (recommended for easy repo access)

### 2.2 Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. If first time: Click "Configure GitHub App" to authorize Railway
4. Select your repository from the list
5. Railway will automatically detect your Dockerfile

### 2.3 Initial Deployment

Railway will start building immediately. This first deployment will FAIL because environment variables are not set yet. That's expected!

---

## Step 3: Configure Environment Variables

### 3.1 Open Variables Settings

1. In your Railway project, click on your service
2. Click the "Variables" tab
3. Click "New Variable" or "Raw Editor" (Raw Editor is faster)

### 3.2 Add Required Variables

Click "Raw Editor" and paste this template (replace with your actual values):

```bash
# API Authentication
API_KEY=your-secure-api-key-here

# LLM API Keys (at least one required)
GEMINI_API_KEYS=your-gemini-key-1,your-gemini-key-2
OPENAI_API_KEYS=your-openai-key-1
GROQ_API_KEYS=your-groq-key-1

# LLM Priority Configuration
IMAGE_ANALYSIS_LLM_PRIORITY=gemini,openai,groq
MATERIAL_ANALYSIS_LLM_PRIORITY=groq,gemini,openai

# Database Configuration (if using PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10

# Application Settings
MAX_FILE_SIZE_MB=10
ALLOWED_ORIGINS=*
RATE_LIMIT=100/minute
REQUEST_TIMEOUT=60
LOG_LEVEL=INFO

# Railway automatically provides PORT - don't set it manually!
```

### 3.3 Important Notes

- **API_KEY**: Create a strong random key (use a password generator)
- **GEMINI_API_KEYS**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **OPENAI_API_KEYS**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **GROQ_API_KEYS**: Get from [Groq Console](https://console.groq.com/keys)
- **Multiple keys**: Separate with commas (no spaces)
- **DATABASE_URL**: If using Railway PostgreSQL, this is auto-provided
- **PORT**: Railway sets this automatically - DO NOT add it manually

### 3.4 Save Variables

1. Click "Update Variables"
2. Railway will automatically redeploy with new environment variables

---

## Step 4: Add PostgreSQL Database (Optional)

If you want to use the database matching features:

### 4.1 Add PostgreSQL Service

1. In your project, click "New"
2. Select "Database"
3. Choose "Add PostgreSQL"
4. Railway will create a PostgreSQL instance

### 4.2 Link Database to Your App

1. Railway automatically creates `DATABASE_URL` variable
2. Your app will detect and use it automatically
3. No manual configuration needed!

### 4.3 Initialize Database Schema

After deployment, you'll need to run migrations or seed scripts. You can do this via Railway's terminal:

1. Click on your service
2. Go to "Deployments" tab
3. Click on the latest deployment
4. Click "View Logs" or use Railway CLI (see Step 7)

---

## Step 5: Configure Domain (Optional)

### 5.1 Get Railway Domain

1. Click on your service
2. Go to "Settings" tab
3. Scroll to "Networking"
4. Click "Generate Domain"
5. Railway provides a free domain like: `your-app.up.railway.app`

### 5.2 Add Custom Domain (Optional)

1. In "Networking" section, click "Custom Domain"
2. Enter your domain (e.g., `api.yourdomain.com`)
3. Add the CNAME record to your DNS provider:
   ```
   CNAME: api.yourdomain.com -> your-app.up.railway.app
   ```
4. Wait for DNS propagation (5-30 minutes)

---

## Step 6: Verify Deployment

### 6.1 Check Deployment Status

1. Go to "Deployments" tab
2. Wait for "Success" status (usually 2-5 minutes)
3. If failed, click on deployment to see logs

### 6.2 Test Your API

Once deployed, test these endpoints:

#### Health Check
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-03-04T...",
  "gemini_api_available": true,
  "database_available": true
}
```

#### Root Endpoint
```bash
curl https://your-app.up.railway.app/
```

#### Test UI
Open in browser:
```
https://your-app.up.railway.app/test-ui
```

#### API Documentation
```
https://your-app.up.railway.app/docs
```

### 6.3 Test Image Analysis

Using curl:
```bash
curl -X POST "https://your-app.up.railway.app/api/v1/analyze" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@/path/to/device-image.jpg"
```

Or use the web interface at `/test-ui`

---

## Step 7: Railway CLI (Optional but Recommended)

### 7.1 Install Railway CLI

**Windows (PowerShell):**
```powershell
iwr https://railway.app/install.ps1 | iex
```

**macOS/Linux:**
```bash
curl -fsSL https://railway.app/install.sh | sh
```

### 7.2 Login to Railway

```bash
railway login
```

### 7.3 Link to Your Project

```bash
cd your-project-directory
railway link
```

Select your project from the list.

### 7.4 Useful CLI Commands

**View logs in real-time:**
```bash
railway logs
```

**Open project in browser:**
```bash
railway open
```

**Run commands in Railway environment:**
```bash
railway run python manage.py migrate
```

**Deploy from CLI:**
```bash
railway up
```

**Check environment variables:**
```bash
railway variables
```

---

## Step 8: Monitor Your Application

### 8.1 View Logs

1. Go to your service in Railway dashboard
2. Click "Deployments" tab
3. Click on active deployment
4. View real-time logs

### 8.2 Check Metrics

1. Go to "Metrics" tab
2. Monitor:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

### 8.3 Set Up Alerts (Optional)

1. Go to "Settings" tab
2. Configure notifications for:
   - Deployment failures
   - High resource usage
   - Service downtime

---

## Step 9: Troubleshooting

### Common Issues and Solutions

#### Issue 1: Deployment Fails with "No PORT"

**Solution:** Railway automatically sets PORT. Make sure your `run.py` uses:
```python
port = int(os.getenv("PORT", "8000"))
```

#### Issue 2: "API Key Not Found" Error

**Solution:** 
1. Check Variables tab
2. Ensure `API_KEY` is set
3. Redeploy if needed

#### Issue 3: "No LLM API Keys Configured"

**Solution:**
1. Add at least one of: `GEMINI_API_KEYS`, `OPENAI_API_KEYS`, or `GROQ_API_KEYS`
2. Format: `key1,key2,key3` (comma-separated, no spaces)

#### Issue 4: Database Connection Fails

**Solution:**
1. Check if PostgreSQL service is running
2. Verify `DATABASE_URL` is set automatically
3. Check database logs in Railway

#### Issue 5: Image Upload Fails

**Solution:**
1. Check `MAX_FILE_SIZE_MB` setting
2. Verify file is JPEG/PNG/WebP
3. Check logs for specific error

#### Issue 6: High Memory Usage

**Solution:**
1. Reduce `DB_POOL_MAX_SIZE` to 5
2. Upgrade Railway plan if needed
3. Optimize image processing

### View Detailed Logs

```bash
# Using Railway CLI
railway logs --tail 100

# Or in dashboard
Deployments → Click deployment → View Logs
```

---

## Step 10: Update Your Application

### 10.1 Deploy Updates

Railway automatically deploys when you push to your repository:

```bash
# Make changes to your code
git add .
git commit -m "Update feature X"
git push origin main
```

Railway will:
1. Detect the push
2. Build new Docker image
3. Deploy automatically
4. Zero-downtime deployment

### 10.2 Manual Redeploy

If you need to redeploy without code changes:

1. Go to "Deployments" tab
2. Click "⋮" menu on latest deployment
3. Click "Redeploy"

Or via CLI:
```bash
railway up --detach
```

---

## Step 11: Cost Management

### Free Tier Limits

Railway free tier includes:
- $5 credit per month
- 500 hours of usage
- 1GB RAM
- 1GB storage

### Monitor Usage

1. Go to "Usage" tab in your project
2. Check current month's usage
3. Set up billing alerts

### Optimize Costs

1. **Use smaller Docker image**: Already using `python:3.11-slim` ✅
2. **Reduce idle time**: Railway sleeps inactive services
3. **Optimize database**: Use connection pooling ✅
4. **Cache responses**: Implement caching for repeated requests
5. **Upgrade plan**: If you exceed free tier, upgrade to Hobby ($5/month)

---

## Step 12: Security Best Practices

### 12.1 Secure Your API Key

- ✅ Use strong random API key (32+ characters)
- ✅ Never commit API keys to Git
- ✅ Rotate keys periodically
- ✅ Use different keys for dev/prod

### 12.2 Configure CORS

Update `ALLOWED_ORIGINS` in environment variables:
```bash
# Allow specific domains
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Or allow all (less secure)
ALLOWED_ORIGINS=*
```

### 12.3 Rate Limiting

Already configured in your app:
```bash
RATE_LIMIT=100/minute
```

Adjust based on your needs.

### 12.4 HTTPS

Railway provides HTTPS automatically for all domains ✅

---

## Step 13: Backup and Recovery

### 13.1 Database Backups

Railway PostgreSQL includes automatic backups:
1. Go to PostgreSQL service
2. Click "Backups" tab
3. View automatic backups
4. Create manual backup if needed

### 13.2 Code Backups

Your code is already backed up in Git ✅

### 13.3 Environment Variables Backup

Export your variables:
```bash
railway variables > env-backup.txt
```

Store securely (NOT in Git!)

---

## Quick Reference

### Essential URLs

```
Dashboard:     https://railway.app/dashboard
Your App:      https://your-app.up.railway.app
API Docs:      https://your-app.up.railway.app/docs
Test UI:       https://your-app.up.railway.app/test-ui
Health Check:  https://your-app.up.railway.app/health
```

### Essential Commands

```bash
# View logs
railway logs

# Redeploy
railway up

# Open dashboard
railway open

# Check variables
railway variables

# Run command in Railway
railway run <command>
```

### Support Resources

- Railway Docs: https://docs.railway.app/
- Railway Discord: https://discord.gg/railway
- Railway Status: https://status.railway.app/

---

## Success Checklist

Before going live, verify:

- [ ] All environment variables are set
- [ ] Health check returns "healthy"
- [ ] Test UI loads successfully
- [ ] Image analysis works via test UI
- [ ] Material analysis works
- [ ] API documentation is accessible
- [ ] Database connection works (if using)
- [ ] Logs show no errors
- [ ] Domain is configured (if using custom domain)
- [ ] CORS is configured correctly
- [ ] Rate limiting is working
- [ ] Monitoring is set up

---

## Next Steps

After successful deployment:

1. **Test thoroughly** with various device images
2. **Monitor logs** for the first few days
3. **Set up alerts** for errors
4. **Document your API** for users
5. **Share your test UI** with stakeholders
6. **Plan for scaling** if traffic increases

---

## Need Help?

If you encounter issues:

1. Check Railway logs: `railway logs`
2. Review this guide's troubleshooting section
3. Check Railway status: https://status.railway.app/
4. Ask in Railway Discord: https://discord.gg/railway
5. Review Railway docs: https://docs.railway.app/

---

**Congratulations! Your E-Waste Image Analyzer is now live on Railway! 🚀**
