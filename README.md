# INDB: Interpretational Database
## Inhale. Exhale. Axiom.

> **"When everyone lies, INDB remembers what you saw."**

**INDB** = **I**nterpretational **D**ata**b**ase — memory, not archive. Meaning at query time, not frozen at ingest.

See [docs/INTERPRETATIONAL_DATABASE.md](docs/INTERPRETATIONAL_DATABASE.md).

**Source:** https://github.com/kaaboeld/indb  
**Packed file:** [latest](https://indb.tech/releases/indb-latest.tar.gz) is 0.11.1. The numbered archive stays at [indb-0.11.1.tar.gz](https://indb.tech/releases/indb-0.11.1.tar.gz).

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
- **Measured 3-node Raft run:** 19–28 events/sec sustained, 50–250ms per request

**Visual:** A cloud of chaotic data points swarming the system.

---

### 2. **EXHALE** (Fusion & Decay)
**Compress truth. Purge noise. Reputation is gravity.**

The **Fusion Engine** compresses repetitive signals. The **Entropy Manager** lets weak data fade.

**What the engine computes** is salience, not a squared reputation:

```
salience = log(1 + fusion_count) × source_weight × recency
```

A fusion count of 0 is salience 0. That event sleeps unless it is signed or still in the recent tail. Reference: [docs/MEMORY_LIFECYCLE.md](docs/MEMORY_LIFECYCLE.md).

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

**Analytical** below 0.3, **Alert** below 0.7, **Instinctive** from 0.7.

The bonus is multiplied by adrenaline, not a fixed add:

- Owner match: `0.8 × adrenaline` (only above 0.3)
- Location match: `0.7 × adrenaline`
- Shared critical token: `0.5 × adrenaline`

Confidence is `reflex_bonus × 0.6 + adrenaline × 0.3`, plus `0.1` when the location matches, capped at 1. It is not a fixed 10% / 46% / 82% per mode.

---

### **Psycho** (Pathfinding Under Weight Ablation)
**Measures what the observer's values were doing to a route.**

Echo radiates in every direction. Psycho picks one and pays for it:

```
cost(a → b) = -log R(a, b) + barrier(b)
```

Minimising a sum of `-log R` maximises the product of resonances, so the cheapest
path is the most plausible chain — not merely the one with fewest hops. `barrier`
is what the observer pays to pass through a node, taken from the negative entries
of their `token_weights`.

The route alone is not the answer. Psycho runs the search twice — valuation
honoured, valuation removed — and prices both on the same scale:

```python
POST /api/v2/psycho/path
{
  "from": "<event-id or free text>",
  "to":   "<event-id or free text>",
  "profile": "psychopath",      # Factor-1 analogue: affect flat, distress ignored
  "compare_to": "neutral",      # the baseline
  "token_weights": {"harm": -6.0}
}

→ detour_cost: 3.98            # what the shortcut costs once the valuation is priced back in
  barrier_walked_into: 6.0     # barrier the shortcut enters that the baseline avoided
  identical_route: false       # true would mean the weights were decoration
```

Zeroing every node's weight would be meaningless — every route would tie. Psycho
ablates one *class* of weight (the emotional harmonic and the observer's valuation)
and keeps the structural term, so a route still exists and is still ranked.

**Use case:** Testing whether a weight in your ranking is load-bearing; tracing how
a chain of events connects when a value judgement is taken out of the scoring.

Full reference: [docs/PSYCHO.md](docs/PSYCHO.md)

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
- ✅ **Stable on that run:** zero re-elections over 5+ minutes

**Timing used in that setup:**
- Heartbeat: 100ms
- Election timeout: 5-10s
- RPC timeout: 500ms

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

| Module | Status | Purpose | Note |
|--------|--------|---------|------|
| **Raft Consensus** | In the engine | Distributed coordination | Optional. Measured run is below. The public API is one node |
| **Prism** | In the engine | Contextual synthesis | |
| **Echo** | In the engine | Resonance detection | |
| **Instinct** | In the engine | Adrenaline reflexes | |
| **Psycho** | In the engine | Pathfinding under weight ablation | `POST /api/v2/psycho/path` |
| **Grain** | In the engine | Identity across exact → statistical | `POST /api/v2/grain/verify` |
| **Fusion Engine** | In the engine | Semantic deduplication | Scores hot events that share a token |
| **Contextual Lens** | In the engine | Adaptive queries | |
| **Event Ingestion** | In the engine | Multi-protocol intake | Cluster rate is the measured figure below |
| **Encryption** | In the engine | AES-256-GCM at rest | TLS when `INDB_USE_SSL` is on |
| **Authentication** | In the engine | API keys, RBAC | Anonymous writes are rejected. An Ed25519 signature is optional |
| **WebSocket** | In the engine | Subscriptions | |
| **GraphQL** | In the engine | Queries | `/graphql` |
| **MCP** | In the engine | Model Context Protocol | Endpoint is in the tree. No separate benchmark |
| **TUI** | In the image | Terminal dashboard | |
| **WUI** | In the image | Web dashboard at `/wui/` | Public on the demo node |
| **Source Connectors** | In the engine | Ingestion adapters | |

---

## 📊 Verified Performance Metrics

### **Cluster Performance (3-Node Raft)**
- **Throughput:** 19-28 events/sec sustained
- **Success Rate:** 99.7% (997/1000 events)
- **Latency:** 50-250ms per request
- **Data Persistence:** 100% (survives node restarts)
- **Stability:** Zero re-elections over 5+ minutes

Module-level timings that used to sit here (<1ms ingest, <10ms for 1000 events, 50/50 at ~20ms) are not a published measurement. The figure this file stands behind is the cluster block above.

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
- **Encryption:** AES-256-GCM at rest. TLS when `INDB_USE_SSL` is on
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

**Result:** The repeated line fuses. The odd one stays.

---

## 🚀 Quick Start

The packed image is the release. Load and run it from [docs/SELFHOST.md](docs/SELFHOST.md). A write needs `X-API-Key`. Reads stay open.

### **Docker Compose in this tree**

The compose file in the clone is the 3-node Raft cluster, not the public node.

```bash
git clone https://github.com/kaaboeld/indb.git
cd indb

# Start 3-node cluster
docker-compose up -d

# Wait for initialization
sleep 20

# Verify cluster
curl http://localhost:8080/raft/status

# Ingest event. Anonymous writes are rejected.
curl -X POST http://localhost:8080/api/v2/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-key>" \
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
| **TUI** (terminal) | `./start_tui.sh` from the clone |

Docs: [docs/CONSOLE.md](docs/CONSOLE.md) · [docs/wui.md](docs/wui.md) · [docs/cli.md](docs/cli.md)

#### TUI — Terminal Dashboard

```bash
./start_tui.sh

# Public API
INDB_API_URL=https://api.indb.tech ./start_tui.sh

# Local cluster
INDB_API_URL=http://localhost:8888 ./start_tui.sh
```

**Tabs:** Control · Events · Modules · Cluster · Query · Analytics · Scripts

**Shortcuts:** `q` quit · `r` refresh · `e` events · `p` query · `a` analytics · `s` scripts

#### WUI — Web Console

```bash
cd wui && npm install && npm run dev    # dev: localhost:5174/wui/
cd wui && npm run build                   # the image serves the built console at /wui/
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

**Shape of the reply.** The numbers below are the formula for a location match at adrenaline 0.7: bonus `0.7 × 0.7 = 0.49`, confidence `0.49 × 0.6 + 0.7 × 0.3 + 0.1 = 0.604`. Mode at 0.7 is Instinctive.

```json
{
  "instinct": {
    "mode": "Instinctive",
    "instinct_confidence": 0.604,
    "adrenaline_level": 0.7,
    "reflex_arc": ["Location Match: books/Dostoevsky/The Idiot"],
    "triggers": [
      {
        "type": "location",
        "bonus": 0.49,
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
An event may carry an Ed25519 signature. A signed event does not sleep:
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

### **Docs**
Documentation is not in the database image: https://docs.indb.tech

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

**Version:** 0.11.1 — Inhale looks sideways (2026-11-03)  
**Status:** Public source at https://github.com/kaaboeld/indb  
**Packed file:** `indb:0.11.1`, also published as [latest](https://indb.tech/releases/indb-latest.tar.gz)

### **0.11.1 — Inhale looks sideways**

- Heuristic fusion scores hot events that share a token
- The embedding path still sees the whole hot tier
- A fused body is replaced by id

### **0.11.0 — Edges fade**

- An edge that touches a weak sleeper is marked stale and kept
- That edge no longer wakes and no longer answers Echo. Token overlap still can
- A sleeper that still carries mass holds the edge past the seven-day clock

### **0.10.0 — Cold stays cold**

- A sleeper's body stays in encrypted `cold.bin`
- RAM keeps the id and the tokens, enough to notice a strong seed
- The body is read when that seed wakes it, or when the id is asked for by name

### **0.9.1 — Direct recall**

- Hot memory keeps an id map
- `get_event`, `get_event_by_id`, and the Raft commit wait use it
- A sleeping event is still found by id in `cold.bin`

### **0.9.0 — Sleep & Wake**

- Low-salience events exhale into encrypted `cold.bin`
- Signed events and the recent tail stay hot
- A strong seed wakes a sleeper and re-indexes it
- `/api/v2/health` reports `hot_events`, `cold_events`, `wake_count`
- Reference: [docs/MEMORY_LIFECYCLE.md](docs/MEMORY_LIFECYCLE.md)

### **0.8.0 — Psycho & Grain**

#### **Psycho** ✅
- Path cost is `-log R(a, b) + barrier(b)`: the cheapest route is the most plausible chain
- Runs the search twice — valuation honoured, valuation removed — and prices both on the same scale
- `detour_cost`, `barrier_walked_into`, `identical_route` say whether a weight was load-bearing
- Profiles include `psychopath` (affect flat) and `empath`; baseline is `neutral`
- `GET /api/v2/psycho/profiles` · `POST /api/v2/psycho/path`
- Reference: [docs/PSYCHO.md](docs/PSYCHO.md)

#### **Grain** ✅
- One identity check across four noise tiers: exact → redundant → resonant → statistical
- Barcode (Ed25519) through SynthID-style n-gram fingerprint, in the kernel
- `GET /api/v2/grain/tiers` · `POST /api/v2/grain/verify`
- Reference: [docs/GRAIN.md](docs/GRAIN.md)

#### **Auth** ✅
- `AUTH_MODE`, RBAC roles, API keys
- Anonymous writes are rejected

#### **Product image** ✅
- The image ships API, cognitive modules, WUI, and TUI
- The landing site (`site/`) is a separate app

### **Already in the engine**

Prism, Echo, Instinct, Fusion, Lens, Paradox, signed memory, Raft, AES-256-GCM at rest, and the WUI/TUI consoles. 1.0.0 has not been cut.

---

## 🗺️ Roadmap

Current cut is **0.11.1**. 1.0.0 is not cut.

| Version | What landed |
|---------|-------------|
| 0.11.1 | Fusion scores shared tokens |
| 0.11.0 | Weak edges fade and stay |
| 0.10.0 | Cold body stays on disk |
| 0.9.1 | Direct recall by id |
| 0.9.0 | Sleep & Wake |
| 0.8.0 | Psycho, Grain, authenticated writes, product image |

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
- An interpretational database. Meaning is read at query time
- Public source, packed image 0.11.1
- Prism, Echo, Instinct, Psycho, Grain, Fusion, Lens
- Optional Raft. The public API is one node
- AES-256-GCM at rest, optional TLS, optional Ed25519

**The measured cluster** (3-node Raft) holds 19–28 events/sec and 50–250ms per request. That is the number. 1.0.0 is not cut.

---

**Built with ❤️ for Truth in the Age of Manipulation**

**"Inhale the chaos. Exhale the noise. Remember the Axiom."**
