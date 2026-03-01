# Project Structure

Clean and organized structure for the Elocate Image Analyzer API.

## 📁 Directory Structure

```
elocate-image-analyzer/
├── app/                          # Application code
│   ├── api/                      # API routes and middleware
│   ├── models/                   # Request/Response models
│   ├── services/                 # Business logic services
│   └── utils/                    # Utility functions
│
├── tests/                        # All test files
│   ├── test_*.py                 # Python test files
│   ├── test_*.ps1                # PowerShell test scripts
│   └── README.md                 # Test documentation
│
├── docs/                         # All documentation
│   ├── RAILWAY_DEPLOYMENT_GUIDE.md
│   ├── HOW_TO_TEST.md
│   ├── RAILWAY_TROUBLESHOOTING.md
│   ├── GEMINI_API_QUOTA_GUIDE.md
│   └── README.md                 # Documentation index
│
├── static/                       # Static files
│   └── test_interface.html       # Test UI
│
├── .github/                      # GitHub workflows
├── .kiro/                        # Kiro configuration
│
├── run.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── railway.json                  # Railway configuration
├── Procfile                      # Process definition
├── .env                          # Environment variables
├── .gitignore                    # Git ignore rules
└── README.md                     # Main documentation
```

## 📂 Key Directories

### `/app` - Application Code
Contains all the application source code organized by functionality.

**Subdirectories:**
- `api/` - FastAPI routes, middleware, authentication
- `models/` - Pydantic models for requests and responses
- `services/` - Core business logic (Gemini API, database, etc.)
- `utils/` - Helper functions and utilities

### `/tests` - Test Suite
All test files in one place for easy discovery and execution.

**Test Types:**
- Unit tests (`test_*.py`)
- Integration tests (`test_*_integration.py`)
- Property tests (`test_*_properties.py`)
- Deployment tests (`test_*.ps1`)

### `/docs` - Documentation
Comprehensive documentation for deployment, testing, and troubleshooting.

**Key Documents:**
- Deployment guides
- Testing guides
- Troubleshooting guides
- API quota management

### `/static` - Static Files
Static assets served by the application.

**Contents:**
- Test interface HTML
- Future: Images, CSS, JS

## 🗂️ Root Files

### Configuration Files
- `railway.json` - Railway deployment configuration
- `Procfile` - Process definition for Railway
- `.env` - Environment variables (not in git)
- `.gitignore` - Git ignore rules
- `.dockerignore` - Docker ignore rules

### Python Files
- `run.py` - Application entry point
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - Main project documentation
- `PROJECT_STRUCTURE.md` - This file

### Deployment Files
- `railway-env.json` - Railway environment variables
- `railway-env.txt` - Environment variables (text format)
- `start.sh` - Startup script
- `deploy.sh` - Deployment script (Linux/Mac)
- `deploy.ps1` - Deployment script (Windows)

## 🎯 File Organization Principles

### 1. Separation of Concerns
- Application code in `/app`
- Tests in `/tests`
- Documentation in `/docs`

### 2. Clear Naming
- Test files: `test_*.py` or `test_*.ps1`
- Documentation: Descriptive names in CAPS
- Scripts: Lowercase with underscores

### 3. Logical Grouping
- Related files in same directory
- Clear subdirectory structure
- Easy to navigate

### 4. Minimal Root
- Only essential files in root
- Configuration files
- Entry points
- Main README

## 📊 File Count Summary

```
app/          ~30 files (Python modules)
tests/        ~40 files (Test files)
docs/         ~20 files (Documentation)
static/       ~5 files (Static assets)
root/         ~15 files (Config & scripts)
```

## 🔍 Finding Files

### Application Code
```bash
# All Python modules
ls app/**/*.py

# Services
ls app/services/*.py

# API routes
ls app/api/*.py
```

### Tests
```bash
# All tests
ls tests/test_*.py

# Integration tests
ls tests/test_*_integration.py

# PowerShell tests
ls tests/*.ps1
```

### Documentation
```bash
# All docs
ls docs/*.md

# Deployment docs
ls docs/*DEPLOY*.md

# Testing docs
ls docs/*TEST*.md
```

## 🚀 Quick Navigation

### For Development
- Start here: `README.md`
- Application code: `app/`
- Run locally: `python run.py`

### For Testing
- Test documentation: `tests/README.md`
- Run tests: `pytest tests/`
- Test scripts: `tests/*.ps1`

### For Deployment
- Deployment guide: `docs/RAILWAY_DEPLOYMENT_GUIDE.md`
- Configuration: `railway.json`
- Environment: `railway-env.json`

### For Troubleshooting
- Troubleshooting: `docs/RAILWAY_TROUBLESHOOTING.md`
- Test guide: `docs/HOW_TO_TEST.md`
- API quota: `docs/GEMINI_API_QUOTA_GUIDE.md`

## 📝 Maintenance

### Adding New Files

**Application Code:**
```bash
# Add to appropriate subdirectory
app/services/new_service.py
app/api/new_routes.py
```

**Tests:**
```bash
# Add to tests directory
tests/test_new_feature.py
```

**Documentation:**
```bash
# Add to docs directory
docs/NEW_GUIDE.md
```

### Cleaning Up

**Remove temporary files:**
```bash
# Python cache
rm -rf __pycache__
rm -rf .pytest_cache

# Logs
rm *.log
```

**Check for orphaned files:**
```bash
# Files not in git
git status --ignored
```

## ✅ Structure Benefits

1. **Easy Navigation** - Clear directory structure
2. **Quick Discovery** - Files grouped by purpose
3. **Clean Root** - Minimal clutter
4. **Scalable** - Easy to add new files
5. **Maintainable** - Clear organization

---

**Last Updated:** March 1, 2026
