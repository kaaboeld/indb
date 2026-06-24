# INDB Testing Guide

## Test Suite Overview

INDB v1.0.0 includes comprehensive testing to ensure system integrity, data consistency, and protocol functionality.

## Test Categories

### 1. System Integrity Tests (`tests/integrity/test_system_audit.py`)

**Purpose:** Validate system health and data integrity on startup.

**Tests:**
- **Data Integrity**
  - Master key exists and valid
  - Database file integrity
  - Successful decryption
  - Event structure validation
  - No data corruption
  
- **Encryption Integrity**
  - Encryption/decryption roundtrip
  - Non-deterministic encryption (random nonce)
  - Wrong key detection
  - Tamper detection
  
- **System Health**
  - Required directories exist
  - Critical files present
  - Python imports work
  - Cache system functional
  - Bloom filter operational
  
- **Protocol Health**
  - HTTP server accessible
  - All endpoints registered

**Run:**
```bash
python3 tests/integrity/test_system_audit.py
```

### 2. Data Flow Tests (`tests/integrity/test_data_flows.py`)

**Purpose:** Validate all data paths through the system.

**Tests:**
- **Event Ingestion Flow**
  - Event creation → Kernel → Storage → Retrieval
  - Batch ingestion → Fusion → Storage
  - Memory → Disk → Reload → Memory
  
- **Query Flow**
  - Query → Filter → Cache → Results
  - Cache miss → Compute → Cache hit
  
- **Fusion Flow**
  - Events → Similarity → Fusion → Fused Event
  - Event → Bloom Filter → Dedup → Storage
  
- **Encryption Flow**
  - Data → Serialize → Encrypt → Decrypt → Deserialize
  
- **Protocol Flow**
  - HTTP Request → Parse → Ingest → Response
  - HTTP Query → Kernel → Cache → JSON

**Run:**
```bash
python3 tests/integrity/test_data_flows.py
```

### 3. Integration Tests (`tests/integration/test_protocols.py`)

**Purpose:** End-to-end protocol testing.

**Tests:**
- HTTP/REST API
- MessagePack protocol
- WebSocket subscriptions
- GraphQL queries
- Security features
- Performance features

**Run:**
```bash
pytest tests/integration/ -v
```

### 4. Load Testing (`tests/performance/load_test.py`)

**Purpose:** Benchmark 100k events/sec throughput.

**Metrics:**
- Throughput (events/sec)
- Latency (min/max/mean/median/P95/P99)
- Error rate
- Success rate

**Run:**
```bash
python3 tests/performance/load_test.py
```

## Startup Audit

**Automatic on server start:**
```bash
./start.sh
```

The startup audit runs automatically and validates:
1. ✅ Data integrity
2. ✅ Encryption system
3. ✅ System health
4. ✅ Protocol endpoints
5. ✅ Data flows

**Manual audit:**
```bash
python3 startup_audit.py
```

## Running All Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific category
pytest tests/integrity/ -v
pytest tests/integration/ -v
pytest tests/performance/ -v
```

## Test Requirements

```bash
pip install pytest pytest-asyncio httpx websockets
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run startup audit
        run: python3 startup_audit.py
      - name: Run all tests
        run: pytest tests/ -v
```

## Test Coverage Goals

- **System Integrity:** 100% (critical)
- **Data Flows:** 100% (critical)
- **Integration:** 90%+
- **Performance:** Baseline established

## Troubleshooting

### Audit Fails on Startup

```bash
# Check specific failure
python3 startup_audit.py

# Run individual test suites
python3 tests/integrity/test_system_audit.py
python3 tests/integrity/test_data_flows.py
```

### Integration Tests Fail

```bash
# Ensure server is running
./start.sh

# Run tests in another terminal
pytest tests/integration/ -v
```

### Load Test Fails

```bash
# Check server is accessible
curl http://localhost:8003/health

# Run with lower concurrency
# Edit tests/performance/load_test.py
# Change CONCURRENT_REQUESTS = 10
```

## Best Practices

1. **Always run startup audit** before production deployment
2. **Run integration tests** after any code changes
3. **Run load tests** before performance-critical releases
4. **Monitor test coverage** - aim for 90%+
5. **Fix failures immediately** - don't accumulate tech debt

## Continuous Monitoring

```bash
# Run audit periodically
watch -n 300 python3 startup_audit.py

# Monitor test results
pytest tests/ --junit-xml=test-results.xml
```
