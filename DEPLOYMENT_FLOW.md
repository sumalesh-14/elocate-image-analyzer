# 🔄 Railway Deployment Flow Diagram

Visual guide to understand the deployment process.

---

## 📊 Complete Deployment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAILWAY DEPLOYMENT FLOW                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ 1. PREPARE   │
│   YOUR CODE  │
└──────┬───────┘
       │
       ├─ ✅ Code in Git repository
       ├─ ✅ Dockerfile exists
       ├─ ✅ requirements.txt updated
       ├─ ✅ run.py configured
       └─ ✅ .env not in Git
       │
       ↓
┌──────────────┐
│ 2. GET API   │
│    KEYS      │
└──────┬───────┘
       │
       ├─ 🔑 Gemini API key
       ├─ 🔑 OpenAI API key (optional)
       ├─ 🔑 Groq API key (optional)
       └─ 🔑 Custom API key (generate)
       │
       ↓
┌──────────────┐
│ 3. CREATE    │
│   RAILWAY    │
│   PROJECT    │
└──────┬───────┘
       │
       ├─ 🌐 Login to railway.app
       ├─ ➕ New Project
       ├─ 📦 Deploy from GitHub
       └─ 🔗 Select repository
       │
       ↓
┌──────────────┐
│ 4. INITIAL   │
│    BUILD     │
└──────┬───────┘
       │
       ├─ 🔨 Railway builds Docker image
       ├─ ⏱️  Takes 2-3 minutes
       └─ ❌ Will fail (no env vars yet)
       │
       ↓
┌──────────────┐
│ 5. ADD ENV   │
│   VARIABLES  │
└──────┬───────┘
       │
       ├─ 📝 Open Variables tab
       ├─ 📋 Copy from .env.railway
       ├─ ✏️  Replace with real values
       └─ 💾 Save variables
       │
       ↓
┌──────────────┐
│ 6. AUTO      │
│   REDEPLOY   │
└──────┬───────┘
       │
       ├─ 🔄 Railway detects changes
       ├─ 🔨 Rebuilds automatically
       ├─ ⏱️  Takes 2-3 minutes
       └─ ✅ Should succeed now
       │
       ↓
┌──────────────┐
│ 7. GENERATE  │
│    DOMAIN    │
└──────┬───────┘
       │
       ├─ 🌐 Settings → Networking
       ├─ ➕ Generate Domain
       └─ 🔗 Get your-app.up.railway.app
       │
       ↓
┌──────────────┐
│ 8. TEST      │
│   DEPLOYMENT │
└──────┬───────┘
       │
       ├─ 🏥 /health → Check health
       ├─ 🧪 /test-ui → Test interface
       ├─ 📚 /docs → API documentation
       └─ 📸 Upload image → Verify works
       │
       ↓
┌──────────────┐
│ 9. MONITOR   │
│   & MAINTAIN │
└──────┬───────┘
       │
       ├─ 📊 Check metrics
       ├─ 📝 Review logs
       ├─ 🔔 Set up alerts
       └─ 🎉 You're live!
       │
       ↓
┌──────────────┐
│   SUCCESS!   │
│      🚀      │
└──────────────┘
```

---

## 🔄 Request Flow (After Deployment)

```
┌─────────────────────────────────────────────────────────────────┐
│                      REQUEST FLOW                                │
└─────────────────────────────────────────────────────────────────┘

User Browser/Client
       │
       │ 1. Upload image
       ↓
┌──────────────────┐
│  Railway Domain  │  https://your-app.up.railway.app
│   (HTTPS Auto)   │
└────────┬─────────┘
         │
         │ 2. Route to container
         ↓
┌──────────────────┐
│  Docker          │
│  Container       │
│  (Your App)      │
└────────┬─────────┘
         │
         │ 3. FastAPI receives request
         ↓
┌──────────────────┐
│  Middleware      │
│  - CORS          │
│  - Auth (API Key)│
│  - Rate Limit    │
└────────┬─────────┘
         │
         │ 4. Validate & process
         ↓
┌──────────────────┐
│  Image Validator │
│  - Check type    │
│  - Check size    │
│  - Validate      │
└────────┬─────────┘
         │
         │ 5. Send to LLM
         ↓
