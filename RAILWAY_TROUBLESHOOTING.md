# 🔧 Railway Deployment Troubleshooting Guide

Common issues and their solutions when deploying to Railway.

---

## 🚨 Deployment Failures

### Issue: Build Fails with "No such file or directory"

**Symptoms:**
```
Error: COPY failed: file not found in build context
```

**Solution:**
1. Check `.dockerignore` - make sure required files aren't excluded
2. Verify all files are committed to Git
3. Check file paths in `Dockerfile` are correct

```bash
# Verify files exist
git ls-files

# Check Dockerfile
cat Dockerfile
```

---

### Issue: "No PORT environment variable"

**Symptoms:**
```
Error: Address already in use
Error: Cannot bind to port
```

**Solution:**
Railway automatically provides `PORT`. Your `run.py` should use:

```python
import os
port = int(os.getenv("PORT", "8000"))
```

✅ **Already fixed in your code!**

---

### Issue: "Requirements installation failed"

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement
```

**Solution:**
1. Check `requirements.txt` syntax
2. Verify package names are correct
3. Pin versions if needed:

```txt
# Good
fastapi>=0.110.0

# Better (more stable)
fastapi==0.110.0
```

---

## 🔑 API Key Issues

### Issue: "No LLM API keys configured"

**Symptoms:**
```
ValueError: At least one LLM API key must be configured
```

**Solution:**
Add at least one API key in Railway Variables:

```bash
GEMINI_API_KEYS=your-key-here
# OR
OPENAI_API_KEYS=your-key-here
# OR
GROQ_API_KEYS=your-key-here
```

**Multiple keys format:**
```bash
GEMINI_API_KEYS=key1,key2,key3
```

⚠️ **No spaces after commas!**

---

### Issue: "API_KEY is required"

**Symptoms:**
```
ValueError: API_KEY is required
```

**Solution:**
Add `API_KEY` in Railway Variables:

```bash
API_KEY=your-secure-random-key-here
```

Generate a secure key:
```powershell
# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

---

### Issue: "Invalid API key" or "401 Unauthorized"

**Symptoms:**
- Requests return 401 error
- "Invalid API key" message

**Solution:**
1. Check API key in request header:
   ```bash
   curl -H "X-API-Key: your-key" https://your-app.up.railway.app/health
   ```

2. Verify API key matches Railway variable:
   - Go to Variables tab
   - Check `API_KEY` value
   - No extra spaces or quotes

3. Test with correct key:
   ```bash
   # Get key from Railway Variables tab
   curl -H "X-API-Key: actual-key-from-railway" https://your-app.up.railway.app/api/v1/analyze
   ```

---

## 🗄️ Database Issues

### Issue: "Database connection failed"

**Symptoms:**
```
asyncpg.exceptions.InvalidCatalogNameError
Connection refused
```

**Solution:**

**If using Railway PostgreSQL:**
1. Verify PostgreSQL service is running
2. Check `DATABASE_URL` is auto-provided:
   - Go to Variables tab
   - Look for `DATABASE_URL`
   - Should start with `postgresql://`

**If using external database:**
1. Add all required variables:
   ```bash
   DATABASE_URL=postgresql://user:pass@host:port/db
   DB_HOST=your-host
   DB_PORT=5432
   DB_NAME=your-db
   DB_USER=your-user
   DB_PASSWORD=your-password
   ```

2. Check firewall allows Railway IPs
3. Verify credentials are correct

---

### Issue: "Too many database connections"

**Symptoms:**
```
asyncpg.exceptions.TooManyConnectionsError
```

**Solution:**
Reduce connection pool size:

```bash
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=5
```

---

## 🌐 Network & CORS Issues

### Issue: "CORS policy blocked"

**Symptoms:**
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Solution:**
Update `ALLOWED_ORIGINS` in Railway Variables:

