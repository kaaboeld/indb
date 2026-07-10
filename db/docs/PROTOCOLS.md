# INDB Protocol Specification

## 1. Transport Layer

INDB is a multi-protocol database. It exposes different interfaces for different use cases.

### HTTP/REST (Standard)
- **Port**: `8000`
- **Use Case**: Management, CRUD, queries, interpretation.
- **Format**: JSON (default) or BSON (optimized).
- **Security**: TLS 1.3 required in production.

### WebSocket (Real-Time)
- **Port**: `8000` (same as HTTP)
- **Endpoint**: `/ws`
- **Use Case**: Real-time event broadcasting ("New Memory formed"), Live Context updates.
- **Events**:
  - `new_event`: Stream of incoming raw events.
  - `fusion`: Notification when events are merged.

### UDP (High-Performance Ingest)
- **Port**: `9001`
- **Latency**: ~0.87 ms (Ultra-Low)
- **Use Case**: "Fire and Forget" ingestion of high-frequency sensor data.
- **Format**: MessagePack or BSON.
- **Ack**: None (Unreliable by design).

### gRPC (Binary Stream)
- **Port**: `50051`
- **Latency**: ~270 ms (10KB Chunked Payload)
- **Use Case**: Efficient upload of large binary blobs (Images, Audio) via Client Streaming.
- **RPC**: `IngestStream` (Client Streaming -> Server).
- **Features**:
    - Chunked Upload support.
    - Metadata + Payload separation.
    - Async Kernel Bridge.

---

## 2. Security Layer

### Response Signing
Every response from INDB is cryptographically signed to prevent tampering (Man-in-the-Middle).

**Structure**:
```json
{
  "data": { ... },
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "...",
    "signature": "...",
    "timestamp": 1700000000
  }
}
```

### End-to-End Encryption (Blind Store)
Data in the `blind_payload` field is opaque to the server.
1. **Client** encrypts data (ChaCha20-Poly1305).
2. **Server** stores the blob.
3. **Server** cannot index, read, or interpret this blob.
4. **Client** retrieves and decrypts locally.

---

## 3. Cognitive Tools

| Tool | Purpose |
|------|---------|
| **Prism** | Paradox-aware synthesis. Transforms events into meaning, returns competing readings, perception gap, `has_unread_essence`. |
| **Echo** | Resonance detection. Harmonic analysis: tokens (20%), emotion (30%), location (50%). Finds similar events. |
| **Instinct** | Adrenaline reflexes. Modes: Analytical (0.0), Alert (0.5), Instinctive (1.0). Fast pattern matching. |
| **Deduction** | Chain inference. Seeds → Echo expansion → temporal/spatial/token chains → conclusion. |
| **Blind** | Zero-knowledge storage. `blind_payload` — ChaCha20, server never reads. Requires `timestamp` + `location`. |

---

## 4. Data Types

| Type | Description |
|------|-------------|
| `raw_data_anchor` | List of abstract tokens (e.g. `["red", "alert"]`). |
| `location` | Spatial anchor string (or Lat/Lon object). |
| `blind_payload` | Base64 encoded encrypted string. |
| `is_fused` | Boolean indicating if this is a compressed memory. |
