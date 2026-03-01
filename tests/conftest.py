"""
Pytest configuration and fixtures for tests.
"""

import os
import pytest

# Set up test environment variables before any imports
os.environ['GEMINI_API_KEY'] = 'test-gemini-api-key'
os.environ['API_KEY'] = 'test-api-key'
os.environ['ALLOWED_ORIGINS'] = 'http://localhost:3000'
os.environ['MAX_FILE_SIZE_MB'] = '10'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['REQUEST_TIMEOUT'] = '30'
os.environ['RATE_LIMIT'] = '10/minute'

# Database test configuration
os.environ['TEST_DATABASE_URL'] = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/elocate_test'
)

# Import test database fixtures
pytest_plugins = ['tests.test_db_setup']

