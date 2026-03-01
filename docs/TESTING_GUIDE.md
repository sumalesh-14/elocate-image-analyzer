# Testing Guide for E-locate Image Analyzer

## Quick Start

### 1. Test Database Connection

Run the simple connection test:
```bash
cd elocate-image-analyzer
.\venv\Scripts\python.exe test_db_connection.py
```

**Expected Output:**
```
✓ Connection successful!
✓ PostgreSQL version: PostgreSQL 17.6...
✓ Database is ready for use!
```

### 2. Start the Server

```bash
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`

### 3. Test the API

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Test Interface (Browser)
Open in browser: `http://localhost:8000/test-ui`

#### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Specific Test Categories

```bash
# Unit tests
pytest tests/test_analyzer.py tests/test_database_matcher.py -v

# Integration tests
pytest tests/test_integration_complete_flow.py -v

# Property-based tests
pytest tests/test_*_properties.py -v

# Security tests
pytest tests/test_security.py -v

# Performance tests
pytest tests/test_performance.py -v
```

### With Coverage
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

View coverage report: Open `htmlcov/index.html` in browser

## Database Configuration

Your `.env` file is configured with:
- **Host:** aws-1-ap-southeast-1.pooler.supabase.com
- **Port:** 6543 (pgbouncer)
- **Database:** postgres
- **SSL:** Required
- **Connection pooling:** Enabled with statement_cache_size=0 for pgbouncer

## Current Status

✓ Database connection: **Working**
✓ Server: **Running on port 8000**
⚠ Gemini API: **Quota exceeded** (wait ~44 seconds or use different API key)

## Troubleshooting

### Gemini API Quota Exceeded
If you see "quota exceeded" errors:
1. Wait for the retry delay (shown in error message)
2. Or get a new API key from https://ai.google.dev/
3. Update `GEMINI_API_KEY` in `.env` file

### Database Connection Issues
- Verify credentials in `.env` file
- Check network connectivity
- Run `test_db_connection.py` for detailed diagnostics

### Server Won't Start
- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`
- Check if port 8000 is already in use
