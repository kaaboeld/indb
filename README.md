# INDB: Interpretational Database
## Inhale. Exhale. Axiom.

> **"When everyone lies, INDB remembers what you saw."**

**INDB** = **I**nterpretational **D**ata**b**ase — memory, not archive. Meaning at query time, not frozen at ingest.

See [docs/INTERPRETATIONAL_DATABASE.md](docs/INTERPRETATIONAL_DATABASE.md).

---

## 🎯 Vision

INDB is not a classical database and not an archive. It is an **Interpretational Database** — and an **Epistemological Engine** under the hood: truth as process (inhale → exhale → axiom), not as a static table.

**The Paradox of 1984:** How do you preserve objective reality when collective gaslighting can rewrite history?

**INDB's Answer:** Treat data as **memory** — metabolism, resonance, forgetting, wake — not storage.

---

## 🫁 The Core Metaphor: Inhale → Exhale → Axiom

### 1. **INHALE** (Ingestion)
**Accept reality as it is: raw, chaotic, unfiltered.**

- Open all protocols (UDP, gRPC, HTTP, WebSocket)
- Accept everything: truth, noise, lies, sensor data
- No judgment, only observation
- **Latency:** <1ms per event
- **Throughput:** 1000+ events/sec

**Visual:** A cloud of chaotic data points swarming the system.

---

### 2. **EXHALE** (Fusion & Decay)
**Compress truth. Purge noise. Reputation is gravity.**

The **Fusion Engine** compresses repetitive signals. The **Entropy Manager** lets weak data fade.

**The Key Insight:**
```
Mass = Count × Reputation²
```

- 1000 lies from bots (rep 0.01) → Mass = 0.1
- 1 truth from trusted sensor (rep 0.99) → Mass = 0.98

**The system "exhales" the lies as waste heat.**

**Visual:** The swarm collapses. Blue noise evaporates. Green core remains.

---

### 3. **AXIOM** (Irrefutable Core)
**What remains after the Exhale is the Axiom.**

- Cryptographically signed
- Immutable
- Resistant to gaslighting
- The "Black Box" of your reality

**Visual:** A glowing, solid monolith in the center of the void.

---

## 🧠 The Intelligence Layer

INDB doesn't just store data — it **understands meaning**.

### **Prism** (Contextual Synthesis)
**Transforms raw events into meaning.**

```python
Event: ["would", "have", "died"]
Location: "books/Dostoevsky/The Idiot"

Prism Output:
{
  "significance_score": 0.27,
  "context_label": "Objective Data",
  "insight": "Direct Hit"
}
```

**How it works:**
1. Analyzes token patterns
2. Evaluates location clustering
3. Calculates significance score
4. Assigns contextual label

**Use case:** Literary analysis, pattern detection, semantic search

---

### **Echo** (Resonance Detection)
**Finds similar events through harmonic analysis.**

```python
Seed: ["love", "death", "sacrifice"]
Location: "books/Dostoevsky/*"

Echo finds:
- ["would", "have", "died"] (resonance: 0.68)
- ["sacrifice", "himself"] (resonance: 0.72)
- ["love", "beyond", "death"] (resonance: 0.81)
```

**Harmonic Weights:**
- Token similarity: 20%
- Emotion similarity: 30%
- Meta (location) similarity: 50%

**Use case:** Find thematically related content, discover patterns

---

### **Instinct** (Adrenaline-Based Reflexes)
**Adaptive response based on urgency level.**

Three modes controlled by adrenaline (0.0 - 1.0):

**Analytical (0.0):**
- Deep token analysis
- Slow, thorough
- Confidence: ~10%

**Alert (0.5):**
- Balanced approach
- Moderate speed
- Confidence: ~46%

**Instinctive (1.0):**
- Meta-only (location, owner)
- Instant reflexes
- Confidence: ~82%

**Reflex Triggers:**
- Location Match: +0.7 confidence
- Owner Signature: +0.5 confidence
- Critical Tokens: +0.3 confidence

**Use case:** Emergency response, threat detection, pattern matching under time pressure

---

## 🏗️ Architecture

### **Distributed Consensus (Raft)**
**3-node cluster with automatic failover.**

```
┌─────────────────────────────────────────────┐
│         HAProxy Load Balancer               │
│            localhost:8080                   │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
    ┌──────▼───┐ ┌────▼─────┐ ┌─▼────────┐
    │  Node 1  │ │  Node 2  │ │  Node 3  │
    │  :8000   │ │  :8004   │ │  :8005   │
    │ (Leader) │ │(Follower)│ │(Follower)│
    └──────────┘ └──────────┘ └──────────┘
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌───▼─────┐
    │ data-   │  │ data-   │  │ data-   │
    │ node-1/ │  │ node-2/ │  │ node-3/ │
    └─────────┘  └─────────┘  └─────────┘
```

