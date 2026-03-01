# Integration and Performance Tests

This directory contains comprehensive integration, performance, and security tests for the database matching integration feature.

## Test Categories

### 1. Integration Tests (`test_integration_complete_flow.py`)
Tests end-to-end scenarios from image upload through database matching to response.

**Scenarios covered:**
- Complete match (category + brand + model found)
- Partial match (category found, brand not found)
- Fuzzy matching with variations ("iphone" → "iPhone")
- Threshold rejection (very different strings)
- Database unavailable (graceful degradation)
- Cache effectiveness

**Requirements validated:** 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 7.5, 8.2

### 2. Performance Tests (`test_performance.py`)
Benchmarks query execution times and concurrent request handling.

**Benchmarks:**
- Category query execution time (<50ms)
- Brand query execution time (<50ms)
- Model query execution time (<50ms)
- Total matching time (<100ms)
- Cache hit response time (<5ms)
- Concurrent request handling (50 simultaneous requests)

**Requirements validated:** 2.6, 3.8, 4.8, 7.1, 7.3, 7.4

### 3. Security Tests (`test_security.py`)
Tests SQL injection prevention, credential sanitization, and security measures.

**Security scenarios:**
- SQL injection attempts in category/brand/model inputs
- Special characters and encoding safety
- Connection string sanitization in logs
- Parameterized query usage
- Read-only permission verification
- SSL/TLS configuration
- Input length limits
- Unicode and null byte handling

**Requirements validated:** 10.1, 10.2, 10.3, 10.4, 10.5

## Prerequisites

### Database Setup

1. **Create test database:**
```bash
createdb elocate_test
```

2. **Set environment variable:**
```bash
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/elocate_test"
```

Or use a different connection string for your test database.

### Python Dependencies

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

Required packages:
- pytest
- pytest-asyncio
- asyncpg
- hypothesis
- Pillow

## Running Tests

### Run All Integration Tests
```bash
pytest tests/test_integration_complete_flow.py -v
```

### Run Performance Tests
```bash
pytest tests/test_performance.py -v -m performance
```

### Run Security Tests
```bash
pytest tests/test_security.py -v -m security
```

### Run All Tests in Task 10
```bash
pytest tests/test_integration_complete_flow.py tests/test_performance.py tests/test_security.py -v
```

### Run with Coverage
```bash
pytest tests/test_integration_complete_flow.py tests/test_performance.py tests/test_security.py --cov=app.services --cov-report=html
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.security` - Security tests

### Run Only Integration Tests
```bash
pytest -m integration -v
```

### Run Only Performance Tests
```bash
pytest -m performance -v
```

### Run Only Security Tests
```bash
pytest -m security -v
```

## Test Database Fixtures

The `test_db_setup.py` module provides fixtures for test database management:

- `test_db_connection` - Single connection with tables and seed data
- `test_db_pool` - Connection pool for performance testing

### Test Data

The fixtures create the following test data:

**Categories:**
- Mobile Phone (UUID: 550e8400-e29b-41d4-a716-446655440001)
- Laptop (UUID: 550e8400-e29b-41d4-a716-446655440002)
- Tablet (UUID: 550e8400-e29b-41d4-a716-446655440003)

**Brands:**
- Apple (UUID: 660e8400-e29b-41d4-a716-446655440001)
- Samsung (UUID: 660e8400-e29b-41d4-a716-446655440002)
- Dell (UUID: 660e8400-e29b-41d4-a716-446655440003)

**Models:**
- iPhone 14 Pro (UUID: 770e8400-e29b-41d4-a716-446655440001)
- Galaxy S23 (UUID: 770e8400-e29b-41d4-a716-446655440002)
- XPS 15 (UUID: 770e8400-e29b-41d4-a716-446655440003)
- iPad Pro (UUID: 770e8400-e29b-41d4-a716-446655440004)

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Typical |
|--------|--------|---------|
| Category query | <50ms | 10-30ms |
| Brand query | <50ms | 10-30ms |
| Model query | <50ms | 10-30ms |
| Total matching | <100ms | 30-80ms |
| Cache hit | <5ms | 0.5-2ms |
| Concurrent (50 req) | All succeed | 100% success |

## Troubleshooting

### Database Connection Issues

If tests fail with connection errors:

1. Verify PostgreSQL is running:
```bash
pg_isready
```

2. Check test database exists:
```bash
psql -l | grep elocate_test
```

3. Verify connection string:
```bash
echo $TEST_DATABASE_URL
```

### Performance Test Failures

If performance tests fail:

1. Ensure database has proper indexes (created by fixtures)
2. Check system load (other processes may affect timing)
3. Run tests multiple times to account for variance
4. Consider adjusting thresholds for slower systems

### Security Test Failures

If security tests fail:

1. Verify input sanitizer is properly implemented
2. Check that parameterized queries are used (not string concatenation)
3. Ensure logging doesn't include sensitive information
4. Verify SSL/TLS configuration in settings

## CI/CD Integration

For continuous integration, use:

```bash
# Run all tests with coverage
pytest tests/test_integration_complete_flow.py tests/test_performance.py tests/test_security.py \
  --cov=app.services \
  --cov-report=xml \
  --cov-report=term \
  -v

# Generate coverage report
coverage report -m
```

## Notes

- Integration tests require a running PostgreSQL instance
- Performance tests may vary based on system resources
- Security tests verify code behavior, not database configuration
- All tests use fixtures that automatically clean up after execution
- Tests are designed to be idempotent and can run in any order
