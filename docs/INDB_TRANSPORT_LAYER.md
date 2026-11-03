# INDB Transport Layer Documentation
**Unified Transport Protocol (UTP) Architecture**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Transport Layer Architecture](#transport-layer-architecture)
3. [Raft Transport](#raft-transport)
4. [Ingestion Protocols](#ingestion-protocols)
5. [Performance](#performance)
6. [Usage Examples](#usage-examples)

---

## Introduction

### What is UTP?

**UTP (Unified Transport Protocol)** in INDB is not a single protocol — it is a **unified architecture** for working with multiple transport protocols simultaneously.

### Philosophy: One Kernel, Many Interfaces

```
                    ┌─────────────────┐
                    │   INDB Kernel   │
                    │  (Single Truth) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │  HTTP   │         │   UDP   │         │  gRPC   │
   │ (REST)  │         │ (Fast)  │         │(Binary) │
   └─────────┘         └─────────┘         └─────────┘
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │WebSocket│         │GraphQL  │         │   MCP   │
   │(Stream) │         │(Flex)   │         │(Context)│
   └─────────┘         └─────────┘         └─────────┘
```

**Principle**: All protocols are converted into `INDBKernel` calls — the single source of truth.

---

## Transport Layer Architecture

### Abstraction Layers

```
Layer 1: Protocol Adapters
    ↓ HTTP, UDP, gRPC, WebSocket, GraphQL, MCP
    
Layer 2: Kernel Interface
    ↓ interpret(), query(), create_event()
    
Layer 3: Core Engine
    ↓ INDB, Fusion, Cache, Storage
    
Layer 4: Persistence
    ↓ indb.bin, raft.log, audit.bin
```

### File Structure

```
backend/
├── protocols/           # Transport protocols
│   ├── udp_server.py   # UDP (port 9001)
│   ├── ws_server.py    # WebSocket (port 8003)
│   └── http_protocol/  # HTTP handlers
│
├── interfaces/          # API interfaces
│   ├── rest/           # REST API
│   ├── grpc/           # gRPC service
│   ├── graphql/        # GraphQL endpoint
│   └── mcp/            # Model Context Protocol
│
├── core/
│   ├── kernel.py       # Unified interface
│   └── raft/
│       └── transport.py # Raft transport
│
└── main.py             # FastAPI app (HTTP coordinator)
```

---

## Raft Transport

### Purpose

**Raft Transport** is a specialised transport layer for **intra-cluster communication**.

### File: `core/raft/transport.py`

```python
class RaftTransport:
    """Transport layer for Raft communication (HTTP implementation)."""
    
    def __init__(self, timeout: float = 0.5, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
```

### Core Methods

#### 1. Request Vote RPC

```python
async def request_vote(
    self, 
    target_url: str, 
    term: int, 
    candidate_id: str
) -> bool:
    """Request vote for leader election"""
    payload = {
        "term": term, 
        "candidate_id": candidate_id
    }
    resp = await self._send_rpc("POST", target_url, "vote", payload)
    return resp.get("vote_granted", False) if resp else False
```

**Usage**:
```
Candidate → Follower: "Vote for me! (term=5)"
Follower → Candidate: "OK, voting for you" or "No, already voted"
```

#### 2. Append Entries RPC

```python
async def append_entries(
    self,
    target_url: str,
    term: int,
    leader_id: str,
    entries: list,
    prev_log_index: int = 0,
    prev_log_term: int = 0,
    leader_commit: int = 0
) -> bool:
    """Heartbeat and log replication"""
    payload = {
        "term": term,
        "leader_id": leader_id,
        "entries": entries,  # Empty = heartbeat
        "prev_log_index": prev_log_index,
        "prev_log_term": prev_log_term,
        "leader_commit": leader_commit
    }
    resp = await self._send_rpc("POST", target_url, "append", payload)
    return resp.get("success", False) if resp else False
```

**Two modes**:

1. **Heartbeat** (entries = [])
   ```
   Leader → Followers: "I am alive! (term=5)"
   Followers → Leader: "Acknowledged, you are leader"
   ```

2. **Replication** (entries = [event1, event2, ...])
   ```
   Leader → Followers: "Write these events to log"
   Followers → Leader: "Written, commit_index updated"
   ```

### Retry Logic

```python
async def _send_rpc(self, method, target_url, endpoint, payload):
    """Generic RPC sender with retry logic"""
    for attempt in range(self.max_retries):  # 3 attempts
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            if attempt < self.max_retries - 1:
                await asyncio.sleep(0.05 * (attempt + 1))  # Linear backoff
    return None
```

**Strategy**:
- Timeout: 0.5s
- Retries: 3 attempts
- Backoff: 50ms, 100ms, 150ms

---

## Ingestion Protocols

### 1. HTTP/REST (port 8003)

**File**: `main.py` (FastAPI)

**Characteristics**:
- Synchronous request-response
- JSON or MessagePack payload, chosen by `Accept`
- Ed25519 signatures
- CORS support

**Example**:
```bash
curl -X POST http://localhost:8000/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data_anchor": ["fast", "red"],
    "location": "highway_101"
  }'
```

**Content negotiation**: send `Accept: application/msgpack` to any `/api/v2` endpoint and the
same payload comes back as MessagePack, with `meta.format` naming the format used.

```bash
curl -s -H "Accept: application/msgpack" http://localhost:8000/api/v2/events -o events.msgpack
```

A JSON object carries its signature in the body. A MessagePack body — like a JSON array —
has nowhere to put one, so the signature travels in headers instead and covers the response
bytes verbatim:

| Header | Meaning |
|---|---|
| `X-INDB-Signature` | Ed25519 signature, base64 |
| `X-INDB-Public-Key` | Public key, base64 |
| `X-INDB-Key-Id` | Key fingerprint |
| `X-INDB-Signed-At` | Unix timestamp |

**Latency**: ~2ms

---

### 2. UDP (port 9001)

**File**: `protocols/udp_server.py`

**Characteristics**:
- Fire-and-forget (no ACK)
- MessagePack serialization
- Minimum latency
- For IoT sensors

**Server code**:
```python
import socket
import msgpack
from core.instance import indb

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 9001))

while True:
    data, addr = sock.recvfrom(65535)
    payload = msgpack.unpackb(data)
    
    # Direct kernel call
    indb.ingest(
        raw_data_anchor=payload['raw_data_anchor'],
        location=payload['location']
    )
```

**Client example**:
```python
import socket
import msgpack

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
data = msgpack.packb({
    "raw_data_anchor": ["temperature", "25C"],
    "location": "sensor_01"
})
sock.sendto(data, ('localhost', 9001))
```

**One answer, one datagram**: a query response has to fit 65507 bytes, so a query without an
explicit `limit` is capped at 100 events, and a response that still does not fit is trimmed
until it does. The metadata says what happened:

```python
{"metadata": {"total_events": 100, "limit": 100, "returned_events": 63, "truncated": True}}
```

Ask for a narrower slice, or use HTTP when the full result matters more than the latency.

**On Fly.io**: the UDP listener binds `fly-global-services:9001` (required by the platform
proxy). Reach it via the app's public hostname or IP — `indb.fly.dev:9001` or the allocated
Fly IPv4 — not `api.indb.tech`, which is HTTP-only.

**Latency**: ~0.4ms

---

### 3. gRPC (port 50051)

**File**: `interfaces/grpc/server.py`

**Characteristics**:
- Binary protocol (Protobuf)
- Bidirectional streaming
- For large data volumes
- Type-safe

**On Fly.io**: connect to `indb.fly.dev:50051` or the app's public IPv4. The custom API
domain (`api.indb.tech`) terminates HTTPS only — gRPC is plain TCP on a separate port.

**Proto definition**:
```protobuf
service INDBService {
  rpc ListEvents(ListEventsRequest) returns (ListEventsResponse);
  rpc IngestStream(stream IngestRequest) returns (IngestResponse);
}

message IngestRequest {
  repeated string raw_data_anchor = 1;
  string location = 2;
  bytes binary_payload = 3;
}
```

**Example**:
```python
import grpc
from interfaces.grpc import indb_pb2, indb_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = indb_pb2_grpc.INDBServiceStub(channel)

# Stream events
def event_generator():
    for i in range(1000):
        yield indb_pb2.IngestRequest(
            raw_data_anchor=["sensor", f"reading_{i}"],
            location="datacenter"
        )

response = stub.IngestStream(event_generator())
```

**Latency**: ~1ms (streaming)

---

### 4. WebSocket (port 8003)

**File**: `protocols/ws_server.py`

**Characteristics**:
- Persistent connection
- Real-time bidirectional
- Subscription model
- Event broadcasting

**Server**:
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.subscriptions = {}
    
    async def broadcast(self, message, event_type="all"):
        """Broadcast to subscribed clients"""
        for ws in self.active_connections:
            subscription = self.subscriptions.get(ws)
            if subscription and event_type in subscription.event_types:
                await ws.send_text(message)
```

**Client**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe
ws.send(JSON.stringify({
  action: 'subscribe',
  event_types: ['new_event', 'fusion'],
  locations: ['highway_101']
}));

// Receive events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
};
```

**Latency**: <10ms (push)

---

### 5. GraphQL (port 8003)

**File**: `interfaces/graphql/schema.py`

**Characteristics**:
- Flexible queries
- Single endpoint
- Type system
- Introspection

**Schema**:
```graphql
type Event {
  id: ID!
  timestamp: Float!
  location: String!
  tokens: [String!]!
  is_fused: Boolean!
  fusion_count: Int!
}

type Query {
  events(limit: Int, offset: Int): [Event!]!
  search(query: String!, fuzzy: Boolean): [Event!]!
}

type Mutation {
  createEvent(
    raw_data_anchor: [String!]!
    location: String!
  ): Event!
}
```

**Query example**:
```graphql
query {
  events(limit: 5) {
    id
    location
    tokens
    fusion_count
  }
}
```

**Latency**: ~3ms

---

### 6. MCP (Model Context Protocol)

**File**: `interfaces/mcp/server.py`

**Characteristics**:
- AI-native protocol
- Context-aware
- Tool calling
- Resource management

**Example**:
```python
from mcp.server import Server

server = Server("indb-mcp")

@server.list_tools()
async def list_tools():
    return [
        {
            "name": "query_events",
            "description": "Query INDB events with context",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context": {"type": "object"},
                    "limit": {"type": "integer"}
                }
            }
        }
    ]

@server.call_tool()
async def call_tool(name, arguments):
    if name == "query_events":
        return await indb.interpret(
            context=arguments["context"],
            limit=arguments.get("limit", 10)
        )
```

**Latency**: ~5ms

---

## Performance

### Protocol Comparison

| Protocol | Latency | Throughput | Use Case |
|----------|-------------|------------------------|----------|
| **UDP** | 0.4ms | 100k+ events/sec | IoT Sensors |
| **HTTP** | 2ms | 50k events/sec | Web Applications |
| **gRPC** | 1ms | 80k events/sec | Microservices |
| **WebSocket** | <10ms | 30k events/sec | Real-time UI |
| **GraphQL** | 3ms | 40k events/sec | Flexible Queries |
| **MCP** | 5ms | 20k events/sec | AI Agents |

### Optimizations

1. **Connection pooling** (HTTP/gRPC)
2. **Binary serialization** (gRPC, UDP)
3. **Async I/O** (all protocols)
4. **Batch processing** (HTTP, gRPC)
5. **Compression** (gRPC, HTTP)

---

## Usage Examples

### Scenario 1: IoT Sensor Network

```python
# 1000 sensors send data every second
import socket
import msgpack
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for sensor_id in range(1000):
    data = msgpack.packb({
        "raw_data_anchor": ["temperature", f"{20 + sensor_id % 10}C"],
        "location": f"sensor_{sensor_id}"
    })
    sock.sendto(data, ('indb-server', 9001))
    time.sleep(0.001)  # 1ms between sends
```

**Result**: 1000 events/sec via UDP

---

### Scenario 2: Web Application

```javascript
// React app with real-time updates
const ws = new WebSocket('ws://indb-server:8003/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    event_types: ['new_event']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateUI(data);
};

// Create event via HTTP
async function createEvent(tokens, location) {
  const response = await fetch('http://indb-server:8003/api/v2/events', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      raw_data_anchor: tokens,
      location: location
    })
  });
  return response.json();
}
```

---

### Scenario 3: Microservice Architecture

```python
# Service A → INDB via gRPC
import grpc
from interfaces.grpc import indb_pb2, indb_pb2_grpc

channel = grpc.insecure_channel('indb-server:50051')
stub = indb_pb2_grpc.INDBServiceStub(channel)

# Batch ingestion
def ingest_batch(events):
    def event_generator():
        for event in events:
            yield indb_pb2.IngestRequest(
                raw_data_anchor=event['tokens'],
                location=event['location']
            )
    
    response = stub.IngestStream(event_generator())
    return response

# Service B → INDB via HTTP
import httpx

async def query_events(context):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://indb-server:8003/api/v2/interpret',
            json={'context': context, 'limit': 100}
        )
        return response.json()
```

---

### Scenario 4: AI Agent with MCP

```python
from mcp.client import Client

client = Client()
await client.connect("http://indb-server:8003/mcp")

# AI agent requests contextual data
result = await client.call_tool(
    "query_events",
    {
        "context": {
            "mood": "Analytical",
            "goal": "Find anomalies",
            "time_range": "last_hour"
        },
        "limit": 50
    }
)

# Analyse results
for event in result['events']:
    if event['fusion_count'] > 100:
        print(f"Anomaly detected: {event['location']}")
```

---

## Conclusion

### Unified Transport Protocol = Flexibility

INDB supports **6 transport protocols** simultaneously:

1. ✅ **UDP** — for speed (0.4ms)
2. ✅ **HTTP** — for compatibility (2ms)
3. ✅ **gRPC** — for microservices (1ms)
4. ✅ **WebSocket** — for real-time (<10ms)
5. ✅ **GraphQL** — for flexibility (3ms)
6. ✅ **MCP** — for AI (5ms)

### Raft Transport = Reliability

Intra-cluster communication via **Raft Transport**:
- Request Vote RPC (leader election)
- Append Entries RPC (replication + heartbeat)
- Retry logic (3 attempts, linear backoff)
- Timeout: 0.5s

### Principle: One Kernel, Many Interfaces

```
All roads lead to the Kernel
    ↓
Kernel → INDB Core
    ↓
Fusion → Cache → Storage
    ↓
indb.bin (Single source of truth)
```

**INDB Transport Layer is an architecture that lets you choose the right tool for each job.**.**

---

*Documentation created: January 31, 2026*  
*INDB version: 0.11.1*