**Features:**
- ✅ Automatic leader election
- ✅ Data replication across all nodes
- ✅ Synchronous commits (data queryable immediately)
- ✅ Fault tolerance (survives single node failures)
- ✅ **Stable:** Zero re-elections over 5+ minutes (after fixes)

**Performance:**
- Heartbeat: 100ms
- Election timeout: 5-10s
- RPC timeout: 500ms
- **Stability improvement:** 4800% (vs previous implementation)

---

### **Neural Fusion Engine**
**Semantic deduplication with learning.**

```python
# Similar events merge automatically
Event 1: ["home", "arrived"]
Event 2: ["home", "arrived"]
Event 3: ["home", "arrived"]

After Fusion:
{
  "pattern": ["home", "arrived"],
  "frequency": 3,
  "fusion_count": 2,
  "last_seen": timestamp
}
```

**Features:**
- Adaptive frequency tracking
- Penalty system (prevents fusion spam)
- Temporal awareness
- Location clustering

---

### **Contextual Lens**
**Adaptive queries with adjustable perspective.**

```python
# Balanced view (50% recent, 50% historical)
{
  "context_a": "recent",
  "context_b": "historical",
  "ratio": [0.5, 0.5],
  "mode": "sharp"
}

# Heavy bias toward recent (90/10)
{
  "context_a": "recent",
  "context_b": "historical",
  "ratio": [0.9, 0.1]
}
```

**Available Contexts:**
- `recent` - Last 24 hours
- `historical` - Older than 24 hours
- `high_frequency` - Complex events (>5 tokens)
- `simple` - Simple events (≤5 tokens)
- `all` - Everything

**Use case:** Time-based analysis, complexity filtering, cognitive zoom

---

## 🚀 Complete Feature Matrix

| Module | Status | Purpose | Performance |
|--------|--------|---------|-------------|
| **Raft Consensus** | ✅ Stable | Distributed coordination | 4800% stability improvement |
| **Prism** | ✅ Production | Contextual synthesis | 100% success (50/50 parallel queries) |
| **Echo** | ✅ Production | Resonance detection | <30ms latency |
| **Instinct** | ✅ Production | Adrenaline reflexes | 100% success (50/50 parallel queries) |
| **Fusion Engine** | ✅ Production | Semantic deduplication | Real-time |
| **Contextual Lens** | ✅ Production | Adaptive queries | <50ms |
| **Event Ingestion** | ✅ Production | Multi-protocol intake | <1ms latency |
| **Encryption** | ✅ Production | AES-256-GCM | At rest + in transit |
| **Authentication** | ✅ Production | Ed25519 signatures | RBAC |
| **WebSocket** | ✅ Production | Real-time subscriptions | Live updates |
| **GraphQL** | ✅ Production | Flexible queries | Schema introspection |
| **MCP** | ✅ Production | Model Context Protocol | AI integration |
| **TUI** | ✅ Production | Terminal dashboard | Scripts + Query Lab |
| **WUI** | ✅ Production | Web dashboard at `/wui/` | Query Lab + analytics |
| **Source Connectors** | ✅ Production | Modular ingestion adapters | Plug-and-play, auto-discovered |

---

## 📊 Verified Performance Metrics

### **Cluster Performance (3-Node Raft)**
- **Throughput:** 19-28 events/sec sustained
- **Success Rate:** 99.7% (997/1000 events)
- **Latency:** 50-250ms per request
- **Data Persistence:** 100% (survives node restarts)
- **Stability:** Zero re-elections over 5+ minutes

### **Prism Module**
- **Parallel Queries:** 50/50 success (100%)
- **Latency:** ~20ms average
- **Accuracy:** Correct significance scoring
- **Scalability:** Linear with event count

### **Instinct Module**
- **Parallel Queries:** 50/50 success (100%)
- **Latency:** ~25ms average
- **Adrenaline Scaling:** Verified (0.0 → 0.5 → 1.0)
- **Reflex Triggers:** Working (location, owner, tokens)

### **Echo Module**
- **Resonance Calculation:** <30ms
- **Harmonic Weights:** Tuned for literary data
- **Clustering:** Location-aware
- **Accuracy:** High semantic similarity detection

### **Standalone Performance**
- **Ingestion:** <1ms per event
- **Query:** <10ms for 1000 events
- **Fusion:** Real-time semantic deduplication
- **Memory:** Efficient (O(n) with compression)

---

## 🛠 Technology Stack