┌──────────────────┐
│  LLM Router      │
│  - Try Gemini    │
│  - Fallback      │
│  - Try OpenAI    │
│  - Try Groq      │
└────────┬─────────┘
         │
         │ 6. Get LLM response
         ↓
┌──────────────────┐
│  Database        │
│  Matcher         │
│  (Optional)      │
└────────┬─────────┘
         │
         │ 7. Build response
         ↓
┌──────────────────┐
│  Response        │
│  - Device info   │
│  - Confidence    │
│  - Materials     │
└────────┬─────────┘
         │
         │ 8. Return JSON
         ↓
User Browser/Client
```

---

## 🔑 Environment Variables Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 ENVIRONMENT VARIABLES FLOW                       │
└─────────────────────────────────────────────────────────────────┘

.env.railway (Template)
       │
       │ 1. Copy template
       ↓
Railway Variables Tab
       │
       │ 2. Paste & edit
       ↓
Railway Secure Storage
       │
       │ 3. Encrypted storage
       ↓
Docker Container
       │
       │ 4. Injected at runtime
       ↓
app/config.py
       │
       │ 5. Loaded by Pydantic
       ↓
Application Code
       │
       │ 6. Used throughout app
       ↓
API Keys → LLM Services
Database → PostgreSQL
Settings → FastAPI
```

---

## 🔄 Update & Deployment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    UPDATE DEPLOYMENT FLOW                        │
└─────────────────────────────────────────────────────────────────┘

Local Development
       │
       │ 1. Make code changes
       ↓
Git Commit
       │
       │ 2. git commit -m "Update"
       ↓
Git Push
       │
       │ 3. git push origin main
       ↓
GitHub Repository
       │
       │ 4. Webhook to Railway
       ↓
Railway Detects Change
       │
       │ 5. Trigger build
       ↓
Build Docker Image
       │
       │ 6. docker build
       ↓
Run Tests (if configured)
       │
       │ 7. Validate build
       ↓
Deploy New Version
       │
       │ 8. Zero-downtime deploy
       ↓
Health Check
       │
       │ 9. Verify /health
       ↓
Switch Traffic
       │
       │ 10. Route to new version
       ↓
Old Version Stopped
       │
       │ 11. Cleanup
       ↓
Deployment Complete ✅
```

---

## 🗄️ Database Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   DATABASE INTEGRATION FLOW                      │
└─────────────────────────────────────────────────────────────────┘

Railway PostgreSQL Service
       │
       │ 1. Auto-provision
       ↓
DATABASE_URL Generated
       │
       │ 2. Injected to app
       ↓
Connection Pool Created
       │
       │ 3. asyncpg pool
       ↓
Database Matcher Service
       │
       │ 4. Query categories
       ↓
LLM Analysis
       │
       │ 5. Match results
       ↓
Auto-Seed New Entries
       │
       │ 6. If confidence high
       ↓
Return Matched IDs
       │
       │ 7. Include in response
       ↓
API Response
```

---

## 🔐 Security Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        SECURITY FLOW                             │
└─────────────────────────────────────────────────────────────────┘

Incoming Request
       │
       │ 1. HTTPS (Railway auto)
       ↓
CORS Middleware
       │
       │ 2. Check origin
       ├─ ✅ Allowed → Continue
       └─ ❌ Blocked → 403
       ↓
API Key Middleware
       │
       │ 3. Check X-API-Key header
       ├─ ✅ Valid → Continue
       └─ ❌ Invalid → 401
       ↓
Rate Limit Middleware
       │
       │ 4. Check request count
       ├─ ✅ Under limit → Continue
       └─ ❌ Over limit → 429
       ↓
Request Processing
       │
       │ 5. Handle request
       ↓
Response
```

---

## 📊 Monitoring Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      MONITORING FLOW                             │
└─────────────────────────────────────────────────────────────────┘

Application Logs
       │
       │ 1. Python logging
       ↓
Railway Log Aggregation
       │
       │ 2. Collect all logs
       ↓
Railway Dashboard
       │
       │ 3. Display in UI
       ├─ 📊 Metrics tab
       ├─ 📝 Logs tab
       └─ 🚀 Deployments tab
       ↓
Railway CLI
       │
       │ 4. railway logs
       ↓
Developer/Ops Team
       │
       │ 5. Monitor & respond
       ↓
Alerts (if configured)
```

