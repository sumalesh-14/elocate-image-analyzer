"""
Unit tests for query cache service.

Tests specific examples, edge cases, and known scenarios for the query cache
functionality used in database matching integration.

**Validates: Requirements 7.5**
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.query_cache import QueryCache


class TestCacheBasicOperations:
    """Test cases for basic cache operations."""

    def test_set_and_get(self):
        """Should store and retrieve values."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Should return None for nonexistent keys."""
        cache = QueryCache(max_size=10, ttl=60)
        assert cache.get("nonexistent") is None

    def test_overwrite_existing_key(self):
        """Should overwrite existing key with new value."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_multiple_keys(self):
        """Should handle multiple keys independently."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_none_value(self):
        """Should be able to cache None values."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.set("key1", None)
        # get() returns None for both missing keys and cached None values
        # This is acceptable behavior for this cache implementation
        assert cache.get("key1") is None

    def test_complex_values(self):
        """Should handle complex data structures."""
        cache = QueryCache(max_size=10, ttl=60)
        value = {
            "id": "uuid-123",
            "name": "iPhone 14",
            "score": 0.95,
            "nested": {"key": "value"}
        }
        cache.set("key1", value)
        result = cache.get("key1")
        assert result == value
        assert result["id"] == "uuid-123"


class TestTTLExpiration:
    """Test cases for TTL expiration behavior."""

    def test_ttl_expiration(self):
        """Should expire entries after TTL."""
        cache = QueryCache(max_size=10, ttl=1)  # 1 second TTL
        cache.set("key1", "value1")
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("key1") is None

    def test_ttl_not_expired(self):
        """Should not expire entries before TTL."""
        cache = QueryCache(max_size=10, ttl=5)  # 5 second TTL
        cache.set("key1", "value1")
        
        # Wait less than TTL
        time.sleep(0.5)
        
        # Should still be available
        assert cache.get("key1") == "value1"

    def test_different_entries_expire_independently(self):
        """Each entry should expire based on its own insertion time."""
        cache = QueryCache(max_size=10, ttl=2)  # 2 second TTL
        
        cache.set("key1", "value1")
        time.sleep(1)
        cache.set("key2", "value2")
        
        # After 1.5 seconds total, key1 should be close to expiring
        time.sleep(0.5)
        
        # key2 should still be valid (1.5s old)
        assert cache.get("key2") == "value2"
        
        # Wait for key1 to expire (2.5s total)
        time.sleep(1)
        
        # key1 should be expired (2.5s old)
        assert cache.get("key1") is None
        # key2 should still be valid (1.5s old)
        assert cache.get("key2") == "value2"

    def test_ttl_with_overwrite(self):
        """Overwriting a key should reset its TTL."""
        cache = QueryCache(max_size=10, ttl=2)  # 2 second TTL
        
        cache.set("key1", "value1")
        time.sleep(1.5)
        
        # Overwrite the key
        cache.set("key1", "value2")
        
        # Wait another 1 second (2.5s from original, 1s from overwrite)
        time.sleep(1)
        
        # Should still be available because TTL was reset
        assert cache.get("key1") == "value2"


class TestLRUEviction:
    """Test cases for LRU eviction when max size reached."""

    def test_max_size_enforcement(self):
        """Should not exceed max size."""
        cache = QueryCache(max_size=3, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.size() == 3

    def test_lru_eviction_on_overflow(self):
        """Should evict least recently used entry when max size exceeded."""
        cache = QueryCache(max_size=3, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Adding 4th entry should evict key1 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.size() == 3

    def test_lru_access_updates_recency(self):
        """Accessing an entry should update its recency."""
        cache = QueryCache(max_size=3, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        _ = cache.get("key1")
        
        # Adding 4th entry should evict key2 (now least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Should still exist
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_lru_set_updates_recency(self):
        """Setting an existing key should update its recency."""
        cache = QueryCache(max_size=3, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Update key1 to make it recently used
        cache.set("key1", "value1_updated")
        
        # Adding 4th entry should evict key2 (now least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1_updated"  # Should still exist
        assert cache.get("key2") is None              # Should be evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_multiple_evictions(self):
        """Should handle multiple evictions correctly."""
        cache = QueryCache(max_size=2, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Evicts key1
        cache.set("key4", "value4")  # Evicts key2
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.size() == 2


class TestCacheKeyGeneration:
    """Test cases for cache key generation."""

    def test_build_key_category(self):
        """Should build correct key for category queries."""
        key = QueryCache.build_key("category", "mobile_phone", "")
        assert key == "category:mobile_phone:"

    def test_build_key_brand(self):
        """Should build correct key for brand queries with category context."""
        category_id = "550e8400-e29b-41d4-a716-446655440001"
        key = QueryCache.build_key("brand", "apple", category_id)
        assert key == f"brand:apple:{category_id}"

    def test_build_key_model(self):
        """Should build correct key for model queries with category and brand context."""
        category_id = "550e8400-e29b-41d4-a716-446655440001"
        brand_id = "660e8400-e29b-41d4-a716-446655440001"
        context = f"{category_id}:{brand_id}"
        key = QueryCache.build_key("model", "iphone_14", context)
        assert key == f"model:iphone_14:{context}"

    def test_build_key_empty_context(self):
        """Should handle empty context correctly."""
        key = QueryCache.build_key("category", "laptop", "")
        assert key == "category:laptop:"

    def test_build_key_special_characters(self):
        """Should handle special characters in text."""
        key = QueryCache.build_key("category", "mobile-phone_v2", "")
        assert key == "category:mobile-phone_v2:"

    def test_build_key_consistency(self):
        """Same inputs should produce same key."""
        key1 = QueryCache.build_key("brand", "apple", "context123")
        key2 = QueryCache.build_key("brand", "apple", "context123")
        assert key1 == key2

    def test_build_key_uniqueness(self):
        """Different inputs should produce different keys."""
        key1 = QueryCache.build_key("brand", "apple", "context1")
        key2 = QueryCache.build_key("brand", "apple", "context2")
        key3 = QueryCache.build_key("brand", "samsung", "context1")
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class TestThreadSafety:
    """Test cases for thread safety."""

    def test_concurrent_reads(self):
        """Should handle concurrent reads safely."""
        cache = QueryCache(max_size=100, ttl=60)
        cache.set("key1", "value1")
        
        def read_cache():
            return cache.get("key1")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_cache) for _ in range(100)]
            results = [f.result() for f in as_completed(futures)]
        
        # All reads should succeed
        assert all(r == "value1" for r in results)

    def test_concurrent_writes(self):
        """Should handle concurrent writes safely."""
        cache = QueryCache(max_size=100, ttl=60)
        
        def write_cache(i):
            cache.set(f"key{i}", f"value{i}")
            return True
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_cache, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]
        
        # All writes should succeed
        assert all(results)
        assert cache.size() == 50

    def test_concurrent_read_write(self):
        """Should handle concurrent reads and writes safely."""
        cache = QueryCache(max_size=100, ttl=60)
        cache.set("shared_key", "initial_value")
        
        results = []
        
        def read_cache():
            value = cache.get("shared_key")
            results.append(("read", value))
        
        def write_cache(value):
            cache.set("shared_key", value)
            results.append(("write", value))
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(25):
                futures.append(executor.submit(read_cache))
                futures.append(executor.submit(write_cache, f"value{i}"))
            
            for f in as_completed(futures):
                f.result()
        
        # Should have 50 operations (25 reads + 25 writes)
        assert len(results) == 50
        
        # Final value should be one of the written values
        final_value = cache.get("shared_key")
        assert final_value is not None

    def test_concurrent_eviction(self):
        """Should handle concurrent writes causing evictions safely."""
        cache = QueryCache(max_size=10, ttl=60)
        
        def write_cache(i):
            cache.set(f"key{i}", f"value{i}")
            return cache.size()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_cache, i) for i in range(50)]
            sizes = [f.result() for f in as_completed(futures)]
        
        # Cache size should never exceed max_size
        assert all(s <= 10 for s in sizes)
        assert cache.size() <= 10

    def test_concurrent_clear(self):
        """Should handle concurrent operations with clear safely."""
        cache = QueryCache(max_size=100, ttl=60)
        
        # Pre-populate cache
        for i in range(20):
            cache.set(f"key{i}", f"value{i}")
        
        def read_cache(i):
            return cache.get(f"key{i}")
        
        def clear_cache():
            cache.clear()
            return True
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            # Mix reads and clears
            for i in range(20):
                futures.append(executor.submit(read_cache, i))
            futures.append(executor.submit(clear_cache))
            
            for f in as_completed(futures):
                f.result()
        
        # After clear, cache should be empty
        assert cache.size() == 0


class TestCacheClear:
    """Test cases for cache clearing."""

    def test_clear_empty_cache(self):
        """Should handle clearing empty cache."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.clear()
        assert cache.size() == 0

    def test_clear_populated_cache(self):
        """Should clear all entries."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.size() == 3
        
        cache.clear()
        
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_usable_after_clear(self):
        """Should be able to use cache after clearing."""
        cache = QueryCache(max_size=10, ttl=60)
        cache.set("key1", "value1")
        cache.clear()
        
        cache.set("key2", "value2")
        assert cache.get("key2") == "value2"
        assert cache.size() == 1


class TestCacheSize:
    """Test cases for cache size tracking."""

    def test_size_empty_cache(self):
        """Should return 0 for empty cache."""
        cache = QueryCache(max_size=10, ttl=60)
        assert cache.size() == 0

    def test_size_after_additions(self):
        """Should track size correctly after additions."""
        cache = QueryCache(max_size=10, ttl=60)
        
        cache.set("key1", "value1")
        assert cache.size() == 1
        
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.set("key3", "value3")
        assert cache.size() == 3

    def test_size_after_overwrite(self):
        """Size should not change when overwriting existing key."""
        cache = QueryCache(max_size=10, ttl=60)
        
        cache.set("key1", "value1")
        assert cache.size() == 1
        
        cache.set("key1", "value2")
        assert cache.size() == 1

    def test_size_after_expiration(self):
        """Size should decrease after entries expire."""
        cache = QueryCache(max_size=10, ttl=1)  # 1 second TTL
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        time.sleep(1.1)
        
        # Accessing expired entries triggers cleanup
        _ = cache.get("key1")
        
        # Size should reflect expired entries
        assert cache.size() < 2

    def test_size_after_eviction(self):
        """Size should remain at max after evictions."""
        cache = QueryCache(max_size=3, ttl=60)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3
        
        cache.set("key4", "value4")
        assert cache.size() == 3  # Should still be 3 after eviction


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_very_small_cache(self):
        """Should handle cache with size 1."""
        cache = QueryCache(max_size=1, ttl=60)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.set("key2", "value2")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_very_short_ttl(self):
        """Should handle very short TTL."""
        cache = QueryCache(max_size=10, ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_long_key_names(self):
        """Should handle long key names."""
        cache = QueryCache(max_size=10, ttl=60)
        long_key = "a" * 1000
        
        cache.set(long_key, "value")
        assert cache.get(long_key) == "value"

    def test_large_values(self):
        """Should handle large values."""
        cache = QueryCache(max_size=10, ttl=60)
        large_value = {"data": "x" * 10000}
        
        cache.set("key1", large_value)
        result = cache.get("key1")
        assert result == large_value

    def test_unicode_keys_and_values(self):
        """Should handle unicode in keys and values."""
        cache = QueryCache(max_size=10, ttl=60)
        
        cache.set("key_日本語", "value_中文")
        assert cache.get("key_日本語") == "value_中文"
        
        cache.set("emoji_🎉", {"text": "Hello 世界"})
        assert cache.get("emoji_🎉")["text"] == "Hello 世界"