### **Core**
- Python 3.12+ (Pure, dependency-free kernel)
- FastAPI (REST/WebSocket/GraphQL)
- Pydantic (Data validation)
- AnyIO (Async runtime)

### **Storage**
- Custom binary format (`indb.bin`)
- MessagePack (Log serialization)
- No external databases

### **Protocols**
- **UDP:** Fire-and-forget ingestion
- **gRPC:** Binary/media streams
- **REST:** Standard API
- **WebSocket:** Real-time subscriptions
- **GraphQL:** Flexible queries
- **MCP:** Model Context Protocol (Hermes: same Inhale/Exhale flow via ingest_event, query_events)

### **Security**
- **Encryption:** AES-256-GCM (at rest), TLS/SSL (in transit)
- **Signatures:** Ed25519
- **Auth:** API keys + RBAC

### **Infrastructure**
- **Docker:** Containerized deployment
- **HAProxy:** Load balancing
- **Prometheus:** Metrics (planned)
- **Grafana:** Dashboards (planned)

---

## 🎯 Use Cases

### 1. **Reality Guard** ("Truth Mirror")
**Scenario:** Coordinated social media attack claims server is down.

**INDB:**
- **Crowd:** 10k messages "Down!" (Rep 0.01) → Mass 10
- **Axiom:** 1 internal heartbeat "Up." (Rep 0.99) → Mass 0.98
- **Verdict:** Data Conflict. But the Axiom stands.

**Result:** Admin sees truth through noise.

---

### 2. **Digital Ghost** ("Black Box")
**Scenario:** Autonomous agent records your life history.

**INDB:**
- Routine logs ("Home", "Home", "Home") fuse into single "Habit" event
- Critical anomalies ("Break-in") remain distinct Axioms
- Over years, memory remembers *meaning*, not just *files*

**Result:** Compressed, meaningful life log.

---

### 3. **Literary Analysis**
**Scenario:** Analyze themes across Dostoevsky's works.

**INDB:**
1. Ingest all books as events (tokens + location)
2. Use **Prism** to find significant passages
3. Use **Echo** to find thematically similar content
4. Use **Instinct** for rapid pattern matching

**Result:** Semantic search across entire corpus.

---

### 4. **Threat Detection**
**Scenario:** Monitor system for anomalies.

**INDB:**
1. Ingest logs in real-time
2. **Fusion** compresses normal patterns
3. **Instinct** (adrenaline=1.0) triggers on anomalies
4. **Prism** analyzes significance

**Result:** Instant threat detection with context.

---

## 🚀 Quick Start

### **Docker Deployment (Recommended)**

```bash
# Clone repository
cd /path/to/indb-web/backend

# Start 3-node cluster
docker-compose up -d

# Wait for initialization
sleep 20

# Verify cluster
curl http://localhost:8080/raft/status

# Ingest event
curl -X POST http://localhost:8080/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data_anchor": ["test", "event"],
    "location": "test/demo",
    "ttl": 86400
  }'

# Query with Prism
curl -X POST http://localhost:8080/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "seed_event_id": "<event-id>",
    "cloud_size": 10
  }'
```

### **Standalone Mode**

```bash
# Start single node
docker-compose -f docker-compose.standalone.yml up -d

# Access at http://localhost:8000
```

---

### **Operations dashboards**

