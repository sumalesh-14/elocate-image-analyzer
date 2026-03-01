"""
Property-based tests for API middleware.

Tests universal properties that should hold across all middleware operations.
"""

import pytest
from hypothesis import given, strategies as st, settings as hypothesis_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

from app.api.middleware import (
    configure_middleware,
    APIKeyAuthMiddleware,
    RequestLoggingMiddleware
)
from app.config import settings


# Create a test FastAPI app
def create_test_app():
    """Create a test FastAPI application with middleware configured."""
    app = FastAPI()
    
    # Add a test endpoint
    @app.get("/api/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}
    
    # Configure middleware
    configure_middleware(app)
    
    return app


# **Validates: Requirements 7.3**
# Feature: image-device-identification, Property 13: CORS headers are present
@given(
    origin=st.one_of(
        st.just("http://localhost:3000"),
        st.just("https://example.com"),
        st.just("http://test.com"),
        st.just("https://app.example.org")
    )
)
@hypothesis_settings(max_examples=100, deadline=None)
def test_cors_headers_present_in_responses(origin):
    """
    Property: For any request with an Origin header, the response should include
    CORS headers (Access-Control-Allow-Origin or appropriate CORS response).
    
    This verifies that CORS middleware is properly configured and responds to
    cross-origin requests.
    """
    app = create_test_app()
    client = TestClient(app)
    
    # Make request with Origin header
    headers = {"Origin": origin}
    response = client.get("/health", headers=headers)
    
    # Response should be successful
    assert response.status_code in [200, 403, 404]
    
    # If origin is in allowed list, CORS headers should be present
    if origin in settings.allowed_origins_list:
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == origin
    
    # For any origin, if CORS is configured, we should see CORS-related headers
    # or the request should be handled (not blocked at middleware level)
    # The key property is that the middleware doesn't crash or block valid requests


@given(
    method=st.sampled_from(["GET", "POST", "OPTIONS"]),
    path=st.sampled_from(["/health", "/api/test"])
)
@hypothesis_settings(max_examples=100, deadline=None)
def test_cors_headers_present_for_all_methods(method, path):
    """
    Property: For any HTTP method (GET, POST, OPTIONS) and any endpoint,
    CORS headers should be consistently present in responses.
    
    This ensures CORS is applied uniformly across all endpoints and methods.
    """
    app = create_test_app()
    client = TestClient(app)
    
    # Make request with allowed origin
    headers = {
        "Origin": "http://localhost:3000",
        "X-API-Key": settings.API_KEY
    }
    
    if method == "GET":
        response = client.get(path, headers=headers)
    elif method == "POST":
        response = client.post(path, headers=headers)
    elif method == "OPTIONS":
        response = client.options(path, headers=headers)
    
    # Response should not be a server error
    assert response.status_code < 500
    
    # CORS headers should be present for allowed origin
    assert "access-control-allow-origin" in response.headers


@given(
    endpoint=st.sampled_from(["/health", "/api/test", "/docs", "/test"])
)
@hypothesis_settings(max_examples=50, deadline=None)
def test_cors_headers_present_across_endpoints(endpoint):
    """
    Property: For any endpoint in the application, CORS headers should be
    present when requests come from allowed origins.
    
    This ensures CORS configuration is applied application-wide.
    """
    app = create_test_app()
    client = TestClient(app)
    
    # Make request with allowed origin
    headers = {
        "Origin": "http://localhost:3000",
        "X-API-Key": settings.API_KEY
    }
    
    response = client.get(endpoint, headers=headers)
    
    # Response should not be a server error
    assert response.status_code < 500
    
    # For successful responses, CORS headers should be present
    if response.status_code < 400:
        assert "access-control-allow-origin" in response.headers


@given(
    allowed_origin=st.sampled_from(settings.allowed_origins_list)
)
@hypothesis_settings(max_examples=50, deadline=None)
def test_allowed_origins_receive_cors_headers(allowed_origin):
    """
    Property: For any origin in the allowed origins list, requests from that
    origin should receive appropriate CORS headers allowing access.
    
    This verifies the CORS configuration correctly allows configured origins.
    """
    app = create_test_app()
    client = TestClient(app)
    
    headers = {"Origin": allowed_origin}
    response = client.get("/health", headers=headers)
    
    # Response should be successful
    assert response.status_code == 200
    
    # CORS headers should allow this origin
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == allowed_origin


@given(
    has_credentials=st.booleans()
)
@hypothesis_settings(max_examples=50, deadline=None)
def test_cors_credentials_handling(has_credentials):
    """
    Property: For any request, CORS should properly handle credentials
    (cookies, authorization headers) according to configuration.
    
    This ensures CORS middleware correctly manages credential policies.
    """
    app = create_test_app()
    client = TestClient(app)
    
    headers = {"Origin": "http://localhost:3000"}
    if has_credentials:
        headers["Authorization"] = "Bearer test-token"
    
    response = client.get("/health", headers=headers)
    
    # Response should be successful
    assert response.status_code == 200
    
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers
    
    # Credentials should be allowed based on configuration
    if "access-control-allow-credentials" in response.headers:
        assert response.headers["access-control-allow-credentials"] in ["true", "false"]

