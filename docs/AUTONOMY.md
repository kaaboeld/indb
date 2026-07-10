# INDB Autonomy Principles

## Core Philosophy

**INDB is AUTONOMOUS** - A self-contained, dependency-free database system.

## What This Means

### ✅ Allowed
- **Binary file storage** (`indb.bin`) - our own format
- **Pure Python** implementations
- **Built-in libraries** (hashlib, threading, asyncio, etc.)
- **Lightweight serialization** (msgpack, json)
- **Cryptography** (for security, not storage)
- **Network protocols** (HTTP, gRPC, WebSocket) - for API only

### ❌ Forbidden
- **External databases** (PostgreSQL, MySQL, MongoDB, Redis, etc.)
- **ORM frameworks** (SQLAlchemy, Django ORM, etc.)
- **Database clients** (pymongo, psycopg2, redis-py, etc.)
- **Dependency injection** from external systems
- **Cloud storage** dependencies (S3, GCS, etc.)

## Storage Architecture

```
INDB Storage (Autonomous)
├── indb.bin          # Binary event store (msgpack + AES-256-GCM)
├── indb.key          # Master encryption key
└── audit.bin         # Audit log (optional)

NO external databases
NO connection strings
NO database servers
```

## Why Autonomy?

1. **Zero Configuration** - Works out of the box
2. **No Infrastructure** - No database servers to manage
3. **Portable** - Copy `indb.bin` and it works
4. **Resilient** - No network dependencies
5. **Secure** - No attack surface from external DBs
6. **Fast** - No network latency
7. **Simple** - One binary file, one process

## Implementation

### Storage Layer
```python
# ✅ CORRECT - Autonomous
from storage.binary import save_encrypted, load_decrypted

events = load_decrypted()  # From indb.bin
save_encrypted(events)     # To indb.bin

# ❌ WRONG - External dependency
from pymongo import MongoClient
db = MongoClient("mongodb://...")
```

### Caching Layer
```python
# ✅ CORRECT - In-memory autonomous
from core.cache import TTLCache

cache = TTLCache(maxsize=1000, ttl=300)

# ❌ WRONG - External Redis
import redis
cache = redis.Redis(host="localhost")
```

### Deduplication
```python
# ✅ CORRECT - Bloom filter (in-memory)
from core.bloom import BloomFilter

bloom = BloomFilter(expected_elements=100000)

# ❌ WRONG - External database for dedup
# Using Redis/MongoDB for duplicate checking
```

## Dependencies Audit

### Removed
- ~~`pymongo`~~ - MongoDB client (REMOVED)
- ~~`redis`~~ - Redis client (NEVER ADDED)
- ~~`psycopg2`~~ - PostgreSQL client (NEVER ADDED)
- ~~`sqlalchemy`~~ - ORM framework (NEVER ADDED)

### Kept (Justified)
- `msgpack` - Binary serialization (lightweight, no server)
- `cryptography` - Encryption (local, no server)
- `fastapi` - HTTP API (not a database)
- `grpcio` - gRPC protocol (not a database)

## Future Considerations

### If We Need More Storage
- **Option 1**: Sharding `indb.bin` into multiple files
- **Option 2**: Memory-mapped files for large datasets
- **Option 3**: Custom index files (still binary, still autonomous)

### What We Will NEVER Do
- Add PostgreSQL "for better queries"
- Add Redis "for caching"
- Add MongoDB "for flexibility"
- Add Elasticsearch "for search"

**INDB is the database. It doesn't need another database.**

## Conclusion

INDB is:
- **Self-contained** - One binary file
- **Self-sufficient** - No external services
- **Self-reliant** - Pure Python implementation

This is our identity. This is our strength.