```bash
# Allow all (development)
ALLOWED_ORIGINS=*

# Allow specific domains (production)
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

⚠️ **No spaces after commas!**

---

### Issue: "Service unavailable" or "502 Bad Gateway"

**Symptoms:**
- App doesn't respond
- 502 error in browser
- Health check fails

**Solution:**

1. **Check deployment status:**
   - Go to Deployments tab
   - Verify status is "Success"
   - If failed, check logs

2. **Check logs for errors:**
   ```bash
   railway logs
   ```

3. **Verify app is listening on correct port:**
   ```python
   # In run.py
   port = int(os.getenv("PORT", "8000"))
   uvicorn.run("app.main:app", host="0.0.0.0", port=port)
   ```

4. **Check health endpoint:**
   ```bash
   curl https://your-app.up.railway.app/health
   ```

---

## 📦 File Upload Issues

### Issue: "File too large"

**Symptoms:**
```
413 Request Entity Too Large
File size exceeds limit
```

**Solution:**
Increase file size limit:

```bash
MAX_FILE_SIZE_MB=20
```

Railway default limit: 100MB  
Your app default: 10MB

---

### Issue: "Invalid file type"

**Symptoms:**
```
INVALID_FILE_TYPE error
```

**Solution:**
Verify file is JPEG, PNG, or WebP:

```bash
# Check file type
file your-image.jpg

# Convert if needed
convert image.png image.jpg
```

---

## 🔥 Performance Issues

### Issue: "Request timeout"

**Symptoms:**
```
504 Gateway Timeout
Request took too long
```

**Solution:**

1. **Increase timeout:**
   ```bash
   REQUEST_TIMEOUT=120
   ```

2. **Check LLM API status:**
   - Gemini: https://status.cloud.google.com/
   - OpenAI: https://status.openai.com/
   - Groq: https://status.groq.com/

3. **Use faster LLM:**
   ```bash
   IMAGE_ANALYSIS_LLM_PRIORITY=groq,gemini,openai
   ```

---

### Issue: "High memory usage"

**Symptoms:**
- App crashes randomly
- "Out of memory" errors
- Slow performance

**Solution:**

1. **Reduce database pool:**
   ```bash
   DB_POOL_MAX_SIZE=5
   ```

2. **Upgrade Railway plan:**
   - Free tier: 1GB RAM
   - Hobby: More RAM available

3. **Check for memory leaks:**
   ```bash
   railway logs | grep -i memory
   ```

---

## 🔐 Security Issues

### Issue: "Rate limit not working"

**Symptoms:**
- Unlimited requests allowed
- No rate limit errors

**Solution:**
Verify rate limit is set:

```bash
RATE_LIMIT=100/minute
```

Test rate limiting:
```bash
# Send multiple rapid requests
for i in {1..150}; do
  curl https://your-app.up.railway.app/health
