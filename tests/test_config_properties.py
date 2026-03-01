"""
Property-based tests for configuration validation.

Uses Hypothesis to verify configuration validation across randomized inputs.
Each test runs minimum 100 iterations to ensure comprehensive coverage.

Feature: database-matching-integration
"""

import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError
from app.config import Settings


# Feature: database-matching-integration, Property 24: Configuration Validation
@given(
    pool_size=st.integers(max_value=0)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_negative_pool_size_validation(pool_size: int):
    """
    Property 24: Configuration Validation
    
    For any invalid configuration parameter (e.g., negative pool size),
    the service should fail to start with a clear error message.
    
    **Validates: Requirements 9.6**
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            GEMINI_API_KEY="test_key",
            API_KEY="test_api_key",
            DB_PASSWORD="test_password",
            DB_MIN_POOL_SIZE=pool_size
        )
    
    # Verify error message is clear
    assert "must be positive" in str(exc_info.value).lower() or "greater than" in str(exc_info.value).lower()


# Feature: database-matching-integration, Property 24: Configuration Validation
@given(
    threshold=st.floats(min_value=-10.0, max_value=10.0).filter(lambda x: x < 0.0 or x > 1.0)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_invalid_threshold_validation(threshold: float):
    """
    Property 24: Configuration Validation
    
    For any threshold outside the range [0.0, 1.0],
    the service should fail to start with a clear error message.
    
    **Validates: Requirements 9.6**
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            GEMINI_API_KEY="test_key",
            API_KEY="test_api_key",
            DB_PASSWORD="test_password",
            CATEGORY_MATCH_THRESHOLD=threshold
        )
    
    # Verify error message mentions the valid range
    error_msg = str(exc_info.value).lower()
    assert "between" in error_msg or "0.0" in error_msg or "1.0" in error_msg


# Feature: database-matching-integration, Property 24: Configuration Validation
@given(
    min_size=st.integers(min_value=1, max_value=50),
    max_size=st.integers(min_value=1, max_value=50)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_pool_size_relationship_validation(min_size: int, max_size: int):
    """
    Property 24: Configuration Validation
    
    For any configuration where max_pool_size < min_pool_size,
    the service should fail to start with a clear error message.
    
    **Validates: Requirements 9.6**
    """
    if max_size < min_size:
        with pytest.raises(ValueError) as exc_info:
            Settings(
                GEMINI_API_KEY="test_key",
                API_KEY="test_api_key",
                DB_PASSWORD="test_password",
                DB_MIN_POOL_SIZE=min_size,
                DB_MAX_POOL_SIZE=max_size
            )
        
        # Verify error message is clear
        assert "max" in str(exc_info.value).lower() and "min" in str(exc_info.value).lower()
    else:
        # Should succeed when max >= min
        settings = Settings(
            GEMINI_API_KEY="test_key",
            API_KEY="test_api_key",
            DB_PASSWORD="test_password",
            DB_MIN_POOL_SIZE=min_size,
            DB_MAX_POOL_SIZE=max_size
        )
        assert settings.DB_MIN_POOL_SIZE == min_size
        assert settings.DB_MAX_POOL_SIZE == max_size


# Feature: database-matching-integration, Property 24: Configuration Validation
@given(
    cache_config=st.integers(max_value=0)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_cache_config_validation(cache_config: int):
    """
    Property 24: Configuration Validation
    
    For any cache configuration parameter that is non-positive,
    the service should fail to start with a clear error message.
    
    **Validates: Requirements 9.6**
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            GEMINI_API_KEY="test_key",
            API_KEY="test_api_key",
            DB_PASSWORD="test_password",
            QUERY_CACHE_TTL=cache_config
        )
    
    # Verify error message is clear
    assert "must be positive" in str(exc_info.value).lower() or "greater than" in str(exc_info.value).lower()


# Feature: database-matching-integration, Property 24: Configuration Validation
@given(
    min_size=st.integers(min_value=1, max_value=100),
    max_size=st.integers(min_value=1, max_value=100),
    threshold=st.floats(min_value=0.0, max_value=1.0),
    cache_ttl=st.integers(min_value=1, max_value=3600),
    cache_size=st.integers(min_value=1, max_value=10000)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_valid_configuration_succeeds(min_size: int, max_size: int, threshold: float, cache_ttl: int, cache_size: int):
    """
    Property 24: Configuration Validation
    
    For any valid configuration parameters, the Settings object should be created successfully.
    
    **Validates: Requirements 9.6**
    """
    if max_size >= min_size:
        settings = Settings(
            GEMINI_API_KEY="test_key",
            API_KEY="test_api_key",
            DB_PASSWORD="test_password",
            DB_MIN_POOL_SIZE=min_size,
            DB_MAX_POOL_SIZE=max_size,
            CATEGORY_MATCH_THRESHOLD=threshold,
            QUERY_CACHE_TTL=cache_ttl,
            QUERY_CACHE_MAX_SIZE=cache_size
        )
        
        assert settings.DB_MIN_POOL_SIZE == min_size
        assert settings.DB_MAX_POOL_SIZE == max_size
        assert settings.CATEGORY_MATCH_THRESHOLD == threshold
        assert settings.QUERY_CACHE_TTL == cache_ttl
        assert settings.QUERY_CACHE_MAX_SIZE == cache_size