---

## 🔄 LLM Fallback Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     LLM FALLBACK FLOW                            │
└─────────────────────────────────────────────────────────────────┘

Image Analysis Request
       │
       │ Priority: gemini,openai,groq
       ↓
Try Gemini (First)
       │
       ├─ ✅ Success → Return result
       │
       ├─ ❌ Failed → Log error
       ↓
Try OpenAI (Second)
       │
       ├─ ✅ Success → Return result
       │
       ├─ ❌ Failed → Log error
       ↓
Try Groq (Third)
       │
       ├─ ✅ Success → Return result
       │
       ├─ ❌ Failed → Log error
       ↓
All Failed
       │
       │ Return error to user
       ↓
Error Response
```

---

## 🎯 Decision Tree: Which Guide to Use?

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENTATION DECISION TREE                   │
└─────────────────────────────────────────────────────────────────┘

START: Need to deploy?
       │
       ├─ Never deployed before?
       │  │
       │  ├─ Want quick start?
       │  │  └─→ RAILWAY_QUICK_START.md
       │  │
       │  └─ Want detailed guide?
       │     └─→ RAILWAY_DEPLOYMENT_GUIDE.md
       │
       ├─ Already deployed?
       │  │
       │  ├─ Having problems?
       │  │  └─→ RAILWAY_TROUBLESHOOTING.md
       │  │
       │  ├─ Need to verify?
       │  │  └─→ DEPLOYMENT_CHECKLIST.md
       │  │
       │  └─ Need to update?
       │     └─→ git push (auto-deploys)
       │
       ├─ Need environment variables?
       │  └─→ .env.railway
       │
       ├─ Want overview?
       │  └─→ README_RAILWAY.md
       │
       └─ Want to understand flow?
          └─→ DEPLOYMENT_FLOW.md (this file!)
```

---

## 📈 Scaling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCALING FLOW                              │
└─────────────────────────────────────────────────────────────────┘

Monitor Usage
       │
       │ Check metrics
       ↓
Usage Increasing?
       │
       ├─ CPU > 80%
       ├─ Memory > 80%
       └─ Response time slow
       ↓
Optimize First
       │
       ├─ Reduce DB pool
       ├─ Add caching
       └─ Optimize queries
       ↓
Still Need More?
       │
       │ Upgrade Railway plan
       ↓
Hobby Plan ($5/mo)
       │
       │ More resources
       ↓
Monitor Again
       │
       │ Verify improvement
       ↓
Stable Performance ✅
```

---

## 🔄 Rollback Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       ROLLBACK FLOW                              │
└─────────────────────────────────────────────────────────────────┘

New Deployment Has Issues
       │
       │ 1. Detect problem
       ↓
Railway Dashboard
       │
       │ 2. Go to Deployments tab
       ↓
Find Last Working Deployment
       │
       │ 3. Identify good version
       ↓
Click "⋮" Menu
       │
       │ 4. Open options
       ↓
Click "Redeploy"
       │
       │ 5. Trigger rollback
       ↓
Railway Redeploys Old Version
       │
       │ 6. Zero-downtime switch
       ↓
Verify Working
       │
       │ 7. Test endpoints
       ↓
Fix Issue in Code
       │
       │ 8. Debug locally
       ↓
Deploy Fixed Version
       │
       │ 9. git push
       ↓
Monitor Carefully
       │
       │ 10. Watch logs
       ↓
Stable Again ✅
```

---

## 🎯 Quick Reference

### Deployment Time Estimates

```
Initial Setup:        5-10 minutes
First Deployment:     3-5 minutes
Subsequent Deploys:   2-3 minutes
Environment Changes:  1 minute + redeploy
Domain Setup:         2 minutes + DNS propagation
Database Setup:       2 minutes
```

### Common Paths

```
Fast Path:
README_RAILWAY.md → RAILWAY_QUICK_START.md → Test

Detailed Path:
README_RAILWAY.md → RAILWAY_DEPLOYMENT_GUIDE.md → 
DEPLOYMENT_CHECKLIST.md → Test

Problem Path:
Issue occurs → RAILWAY_TROUBLESHOOTING.md → Fix → Test
```

---

**Use these diagrams to understand the deployment process! 📊**