done
```

Should see 429 errors after 100 requests.

---

### Issue: "API key exposed in logs"

**Symptoms:**
- API keys visible in Railway logs
- Security concern

**Solution:**

1. **Rotate exposed keys immediately**
2. **Check code doesn't log secrets:**
   ```python
   # Bad
   logger.info(f"API key: {api_key}")
   
   # Good
   logger.info("API key configured")
   ```

3. **Use Railway's secret management**
4. **Never commit `.env` to Git**

---

## 🐛 Application Errors

### Issue: "Module not found"

**Symptoms:**
```
ModuleNotFoundError: No module named 'app'
```

**Solution:**

1. **Check directory structure:**
   ```
   your-repo/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py
   │   └── ...
   ├── run.py
   └── requirements.txt
   ```

2. **Verify imports in run.py:**
   ```python
   from app.main import app  # Correct
   ```

3. **Check PYTHONPATH:**
   ```bash
   # In Dockerfile or Railway
   ENV PYTHONPATH=/app
   ```

---

### Issue: "Image analysis fails"

**Symptoms:**
```
ANALYSIS_FAILED error
LLM API error
```

**Solution:**

1. **Check LLM API keys are valid:**
   ```bash
   # Test Gemini key
   curl -H "x-goog-api-key: YOUR_KEY" \
     https://generativelanguage.googleapis.com/v1/models
   ```

2. **Check LLM API quotas:**
   - Gemini: Check Google Cloud Console
   - OpenAI: Check usage dashboard
   - Groq: Check Groq console

3. **Enable fallback:**
   ```bash
   IMAGE_ANALYSIS_LLM_PRIORITY=gemini,openai,groq
   ```

4. **Check logs for specific error:**
   ```bash
   railway logs | grep -i error
   ```

---

## 📊 Monitoring Issues

### Issue: "Can't see logs"

**Symptoms:**
- Logs tab is empty
- No deployment logs

**Solution:**

1. **Wait for deployment to complete**
2. **Refresh the page**
3. **Use Railway CLI:**
   ```bash
   railway logs --tail 100
   ```

4. **Check log level:**
   ```bash
   LOG_LEVEL=INFO
   ```

---

### Issue: "Metrics not showing"

**Symptoms:**
- Metrics tab is empty
- No CPU/memory data

**Solution:**

1. **Wait 5-10 minutes** after deployment
2. **Send some requests** to generate metrics
3. **Check service is running:**
   ```bash
   curl https://your-app.up.railway.app/health
   ```

---

## 🔄 Deployment Issues

### Issue: "Automatic deployment not working"

**Symptoms:**
- Push to GitHub doesn't trigger deploy
- Manual deploy required

**Solution:**

1. **Check GitHub connection:**
   - Settings → GitHub
   - Verify repository is connected

2. **Check branch settings:**
   - Settings → Service
   - Verify correct branch is selected

3. **Manually trigger deploy:**
   - Deployments tab
   - Click "Deploy"

---

### Issue: "Deployment stuck"

**Symptoms:**
- Deployment shows "Building" for > 10 minutes
- No progress

**Solution:**

1. **Cancel and retry:**
   - Click deployment
   - Click "Cancel"
   - Click "Redeploy"

2. **Check Railway status:**
   - https://status.railway.app/

3. **Contact Railway support:**
   - Discord: https://discord.gg/railway

---

## 🆘 Emergency Procedures

### Complete Service Failure

1. **Check Railway status:**
   ```
   https://status.railway.app/
   ```

2. **View recent logs:**
   ```bash
   railway logs --tail 500
   ```

3. **Rollback to previous deployment:**
   - Deployments tab
   - Find last working deployment
   - Click "⋮" → "Redeploy"

4. **Verify environment variables:**
   - Variables tab
   - Check all required vars are set

5. **Contact support:**
   - Discord: https://discord.gg/railway
   - Include: logs, error messages, deployment ID

---

## 📞 Getting Help

### Before Asking for Help

Gather this information:

1. **Error message** (exact text)
2. **Deployment logs** (last 100 lines)
3. **Environment variables** (names only, not values!)
4. **Steps to reproduce**
5. **Expected vs actual behavior**

### Railway Support Channels

- **Discord:** https://discord.gg/railway (fastest)
- **Docs:** https://docs.railway.app/
- **Status:** https://status.railway.app/
- **GitHub:** https://github.com/railwayapp/railway

### Application Support

- **API Docs:** `/docs` on your deployment
- **Test UI:** `/test-ui` on your deployment
- **Health Check:** `/health` on your deployment

---

## 🔍 Debugging Commands

### View Logs
```bash
# Last 100 lines
railway logs --tail 100

# Follow logs in real-time
railway logs --follow

# Filter logs
railway logs | grep -i error
```

### Check Variables
```bash
# List all variables
railway variables

# Check specific variable
railway variables | grep API_KEY
```

### Test Endpoints
```bash
# Health check
curl https://your-app.up.railway.app/health

# With API key
curl -H "X-API-Key: your-key" \
  https://your-app.up.railway.app/api/v1/analyze

# Verbose output
curl -v https://your-app.up.railway.app/health
```

### Check Service Status
```bash
# Railway CLI
railway status

# Or check dashboard
railway open
```

---

## ✅ Prevention Checklist

Avoid issues by following these practices:

- [ ] Always test locally before deploying
- [ ] Use `.env.example` for documentation
- [ ] Never commit `.env` to Git
- [ ] Pin dependency versions in `requirements.txt`
- [ ] Monitor logs after deployment
- [ ] Set up health check alerts
- [ ] Keep API keys secure
- [ ] Document environment variables
- [ ] Test with various inputs
- [ ] Have rollback plan ready

---

## 📚 Additional Resources

- **Railway Docs:** https://docs.railway.app/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Docker Docs:** https://docs.docker.com/
- **Python Docs:** https://docs.python.org/

---

**Still stuck? Check the main deployment guide: `RAILWAY_DEPLOYMENT_GUIDE.md`**
