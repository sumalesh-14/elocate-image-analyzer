# 🔍 Elocate Image Analyzer — How to Run

FastAPI service that uses **Google Gemini Vision** to identify electronic devices from images.  
Uses a **two-pass grounded approach** to match category, brand, and model against your PostgreSQL database.  
Auto-seeds new entries when a device is not yet in the DB.

---

## 📋 Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 14+ (your Elocate DB) |
| Google Gemini API Key | Required |

---

## ⚡ Quick Start (Local Dev)

### 1. Clone & enter the folder

```bash
cd elocate-image-analyzer
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Then open `.env` and set:

```env
# ── Required ──────────────────────────────────────────────────────
GEMINI_API_KEY=your_google_gemini_api_key_here
API_KEY=your_service_api_key_here          # used to authenticate requests

# ── CORS ──────────────────────────────────────────────────────────
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# ── Database ──────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=5432
DB_NAME=elocate
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_SSL_MODE=require                        # use 'disable' for local without SSL

# ── Optional (defaults are fine for local dev) ────────────────────
LOG_LEVEL=INFO                             # DEBUG gives verbose logs
MAX_FILE_SIZE_MB=10
RATE_LIMIT=10/minute
REQUEST_TIMEOUT=30
```

### 5. Run the server

```bash
python run.py
```

Or with uvicorn directly (with auto-reload for dev):

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be live at: **http://localhost:8000**

---

## 🌐 Key Endpoints

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/v1/analyze` | Upload a device image for analysis |
| `GET` | `/health` | Service health check |
| `GET` | `/test-ui` | Interactive browser test UI |
| `GET` | `/docs` | Swagger API documentation |

---

## 🧪 Test in the Browser

Open: **http://localhost:8000/test-ui**

This loads a built-in HTML test interface where you can:
- Upload an image
- Enter your API key
- See the full JSON analysis result

---

## 📡 API Usage

### Analyze a device image

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "X-API-Key: your_service_api_key_here" \
  -F "file=@/path/to/device.jpg"
```

### Health check

```bash
curl http://localhost:8000/health
```

### Example response

```json
{
  "success": true,
  "processingTimeMs": 3241,
  "data": {
    "category": "Mobile Phone",
    "brand": "Samsung",
    "model": "Galaxy S24",
    "deviceType": "Android Smartphone",
    "confidenceScore": 0.92,
    "category_id": "uuid-here",
    "brand_id": "uuid-here",
    "model_id": "uuid-here",
    "database_status": "success",
    "severity": "high",
    "contains_hazardous_materials": true,
    "contains_precious_metals": true
  }
}
```

---

## 🗄️ How the Two-Pass + Auto-Seed Works

```
Image uploaded
  │
  ├── Pass 1 → Gemini picks category from your DB list (or signals "NEW: Pen Drive")
  │            ↳ If NEW → auto-inserts into device_category table
  │
  ├── Pass 2 → Gemini picks brand from filtered DB list (or "NEW: Corsair")
  │            ↳ If NEW → auto-inserts into device_brand + category_brand mapping
  │
  └── Model → Fuzzy-matched or "NEW: Ultra Fit 128GB"
               ↳ If NEW → auto-inserts into device_model with brand+category link
```

> New entries are only seeded if **confidence ≥ 70%** to avoid polluting the DB with bad data.

---

## 🐳 Docker

### Build & run

```bash
docker build -t elocate-image-analyzer .
docker run -p 8000:8000 --env-file .env elocate-image-analyzer
```

---

## 🚀 Deploy to Railway

The project is pre-configured for Railway:

1. Push to GitHub
2. Connect the repo in Railway
3. Add all environment variables from `.env` in Railway's **Variables** tab
4. Railway auto-detects `nixpacks.toml` and deploys

Deployed URL pattern: `https://elocate-python-production.up.railway.app`

---

