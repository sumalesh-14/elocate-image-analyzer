# Tests Directory

This directory contains all test files for the Elocate Image Analyzer API.

## 📁 Test Structure

### Unit Tests
- `test_analyzer.py` - Core analyzer functionality
- `test_config_properties.py` - Configuration validation
- `test_input_sanitizer.py` - Input sanitization
- `test_fuzzy_matcher.py` - Fuzzy matching logic
- `test_database_matcher.py` - Database matching
- `test_query_cache.py` - Query caching

### Integration Tests
- `test_analyzer_database_integration.py` - Analyzer + Database
- `test_integration_complete_flow.py` - End-to-end flow
- `test_input_sanitization_integration.py` - Input validation flow
- `test_routes.py` - API routes

### Property-Based Tests
- `test_response_properties.py` - Response validation
- `test_db_connection_properties.py` - Database connection
- `test_database_matcher_properties.py` - Database matcher
- `test_fuzzy_matcher_properties.py` - Fuzzy matcher
- `test_cache_properties.py` - Cache behavior
- `test_error_handling_properties.py` - Error handling

### Database Tests
- `test_db_setup.py` - Database setup
- `test_db_connection.py` - Connection testing
- `test_direct_connection.py` - Direct connection
- `test_psycopg2.py` - psycopg2 driver
- `test_pooler_psycopg2.py` - Connection pooler
- `test_local_db.py` - Local database testing

### Security & Performance Tests
- `test_security.py` - Security validation
- `test_performance.py` - Performance benchmarks

### Deployment Tests
- `test_railway_deployment.ps1` - Railway deployment testing
- `test_api.ps1` - API endpoint testing
- `test_gemini_quota.py` - Gemini API quota checking

### Other Tests
- `test_hierarchical_dependencies.py` - Dependency testing
- `debug_test.py` - Debug utilities

## 🚀 Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_analyzer.py
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Integration Tests Only
```bash
pytest tests/ -m integration
```

### Run Property Tests
```bash
pytest tests/test_*_properties.py
```

## 🔧 Test Categories

### By Type
- **Unit Tests:** Test individual components in isolation
- **Integration Tests:** Test component interactions
- **Property Tests:** Test invariants and edge cases
- **E2E Tests:** Test complete workflows

### By Component
- **Analyzer:** Core analysis logic
- **Database:** Database connections and queries
- **API:** REST endpoints and middleware
- **Security:** Input validation and authentication
- **Performance:** Response times and resource usage

## 📊 Test Scripts

### PowerShell Scripts
- `test_railway_deployment.ps1` - Test deployed Railway app
- `test_api.ps1` - Test local API endpoints

### Python Scripts
- `test_local_db.py` - Comprehensive database connection test
- `test_gemini_quota.py` - Check Gemini API quota status

## 🎯 Quick Test Commands

```bash
# Test database connection
python tests/test_local_db.py

# Test Gemini API
python tests/test_gemini_quota.py

# Test Railway deployment
.\tests\test_railway_deployment.ps1

# Test local API
.\tests\test_api.ps1

# Run all unit tests
pytest tests/ -v

# Run with markers
pytest tests/ -m "not slow"
```

## 📝 Test Documentation

See `INTEGRATION_TESTS_README.md` for detailed integration test documentation.

## ✅ Test Coverage Goals

- Unit Tests: >80% coverage
- Integration Tests: All critical paths
- Property Tests: Edge cases and invariants
- E2E Tests: Main user workflows

---

**Last Updated:** March 1, 2026
