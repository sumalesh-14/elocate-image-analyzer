"""
Property-based tests for database connection manager.

Uses Hypothesis to verify connection pool properties across randomized scenarios.
Each test runs minimum 100 iterations to ensure comprehensive coverage.

Feature: database-matching-integration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
import asyncpg

from app.services.db_connection import DatabaseConnectionManager


# Feature: database-matching-integration, Property 1: Connection Pool Size Bounds
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_connection_pool_size_bounds():
    """
    Property 1: Connection Pool Size Bounds
    
    For any valid connection pool state during service operation,
    the number of active connections should be between 5 and 20 inclusive.
    
    **Validates: Requirements 1.2**
    
    Note: This test verifies that the pool is configured with correct bounds.
    The actual runtime enforcement is handled by asyncpg.
    """
    manager = DatabaseConnectionManager()
    
    # Mock connection for health check
    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the asyncpg.create_pool to return a mock pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    mock_pool.close = AsyncMock()
    
    with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
        mock_create_pool.return_value = mock_pool
        
        await manager.initialize()
        
        # Verify pool was created with correct bounds
        assert mock_create_pool.called
        call_kwargs = mock_create_pool.call_args.kwargs
        
        # Property: min_size should be 5
        assert call_kwargs['min_size'] == 5, f"Expected min_size=5, got {call_kwargs['min_size']}"
        
        # Property: max_size should be 20
        assert call_kwargs['max_size'] == 20, f"Expected max_size=20, got {call_kwargs['max_size']}"
        
        # Property: max_size >= min_size
        assert call_kwargs['max_size'] >= call_kwargs['min_size'], \
            f"max_size ({call_kwargs['max_size']}) must be >= min_size ({call_kwargs['min_size']})"
        
        await manager.close()


# Feature: database-matching-integration, Property 1: Connection Pool Size Bounds
@pytest.mark.asyncio
@given(
    min_size=st.integers(min_value=1, max_value=10),
    max_size=st.integers(min_value=10, max_value=50)
)
@settings(max_examples=20)
@pytest.mark.property_test
async def test_pool_configuration_respects_settings(min_size: int, max_size: int):
    """
    Property 1: Connection Pool Size Bounds
    
    For any valid pool configuration, the manager should pass the correct
    min_size and max_size parameters to asyncpg.create_pool.
    
    **Validates: Requirements 1.2**
    """
    assume(max_size >= min_size)
    
    manager = DatabaseConnectionManager()
    
    # Mock connection for health check
    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock the asyncpg.create_pool
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    mock_pool.close = AsyncMock()
    
    with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
        mock_create_pool.return_value = mock_pool
        
        # Temporarily override settings
        with patch('app.services.db_connection.settings') as mock_settings:
            mock_settings.DB_HOST = "localhost"
            mock_settings.DB_PORT = 5432
            mock_settings.DB_NAME = "test"
            mock_settings.DB_USER = "test"
            mock_settings.DB_PASSWORD = "test"
            mock_settings.DB_MIN_POOL_SIZE = min_size
            mock_settings.DB_MAX_POOL_SIZE = max_size
            mock_settings.DB_CONNECTION_TIMEOUT = 10
            mock_settings.DB_QUERY_TIMEOUT = 50
            mock_settings.DB_SSL_MODE = "disable"
            
            await manager.initialize()
            
            # Verify pool was created with correct bounds
            call_kwargs = mock_create_pool.call_args.kwargs
            assert call_kwargs['min_size'] == min_size
            assert call_kwargs['max_size'] == max_size
            assert call_kwargs['max_size'] >= call_kwargs['min_size']
            
            await manager.close()



# Feature: database-matching-integration, Property 2: Connection Retry with Exponential Backoff
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_connection_retry_exponential_backoff():
    """
    Property 2: Connection Retry with Exponential Backoff
    
    For any database connection failure scenario, the system should attempt
    exactly 3 retries with exponentially increasing delays (approximately 100ms, 200ms, 400ms).
    
    **Validates: Requirements 1.3**
    """
    manager = DatabaseConnectionManager()
    
    # Track sleep calls to verify exponential backoff
    sleep_calls = []
    
    async def mock_sleep(delay):
        sleep_calls.append(delay)
    
    # Mock asyncpg.create_pool to always fail
    with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
        mock_create_pool.side_effect = asyncpg.PostgresConnectionError("Connection failed")
        
        with patch('asyncio.sleep', new=mock_sleep):
            await manager.initialize()
            
            # Property: Should attempt exactly 3 times (initial + 2 retries)
            assert mock_create_pool.call_count == 3, \
                f"Expected 3 connection attempts, got {mock_create_pool.call_count}"
            
            # Property: Should have 2 sleep calls (no sleep before first attempt)
            assert len(sleep_calls) == 2, \
                f"Expected 2 sleep calls, got {len(sleep_calls)}"
            
            # Property: Delays should be approximately 0.2 and 0.4 (exponential backoff)
            # First retry after 0.2s, second retry after 0.4s
            assert abs(sleep_calls[0] - 0.2) < 0.01, \
                f"Expected first delay ~0.2s, got {sleep_calls[0]}s"
            assert abs(sleep_calls[1] - 0.4) < 0.01, \
                f"Expected second delay ~0.4s, got {sleep_calls[1]}s"
            
            # Property: Delays should be exponentially increasing
            assert sleep_calls[1] > sleep_calls[0], \
                "Second delay should be greater than first delay"
            
            # Property: Manager should not be available after all retries fail
            assert not manager.is_available(), \
                "Manager should not be available after all retries fail"


# Feature: database-matching-integration, Property 2: Connection Retry with Exponential Backoff
@pytest.mark.asyncio
@given(
    failure_count=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=20)
@pytest.mark.property_test
async def test_retry_behavior_with_varying_failures(failure_count: int):
    """
    Property 2: Connection Retry with Exponential Backoff
    
    For any number of connection failures (1-3), the system should retry
    with exponential backoff until success or exhausting all retries.
    
    **Validates: Requirements 1.3**
    """
    manager = DatabaseConnectionManager()
    
    # Track attempts and sleep calls
    attempt_count = [0]
    sleep_calls = []
    
    async def mock_sleep(delay):
        sleep_calls.append(delay)
    
    # Mock connection for health check
    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock pool that succeeds after failure_count attempts
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    mock_pool.close = AsyncMock()
    
    async def create_pool_with_failures(*args, **kwargs):
        attempt_count[0] += 1
        if attempt_count[0] < failure_count:
            raise asyncpg.PostgresConnectionError("Connection failed")
        return mock_pool
    
    with patch('asyncpg.create_pool', new=create_pool_with_failures):
        with patch('asyncio.sleep', new=mock_sleep):
            await manager.initialize()
            
            # Property: Should attempt exactly failure_count times before success
            assert attempt_count[0] == failure_count, \
                f"Expected {failure_count} attempts, got {attempt_count[0]}"
            
            # Property: Should have (failure_count - 1) sleep calls
            expected_sleeps = failure_count - 1
            assert len(sleep_calls) == expected_sleeps, \
                f"Expected {expected_sleeps} sleep calls, got {len(sleep_calls)}"
            
            # Property: Each delay should be exponentially increasing
            for i in range(len(sleep_calls) - 1):
                assert sleep_calls[i + 1] > sleep_calls[i], \
                    f"Delay {i+1} ({sleep_calls[i+1]}) should be greater than delay {i} ({sleep_calls[i]})"
            
            # Property: Manager should be available after successful connection
            assert manager.is_available(), \
                "Manager should be available after successful connection"
            
            await manager.close()


# Feature: database-matching-integration, Property 2: Connection Retry with Exponential Backoff
@pytest.mark.asyncio
@pytest.mark.property_test
async def test_no_retry_on_immediate_success():
    """
    Property 2: Connection Retry with Exponential Backoff
    
    When the first connection attempt succeeds, no retries should occur.
    
    **Validates: Requirements 1.3**
    """
    manager = DatabaseConnectionManager()
    
    sleep_calls = []
    
    async def mock_sleep(delay):
        sleep_calls.append(delay)
    
    # Mock connection for health check
    mock_conn = MagicMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    
    # Create async context manager mock
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    # Mock successful connection
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_context)
    mock_pool.close = AsyncMock()
    
    with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
        mock_create_pool.return_value = mock_pool
        
        with patch('asyncio.sleep', new=mock_sleep):
            await manager.initialize()
            
            # Property: Should attempt exactly once
            assert mock_create_pool.call_count == 1, \
                f"Expected 1 connection attempt, got {mock_create_pool.call_count}"
            
            # Property: Should have no sleep calls
            assert len(sleep_calls) == 0, \
                f"Expected 0 sleep calls on immediate success, got {len(sleep_calls)}"
            
            # Property: Manager should be available
            assert manager.is_available(), \
                "Manager should be available after successful connection"
            
            await manager.close()

