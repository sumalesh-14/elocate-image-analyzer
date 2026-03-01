"""
Performance tests for database matching integration.

Benchmarks query execution times and concurrent request handling to ensure
performance requirements are met.

Validates Requirements: 2.6, 3.8, 4.8, 7.1, 7.3, 7.4
"""

import pytest
import asyncio
import time
from typing import List
from statistics import mean, median

from app.services.database_matcher import DatabaseMatcher
from tests.test_db_setup import (
    TEST_CATEGORY_MOBILE_ID,
    TEST_BRAND_APPLE_ID,
    TEST_MODEL_IPHONE_14_ID,
)


@pytest.mark.asyncio
@pytest.mark.performance
async def test_category_query_execution_time(test_db_connection):
    """
    Benchmark category query execution time (<50ms requirement).
    
    Validates Requirements: 2.6, 7.1
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # Warm up
    await matcher.match_category("Mobile Phone")
    
    # Clear cache to ensure we're testing database query time
    matcher.cache.clear()
    
    # Run multiple iterations
    execution_times = []
    iterations = 10
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = await matcher.match_category("Mobile Phone")
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000
        execution_times.append(execution_time_ms)
        
        # Verify result is correct
        assert result is not None
        assert result.id == TEST_CATEGORY_MOBILE_ID
        
        # Clear cache between iterations
        matcher.cache.clear()
    
    # Calculate statistics
    avg_time = mean(execution_times)
    median_time = median(execution_times)
    max_time = max(execution_times)
    
    print(f"\nCategory Query Performance:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  Median: {median_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    # Verify performance requirement (<50ms)
    assert avg_time < 50, f"Average category query time {avg_time:.2f}ms exceeds 50ms requirement"
    assert max_time < 100, f"Max category query time {max_time:.2f}ms is too high"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_brand_query_execution_time(test_db_connection):
    """
    Benchmark brand query execution time (<50ms requirement).
    
    Validates Requirements: 3.8, 7.1
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # Warm up
    await matcher.match_brand("Apple", TEST_CATEGORY_MOBILE_ID)
    
    # Clear cache
    matcher.cache.clear()
    
    # Run multiple iterations
    execution_times = []
    iterations = 10
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = await matcher.match_brand("Apple", TEST_CATEGORY_MOBILE_ID)
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000
        execution_times.append(execution_time_ms)
        
        # Verify result is correct
        assert result is not None
        assert result.id == TEST_BRAND_APPLE_ID
        
        # Clear cache between iterations
        matcher.cache.clear()
    
    # Calculate statistics
    avg_time = mean(execution_times)
    median_time = median(execution_times)
    max_time = max(execution_times)
    
    print(f"\nBrand Query Performance:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  Median: {median_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    # Verify performance requirement (<50ms)
    assert avg_time < 50, f"Average brand query time {avg_time:.2f}ms exceeds 50ms requirement"
    assert max_time < 100, f"Max brand query time {max_time:.2f}ms is too high"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_model_query_execution_time(test_db_connection):
    """
    Benchmark model query execution time (<50ms requirement).
    
    Validates Requirements: 4.8, 7.1
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # Warm up
    await matcher.match_model("iPhone 14 Pro", TEST_CATEGORY_MOBILE_ID, TEST_BRAND_APPLE_ID)
    
    # Clear cache
    matcher.cache.clear()
    
    # Run multiple iterations
    execution_times = []
    iterations = 10
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = await matcher.match_model("iPhone 14 Pro", TEST_CATEGORY_MOBILE_ID, TEST_BRAND_APPLE_ID)
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000
        execution_times.append(execution_time_ms)
        
        # Verify result is correct
        assert result is not None
        assert result.id == TEST_MODEL_IPHONE_14_ID
        
        # Clear cache between iterations
        matcher.cache.clear()
    
    # Calculate statistics
    avg_time = mean(execution_times)
    median_time = median(execution_times)
    max_time = max(execution_times)
    
    print(f"\nModel Query Performance:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  Median: {median_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    # Verify performance requirement (<50ms)
    assert avg_time < 50, f"Average model query time {avg_time:.2f}ms exceeds 50ms requirement"
    assert max_time < 100, f"Max model query time {max_time:.2f}ms is too high"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_total_matching_time(test_db_connection):
    """
    Benchmark total matching time for complete flow (<100ms requirement).
    
    Validates Requirements: 7.1
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # Warm up
    await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
    
    # Clear cache
    matcher.cache.clear()
    
    # Run multiple iterations
    execution_times = []
    iterations = 10
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000
        execution_times.append(execution_time_ms)
        
        # Verify result is correct
        assert result.category is not None
        assert result.brand is not None
        assert result.model is not None
        assert result.database_status == "success"
        
        # Clear cache between iterations
        matcher.cache.clear()
    
    # Calculate statistics
    avg_time = mean(execution_times)
    median_time = median(execution_times)
    max_time = max(execution_times)
    
    print(f"\nTotal Matching Performance:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  Median: {median_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    # Verify performance requirement (<100ms)
    assert avg_time < 100, f"Average total matching time {avg_time:.2f}ms exceeds 100ms requirement"
    assert max_time < 200, f"Max total matching time {max_time:.2f}ms is too high"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_cache_hit_response_time(test_db_connection):
    """
    Benchmark cache hit response time (<5ms requirement).
    
    Validates Requirements: 7.3, 7.4
    """
    matcher = DatabaseMatcher(test_db_connection)
    
    # First query to populate cache
    await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
    
    # Run multiple iterations with cache hits
    execution_times = []
    iterations = 20
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        result = await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000
        execution_times.append(execution_time_ms)
        
        # Verify result is correct
        assert result.category is not None
        assert result.brand is not None
        assert result.model is not None
    
    # Calculate statistics
    avg_time = mean(execution_times)
    median_time = median(execution_times)
    max_time = max(execution_times)
    
    print(f"\nCache Hit Performance:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  Median: {median_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    # Verify performance requirement (<5ms)
    assert avg_time < 5, f"Average cache hit time {avg_time:.2f}ms exceeds 5ms requirement"
    assert max_time < 10, f"Max cache hit time {max_time:.2f}ms is too high"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_request_handling(test_db_pool):
    """
    Test concurrent request handling (50 simultaneous requests).
    
    Validates Requirements: 7.3
    """
    # Create matcher with connection pool
    async def perform_match(pool, request_id: int):
        """Perform a single match operation."""
        async with pool.acquire() as conn:
            matcher = DatabaseMatcher(conn)
            
            # Vary the queries to test different scenarios
            queries = [
                ("Mobile Phone", "Apple", "iPhone 14 Pro"),
                ("Laptop", "Dell", "XPS 15"),
                ("Tablet", "Apple", "iPad Pro"),
                ("Mobile Phone", "Samsung", "Galaxy S23"),
            ]
            
            query = queries[request_id % len(queries)]
            
            start_time = time.perf_counter()
            result = await matcher.match_device(*query)
            end_time = time.perf_counter()
            
            execution_time_ms = (end_time - start_time) * 1000
            
            return {
                'request_id': request_id,
                'execution_time_ms': execution_time_ms,
                'success': result.database_status in ["success", "partial_success"]
            }
    
    # Run 50 concurrent requests
    num_requests = 50
    
    start_time = time.perf_counter()
    tasks = [perform_match(test_db_pool, i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks)
    end_time = time.perf_counter()
    
    total_time_ms = (end_time - start_time) * 1000
    
    # Analyze results
    execution_times = [r['execution_time_ms'] for r in results]
    success_count = sum(1 for r in results if r['success'])
    
    avg_time = mean(execution_times)
    median_time = median(execution_times)
    max_time = max(execution_times)
    min_time = min(execution_times)
    
    print(f"\nConcurrent Request Performance ({num_requests} requests):")
    print(f"  Total time: {total_time_ms:.2f}ms")
    print(f"  Successful requests: {success_count}/{num_requests}")
    print(f"  Average request time: {avg_time:.2f}ms")
    print(f"  Median request time: {median_time:.2f}ms")
    print(f"  Min request time: {min_time:.2f}ms")
    print(f"  Max request time: {max_time:.2f}ms")
    print(f"  Requests per second: {(num_requests / total_time_ms * 1000):.2f}")
    
    # Verify all requests succeeded
    assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"
    
    # Verify reasonable performance under load
    assert avg_time < 200, f"Average time under load {avg_time:.2f}ms is too high"
    assert max_time < 500, f"Max time under load {max_time:.2f}ms is too high"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_connection_pool_efficiency(test_db_pool):
    """
    Test that connection pool efficiently reuses connections.
    
    Validates Requirements: 7.3
    """
    # Perform multiple sequential queries
    num_queries = 20
    
    async def perform_query(pool):
        async with pool.acquire() as conn:
            matcher = DatabaseMatcher(conn)
            return await matcher.match_category("Mobile Phone")
    
    start_time = time.perf_counter()
    for _ in range(num_queries):
        result = await perform_query(test_db_pool)
        assert result is not None
    end_time = time.perf_counter()
    
    total_time_ms = (end_time - start_time) * 1000
    avg_time_per_query = total_time_ms / num_queries
    
    print(f"\nConnection Pool Efficiency ({num_queries} sequential queries):")
    print(f"  Total time: {total_time_ms:.2f}ms")
    print(f"  Average per query: {avg_time_per_query:.2f}ms")
    
    # Verify connection reuse is efficient
    assert avg_time_per_query < 100, f"Average query time {avg_time_per_query:.2f}ms suggests inefficient connection reuse"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_cache_effectiveness_under_load(test_db_connection):
    """
    Test cache effectiveness with repeated queries.
    
    Validates Requirements: 7.5
    """
    matcher = DatabaseMatcher(test_db_connection)
    matcher.cache.clear()
    
    # First query - cache miss
    start_time = time.perf_counter()
    result1 = await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
    first_query_time = (time.perf_counter() - start_time) * 1000
    
    # Subsequent queries - cache hits
    cache_hit_times = []
    for _ in range(10):
        start_time = time.perf_counter()
        result = await matcher.match_device("Mobile Phone", "Apple", "iPhone 14 Pro")
        cache_hit_time = (time.perf_counter() - start_time) * 1000
        cache_hit_times.append(cache_hit_time)
        
        # Verify same result
        assert result.category.id == result1.category.id
        assert result.brand.id == result1.brand.id
        assert result.model.id == result1.model.id
    
    avg_cache_hit_time = mean(cache_hit_times)
    
    print(f"\nCache Effectiveness:")
    print(f"  First query (cache miss): {first_query_time:.2f}ms")
    print(f"  Average cache hit: {avg_cache_hit_time:.2f}ms")
    print(f"  Speedup: {first_query_time / avg_cache_hit_time:.1f}x")
    
    # Verify cache provides significant speedup
    assert avg_cache_hit_time < first_query_time / 5, "Cache should provide at least 5x speedup"
    assert avg_cache_hit_time < 5, f"Cache hit time {avg_cache_hit_time:.2f}ms exceeds 5ms requirement"
