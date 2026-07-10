"""
Autonomous In-Memory Caching for INDB
No external dependencies - pure Python implementation.
"""

import time
import weakref
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, Tuple
from collections import OrderedDict
from threading import RLock
from core.constants import (
    CACHE_QUERY_MAXSIZE,
    CACHE_QUERY_TTL_SEC,
    CACHE_FUSION_MAXSIZE,
    CACHE_FUSION_TTL_SEC,
    CACHE_DECORATOR_DEFAULT_MAXSIZE,
    CACHE_DECORATOR_DEFAULT_TTL_SEC,
)


class TTLCache:
    """
    Time-To-Live cache with automatic expiration.
    Thread-safe implementation using OrderedDict.
    """
    
    def __init__(self, maxsize: int = CACHE_QUERY_MAXSIZE, ttl: int = CACHE_QUERY_TTL_SEC):
        """
        Initialize TTL cache.
        
        Args:
            maxsize: Maximum number of items in cache
            ttl: Time-to-live in seconds
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[str, Tuple[Any, float, float]] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            value, timestamp, item_ttl = self._cache[key]
            
            # Check expiration
            if time.time() - timestamp > item_ttl:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with current timestamp."""
        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.maxsize and key not in self._cache:
                self._cache.popitem(last=False)
            
            # Use provided TTL or default global TTL
            expiry = ttl if ttl is not None else self.ttl
            
            self._cache[key] = (value, time.time(), expiry)
            self._cache.move_to_end(key)
    
    def delete(self, key: str) -> bool:
        """Remove key from cache. Returns True if key existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "ttl": self.ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
            }
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns number removed."""
        with self._lock:
            now = time.time()
            expired = [
                key for key, (_, timestamp, item_ttl) in self._cache.items()
                if now - timestamp > item_ttl
            ]
            
            for key in expired:
                del self._cache[key]
            
            return len(expired)


class WeakValueCache:
    """
    Cache using weak references to values.
    Automatically removes entries when objects are garbage collected.
    """
    
    def __init__(self):
        self._cache: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._lock = RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            self._cache[key] = value
    
    def delete(self, key: str) -> None:
        """Remove key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


def ttl_cache(ttl: int = CACHE_DECORATOR_DEFAULT_TTL_SEC, maxsize: int = CACHE_DECORATOR_DEFAULT_MAXSIZE):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl: Time-to-live in seconds
        maxsize: Maximum cache size
    
    Example:
        @ttl_cache(ttl=60, maxsize=100)
        def expensive_query(param):
            return result
    """
    cache = TTLCache(maxsize=maxsize, ttl=ttl)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from args and kwargs
            key = str((args, tuple(sorted(kwargs.items()))))
            
            # Try cache first
            result = cache.get(key)
            if result is not None:
                return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        # Attach cache methods to function
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.stats
        
        return wrapper
    
    return decorator


# Global cache instances
query_cache = TTLCache(maxsize=CACHE_QUERY_MAXSIZE, ttl=CACHE_QUERY_TTL_SEC)      # 5 minutes
fusion_cache = TTLCache(maxsize=CACHE_FUSION_MAXSIZE, ttl=CACHE_FUSION_TTL_SEC)   # 10 minutes
event_cache = WeakValueCache()  # Weak references to Event objects


# Convenience functions
def cache_query(key: str, value: Any) -> None:
    """Cache a query result."""
    query_cache.set(key, value)


def get_cached_query(key: str) -> Optional[Any]:
    """Get cached query result."""
    return query_cache.get(key)


def invalidate_query_cache() -> None:
    """Clear all query caches."""
    query_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    return {
        "query_cache": query_cache.stats(),
        "fusion_cache": fusion_cache.stats(),
        "event_cache_size": event_cache.size(),
    }