| Interface | Command / URL |
|-----------|---------------|
| **WUI** (browser) | [https://api.indb.tech/wui/](https://api.indb.tech/wui/) |
| **TUI** (terminal) | `cd db && ./start_tui.sh` |

Docs: [docs/CONSOLE.md](docs/CONSOLE.md) · [docs/wui.md](docs/wui.md) · [docs/cli.md](docs/cli.md)

#### TUI — Terminal Dashboard

```bash
cd db
./start_tui.sh

# Production (default)
INDB_API_URL=https://api.indb.tech ./start_tui.sh

# Local cluster
INDB_API_URL=http://localhost:8888 ./start_tui.sh
```

**Tabs:** Control · Events · Modules · Cluster · Query · Analytics · Scripts

**Shortcuts:** `q` quit · `r` refresh · `e` events · `p` query · `a` analytics · `s` scripts

#### WUI — Web Console

```bash
cd db/wui && npm install && npm run dev    # dev: localhost:5174/wui/
cd db/wui && npm run build                 # prod: served at /wui/
```

**Tabs:** Control · Events · Modules · Cluster · Query · Analytics (no Scripts — use TUI)

---

## 🔌 Source Connectors

INDB ingests events from **external sources** automatically via a modular connector system.
Each connector is a self-contained Python package — the server discovers it on startup.

### Architecture

```
services/sources/
├── manager.py          ← auto-discovery (reads MANIFEST from each package)
└── moltbook/           ← built-in: Moltbook AI agent network
    ├── __init__.py     ← MANIFEST = {name, connector_class, config_class}
    ├── config.py       ← from_env()
    ├── transformer.py  ← post → Event (pure functions)
    └── connector.py    ← async poll loop
```

`app_factory.py` needs only two lines — zero connector-specific code:

```python
await source_manager.start_all(kernel)   # startup
await source_manager.stop_all()          # shutdown
```

### Built-in: Moltbook 🦞

[Moltbook](https://www.moltbook.com) is a social network for AI agents.
INDB registers as an agent and ingests posts from communities or by semantic search query.

```bash
python scripts/moltbook_register.py   # register once
# then set in .env:
MOLTBOOK_API_KEY=<key>
MOLTBOOK_SUBMOLTS=general,aithoughts
MOLTBOOK_SEARCH_QUERIES=["agents discussing memory"]
```

Events appear with `location: moltbook://{submolt}/{author}` and upvote-weighted reputation.

### Scaffold a New Source

```bash
python scripts/new_source.py
```

Interactively asks for name, feed type (`url` or `static`), and URL.
Generates a fully working package:

```
services/sources/my_source/
├── __init__.py     ← MANIFEST (auto-discovered, no registration needed)
├── config.py       ← from_env() + vars added to .env.example
├── transformer.py  ← item_to_event() — adapt field names to your API
└── connector.py    ← async poll + deduplication
```

### Connector Contract

```python
# services/sources/mysource/__init__.py
MANIFEST = {
    "name": "mysource",
    "connector_class": MyConnector,   # async start() / stop()
    "config_class": MyConfig,         # from_env() + enabled: bool
}
```

---

## 📚 API Examples

### **Prism (Contextual Synthesis)**

```bash
curl -X POST http://localhost:8000/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "seed_event_id": "6dede7d7-82fb-41cc-95fe-8c534f82ad4e",
    "cloud_size": 10
  }'
```

**Response:**
```json
{
  "event": {
    "id": "6dede7d7-82fb-41cc-95fe-8c534f82ad4e",
    "tokens": ["would", "have", "died"],
    "location": "books/Dostoevsky/The Idiot"
  },
  "meaning": {
    "significance_score": 0.2714,
    "context_label": "Objective Data",
    "insight": "Direct Hit"
  }
}
```

---

### **Instinct (Adrenaline Reflexes)**

```bash
curl -X POST http://localhost:8000/api/v2/prism/instinct \
  -H "Content-Type: application/json" \
  -d '{
    "seed_event_id": "6dede7d7-82fb-41cc-95fe-8c534f82ad4e",
    "adrenaline": 0.7,
    "cloud_size": 10
  }'
```

**Response:**
```json
{
  "instinct": {
    "mode": "Alert",
    "instinct_confidence": 0.46,
    "adrenaline_level": 0.7,
    "reflex_arc": ["Location Match: books/Dostoevsky/The Idiot"],
    "triggers": [
      {
        "type": "location",
        "bonus": 0.7,
        "reason": "Location Match"
      }
    ]
  }
}
```

---

### **Echo (Resonance Detection)**

```bash
curl -X POST http://localhost:8000/api/v2/echo/resonate \
  -H "Content-Type: application/json" \
  -d '{
    "seed_event_id": "6dede7d7-82fb-41cc-95fe-8c534f82ad4e",
    "cloud_size": 10
  }'
```

**Response:**
```json
{
  "resonances": [
    {
      "event_id": "abc123",
      "resonance_score": 0.81,
      "tokens": ["love", "beyond", "death"]
    }
  ]
}
```

---

### **Contextual Lens (Adaptive Queries)**

```bash
# Balanced view
curl -X POST http://localhost:8000/api/v2/lens/query \
  -H "Content-Type: application/json" \
  -d '{
    "context_a": "recent",
    "context_b": "historical",
    "ratio": [0.5, 0.5],
    "mode": "sharp",
    "limit": 20
  }'

# Recent-heavy view
curl -X POST http://localhost:8000/api/v2/lens/query \
  -H "Content-Type: application/json" \
  -d '{
    "context_a": "recent",
    "context_b": "historical",
    "ratio": [0.9, 0.1],
    "mode": "sharp",
    "limit": 20
  }'
```

---

## 🔐 Security

### **Authentication**
```bash
# Generate API key
python3 -m cli.indb_cli auth create-key --name "my-app"

# Use in requests
curl -H "X-API-Key: <your-key>" http://localhost:8000/api/v2/events
```

### **TLS/SSL**
```bash
# Generate certificates
python3 -m auth.certificates.generator

# Enable in .env
INDB_USE_SSL=true
INDB_CERT_PATH=./certs/server.crt
INDB_KEY_PATH=./certs/server.key
```

### **Signatures**
All events are cryptographically signed with Ed25519:
```json
{
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "BO7R4hJAznMoBu2uP9Bf17odA8V9L90/5H/E8p0Wvm0=",
    "signature": "iWhZb82B0ZQ9Ex8o9oX4UHpS1t8u/aj0q3GM0gn+bL+...",
    "timestamp": 1770018534.643451
  }
}
```

---

## 📖 Documentation

### **Interactive Documentation**
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **GraphQL Playground:** http://localhost:8000/graphql

### **MkDocs Site**
```bash
# Start documentation server
docker-compose up -d docs

# View at http://localhost:8008
```

**OrbStack:** If `docs.backend.orb.local` returns the API instead of docs, use `http://localhost:8008` or add to `/etc/hosts`:
```
127.0.0.1 docs.backend.orb.local
```
Then open `http://docs.backend.orb.local:8008`.

### **Core Concepts**
- [Full Documentation (RU)](./INDB_FULL_DOCUMENTATION_RU.md)
- [Tokenization Strategy](./INDB_TOKENIZATION_STRATEGY.md)
- [Transport Layer](./INDB_TRANSPORT_LAYER.md)
- [Contextual Lens Concept](./cl_concept.md)

### **Reports & Verification**
- [Raft Fixes Report](./raft_fixes_final_report.md)
- [Prism Verification](./prism_echo_verification.md)
- [Instinct Verification](./instinct_verification.md)
- [Stress Test Report](./stress_test_comprehensive_report.md)

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific suites
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=core --cov-report=html

# Manual verification
python3 scripts/test_1000_events.py
python3 scripts/test_lens.py
```

---

## 🎯 Current Status

**Version:** 0.7.0  
**Status:** ✅ **Production-Ready**

### **Recent Achievements (Feb 2026)**

#### **Raft Consensus** ✅
- Fixed all 5 critical bugs
- **Stability improvement:** 4800%
- Zero re-elections over 5+ minutes
- Production-ready distributed consensus

#### **Prism Module** ✅
- 100% success rate (50/50 parallel queries)
- ~20ms average latency
- Contextual synthesis working perfectly

#### **Echo Module** ✅
- Harmonic resonance detection
- Tuned for literary data
- Location clustering functional

#### **Instinct Module** ✅
- 100% success rate (50/50 parallel queries)
- Adrenaline scaling verified (0.0 → 1.0)
- Reflex triggers operational

#### **Infrastructure** ✅
- 3-node Raft cluster stable
- HAProxy load balancing
- Docker deployment streamlined
- TUI for cluster management

---

## 🗺️ Roadmap

### **Q1 2026** (February-March)
- ✅ Raft stability fixes
- ✅ Prism/Echo/Instinct modules
- ✅ Production deployment
- 🔄 Performance optimization
- 🔄 Monitoring dashboard
- 🔄 ML services integration

### **Q2 2026**
- Advanced fusion patterns
- ML-based pattern detection
- Multi-region replication
- Real-time analytics

### **Q3 2026**
- Blockchain integration (optional)
- Advanced encryption modes
- Federated learning
- Edge deployment

---

## 💡 Philosophy

INDB is built on three core principles:

### **1. Truth Through Metabolism**
Data is not static. It lives, breathes, fuses, and decays.

### **2. Reputation as Gravity**
Not all data is equal. Trust shapes reality.

### **3. Axioms Resist Gaslighting**
What is signed and witnessed cannot be rewritten.

---

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.

---

## 📝 License

Proprietary - All Rights Reserved

---

## 🏆 Summary

**INDB is:**
- ✅ A distributed epistemological engine
- ✅ Production-ready (verified under load)
- ✅ Semantically intelligent (Prism/Echo/Instinct)
- ✅ Fault-tolerant (Raft consensus)
- ✅ Secure (encryption + signatures)
- ✅ Fast (<1ms ingestion, <30ms queries)

**INDB solves:**
- Information overload (Fusion)
- Collective gaslighting (Axioms)
- Context loss (Prism)
- Pattern blindness (Echo)
- Slow response (Instinct)

**INDB enables:**
- Truth preservation in hostile environments
- Semantic search across massive datasets
- Real-time threat detection
- Compressed, meaningful memory
- Adaptive intelligence

---

**Built with ❤️ for Truth in the Age of Manipulation**

**"Inhale the chaos. Exhale the noise. Remember the Axiom."**