## 🧾 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini Vision API key |
| `API_KEY` | ✅ | — | Auth key for incoming requests |
| `ALLOWED_ORIGINS` | ✅ | — | Comma-separated CORS origins |
| `DB_HOST` | ✅ | — | PostgreSQL host |
| `DB_PORT` | ✅ | `5432` | PostgreSQL port |
| `DB_NAME` | ✅ | — | Database name |
| `DB_USER` | ✅ | — | DB username |
| `DB_PASSWORD` | ✅ | — | DB password |
| `DB_SSL_MODE` | ❌ | `require` | `require` or `disable` |
| `LOG_LEVEL` | ❌ | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MAX_FILE_SIZE_MB` | ❌ | `10` | Max upload size in MB |
| `RATE_LIMIT` | ❌ | `10/minute` | Rate limit per IP |
| `REQUEST_TIMEOUT` | ❌ | `30` | Gemini API timeout (seconds) |
| `CATEGORY_MATCH_THRESHOLD` | ❌ | `0.80` | Fuzzy match threshold (0.0–1.0) |
| `BRAND_MATCH_THRESHOLD` | ❌ | `0.80` | Fuzzy match threshold (0.0–1.0) |
| `MODEL_MATCH_THRESHOLD` | ❌ | `0.75` | Fuzzy match threshold (0.0–1.0) |
| `QUERY_CACHE_TTL` | ❌ | `300` | DB result cache TTL (seconds) |
| `QUERY_CACHE_MAX_SIZE` | ❌ | `1000` | Max cache entries |

---

## 🗂️ Project Structure

```
elocate-image-analyzer/
├── app/
│   ├── api/
│   │   ├── routes.py          # API endpoints
│   │   └── middleware.py      # CORS, rate limiting, auth
│   ├── models/
│   │   └── response.py        # Pydantic response models
│   ├── services/
│   │   ├── analyzer.py        # Main orchestration (two-pass flow)
│   │   ├── gemini_service.py  # Pass-1 & Pass-2 Gemini prompts
│   │   ├── database_matcher.py# DB fetch, match, and auto-seed
│   │   ├── db_connection.py   # asyncpg connection pool
│   │   ├── fuzzy_matcher.py   # rapidfuzz string matching
│   │   ├── image_validator.py # File type/size/safety checks
│   │   ├── input_sanitizer.py # SQL injection prevention
│   │   └── query_cache.py     # TTL-based result cache
│   ├── utils/
│   │   ├── logger.py          # Structured JSON / development logger
│   │   └── orchestration_log.py # 🆕 Emoji terminal trace printer
│   ├── config.py              # Settings from environment variables
│   └── main.py                # FastAPI app, startup/shutdown
├── static/
│   └── test_interface.html    # Browser test UI
├── tests/                     # pytest test suite
├── .env.example               # Environment variable template
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build
├── run.py                     # Entry point (handles PORT env var)
├── start.sh                   # Shell start script for Railway
└── RUNNING.md                 # ← you are here
```

---

## 🏃 Run Tests

```bash
pytest tests/ -v
```

With coverage report:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

---

## 📋 Console Output

Every analysis request prints a structured trace to the terminal:

```
════════════════════════════════════════════════════════════════════
  🔍  NEW DEVICE ANALYSIS REQUEST
════════════════════════════════════════════════════════════════════
    File                  samsung.jpg
    Size                  487.3 KB

  ✅  Image validated OK

🧠  PASS 1 — Category Identification  (8 DB categories offered)
────────────────────────────────────────────────────────────────────
    Raw pick              Mobile Phone
    Confidence            95%

  ✅  Category matched → Mobile Phone (100%)

🏷️   PASS 2 — Brand & Model  (12 brands offered)
────────────────────────────────────────────────────────────────────
  ✅  Brand matched → Samsung (100%)
  ✅  Model matched → Galaxy S24 (100%)

════════════════════════════════════════════════════════════════════
  ✅  ANALYSIS COMPLETE  (3241 ms)
════════════════════════════════════════════════════════════════════
```

> Items marked `[NEW ✨]` were auto-seeded into the database during this request.
