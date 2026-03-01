"""
Query cache service for database matching results.

This module provides a TTL-based cache for database query results to reduce
database load and improve response times for repeated queries.
"""

from typing import Any, Optional
from cachetools import TTLCache
import threading


class QueryCache:
    """
    Thread-safe query cache with TTL-based expiration.
    
    Uses cachetools.TTLCache to store database query results with automatic
    expiration after 5 minutes. Implements LRU eviction when max size is reached.
    
    Cache key format: {entity_type}:{normalized_text}:{context}
    Examples:
        - category:mobile_phone:
        - brand:apple:550e8400-e29b-41d4-a716-446655440001
        - model:iphone_14:550e8400-e29b-41d4-a716-446655440001:660e8400-e29b-41d4-a716-446655440001
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Initialize the query cache.
        
        Args:
            max_size: Maximum number of entries in the cache (default: 1000)
            ttl: Time-to-live in seconds for cache entries (default: 300 = 5 minutes)
        """
        self._cache = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key in format {entity_type}:{normalized_text}:{context}
        
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key in format {entity_type}:{normalized_text}:{context}
            value: Value to cache (typically a match result or None)
            ttl: Optional TTL override (not used with TTLCache, kept for interface compatibility)
        """
        with self._lock:
            self._cache[key] = value
    
    def clear(self) -> None:
        """
        Clear all entries from the cache.
        """
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """
        Get the current number of entries in the cache.
        
        Returns:
            Number of cached entries
        """
        with self._lock:
            return len(self._cache)
    
    @staticmethod
    def build_key(entity_type: str, normalized_text: str, context: str = "") -> str:
        """
        Build a cache key from components.
        
        Args:
            entity_type: Type of entity (category, brand, model)
            normalized_text: Normalized search text
            context: Optional context (e.g., category_id for brand queries)
        
        Returns:
            Formatted cache key
        """
        return f"{entity_type}:{normalized_text}:{context}"
