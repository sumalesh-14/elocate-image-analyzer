# 🚀 Railway Deployment Checklist

Use this checklist to ensure a smooth deployment.

---

## 📋 Pre-Deployment

### Code Preparation
- [ ] All code committed to Git
- [ ] `.env` file is in `.gitignore` (never commit secrets!)
- [ ] `Dockerfile` exists and is correct
- [ ] `requirements.txt` is up to date
- [ ] `run.py` exists and handles PORT correctly
- [ ] Code pushed to GitHub/GitLab/Bitbucket

### API Keys Ready
- [ ] Gemini API key(s) obtained
- [ ] OpenAI API key(s) obtained (optional)
- [ ] Groq API key(s) obtained (optional)
- [ ] Custom API key generated (32+ random characters)
- [ ] Database credentials ready (if using external DB)

### Railway Account
- [ ] Railway account created
- [ ] GitHub connected to Railway
- [ ] Payment method added (if needed)

---

## 🏗️ Deployment Steps

### 1. Create Project
- [ ] Logged into Railway
- [ ] Created new project
- [ ] Selected "Deploy from GitHub repo"
- [ ] Repository selected and authorized
- [ ] Initial build started (will fail - expected)

### 2. Configure Environment Variables
- [ ] Opened Variables tab
- [ ] Clicked "Raw Editor"
- [ ] Pasted environment variables from `.env.railway`
- [ ] Replaced all placeholder values with real keys
- [ ] Verified no typos in variable names
- [ ] Clicked "Update Variables"
- [ ] Automatic redeploy triggered

### 3. Add Database (Optional)
- [ ] Clicked "New" → "Database" → "PostgreSQL"
- [ ] Database created successfully
- [ ] `DATABASE_URL` automatically added to variables
- [ ] Database connection verified in logs

### 4. Configure Domain
- [ ] Opened Settings → Networking
- [ ] Clicked "Generate Domain"
- [ ] Railway domain generated (e.g., `your-app.up.railway.app`)
- [ ] Custom domain added (if applicable)
- [ ] DNS records configured (if using custom domain)

---

## ✅ Post-Deployment Verification

### Health Checks
- [ ] Deployment status shows "Success"
- [ ] No errors in deployment logs
- [ ] Health endpoint returns 200: `/health`
- [ ] Root endpoint returns service info: `/`

### API Endpoints
- [ ] API docs accessible: `/docs`
- [ ] Test UI loads: `/test-ui`
- [ ] Material analysis test UI loads: `/static/material_analysis_test.html`

### Functionality Tests
- [ ] Image upload works via test UI
- [ ] Device analysis returns results
- [ ] Material analysis works
- [ ] API key authentication works
- [ ] Rate limiting is active
- [ ] CORS configured correctly

### Database (if applicable)
- [ ] Database connection successful
- [ ] Categories table accessible
- [ ] Brands table accessible
- [ ] Models table accessible
- [ ] Database queries working

---

## 🔒 Security Verification

- [ ] API key is strong (32+ characters)
- [ ] API key is NOT in Git repository
- [ ] HTTPS is enabled (automatic on Railway)
- [ ] CORS origins configured correctly
- [ ] Rate limiting is active
- [ ] No sensitive data in logs
- [ ] Environment variables are secure

---

## 📊 Monitoring Setup

- [ ] Logs are accessible and readable
- [ ] Metrics tab shows data
- [ ] Alerts configured (optional)
- [ ] Railway CLI installed (optional)
- [ ] Bookmark Railway dashboard

---

## 🧪 Testing Checklist

### Image Analysis Tests
- [ ] Upload smartphone image → correct identification
- [ ] Upload laptop image → correct identification
- [ ] Upload tablet image → correct identification
- [ ] Upload unclear image → handles gracefully
- [ ] Upload invalid file → proper error message
- [ ] Upload oversized file → proper error message

### Material Analysis Tests
- [ ] Analyze Samsung Galaxy S21 → returns materials
- [ ] Analyze iPhone 13 → returns materials
- [ ] Analyze MacBook Pro → returns materials
- [ ] Invalid input → proper error message

### API Key Tests
- [ ] Request without API key → 401 error
- [ ] Request with wrong API key → 401 error
- [ ] Request with correct API key → success

### Rate Limiting Tests
- [ ] Multiple rapid requests → rate limit triggered
- [ ] Rate limit message is clear

---

## 📝 Documentation

- [ ] API documentation reviewed
- [ ] Test UI instructions clear
- [ ] Environment variables documented
- [ ] Deployment guide accessible
- [ ] Team members have access

---

## 🎯 Performance Checks

- [ ] Response time < 5 seconds for image analysis
- [ ] Response time < 3 seconds for material analysis
- [ ] Memory usage within limits
- [ ] CPU usage reasonable
- [ ] No memory leaks observed

---

## 🔄 Continuous Deployment

- [ ] Automatic deployments enabled
- [ ] Push to main branch triggers deploy
- [ ] Deployment notifications configured
- [ ] Rollback plan documented

---

## 📞 Support & Backup

- [ ] Railway support channels bookmarked
- [ ] Environment variables backed up (securely)
- [ ] Database backup configured (if applicable)
- [ ] Team has access to Railway project
- [ ] Emergency contacts documented

---

## 🎉 Go Live Checklist

Before announcing to users:

- [ ] All above items completed
- [ ] Tested with real device images
- [ ] Monitored for 24 hours
- [ ] No critical errors in logs
- [ ] Performance is acceptable
- [ ] Team trained on monitoring
- [ ] Incident response plan ready

---

## 📈 Post-Launch

Week 1:
- [ ] Monitor logs daily
- [ ] Check error rates
- [ ] Review performance metrics
- [ ] Gather user feedback
- [ ] Document any issues

Week 2-4:
- [ ] Optimize based on usage patterns
- [ ] Scale resources if needed
- [ ] Update documentation
- [ ] Plan improvements

---

## 🆘 Emergency Contacts

Railway Support:
- Discord: https://discord.gg/railway
- Status: https://status.railway.app/
- Docs: https://docs.railway.app/

Project Team:
- [ ] Add team member contacts here

---

## 📊 Success Metrics

Track these after deployment:

- [ ] Uptime: Target 99.9%
- [ ] Response time: Target < 5s
- [ ] Error rate: Target < 1%
- [ ] User satisfaction: Target > 90%
- [ ] API usage: Track daily requests

---

**Deployment Date:** _______________

**Deployed By:** _______________

**Railway URL:** _______________

**Status:** ⬜ Not Started | ⬜ In Progress | ⬜ Complete | ⬜ Live

---

**Notes:**

_Add any deployment-specific notes here_

---

✅ **All checks passed? Congratulations! Your app is live! 🎉**
