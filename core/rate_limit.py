"""
Rate Limitation Configuration for INDB

Uses slowapi to provide token bucket rate limiting.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter with client IP as the key
limiter = Limiter(key_func=get_remote_address)

class RateLimits:
    """Standard rate limits"""
    UNLIMITED = None
    DEFAULT = "100/minute"
    STRICT = "5/minute"      # For auth endpoints
    INGEST = "10000/minute"  # For event creation (increased for bulk loading)
    BURST = "20/minute"      # For expensive operations
