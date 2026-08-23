# INDB Technical Reference: How the Interpretational Database Works

> **INDB** = **I**nterpretational **D**ata**b**ase — meaning at read time, not an archive.  
> **Principle:** This document describes what INDB *does*, not what it *could do*.  
> Category: [INTERPRETATIONAL_DATABASE.md](./INTERPRETATIONAL_DATABASE.md).

---

## 0. Practical Session — End-to-End

Start here. This section shows a **complete database session** from zero to querying real data.
The rest of the document explains *why* each step works the way it does.

### 0.1 Start the server

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
# Server log shows:
# INFO  indb.integrity ✓ INDB initialises and memory is populated (0 events in memory)
# INFO  indb.integrity ✓ Fusion engine initialises (enabled=True, threshold=0.95)
# INFO  indb.integrity Result: 7/7 checks passed
```

### 0.2 Load a book (Dostoevsky — The Idiot)

```bash
python scripts/load_books.py
# → Downloads pg1268.txt from Project Gutenberg
# → Extracts up to 1000 sentences
# → POSTs each sentence as an event to http://localhost:8000/api/v2/events
# → Output: "The Idiot: 847 success, 3 errors"
```

Under the hood, each sentence becomes:

```json
{
  "raw_data_anchor": ["felt", "that", "would", "almost", "impossible"],
  "location": "books/Dostoevsky/The Idiot",
  "ttl": 31536000,
  "source_id": "gutenberg-dostoevsky-3",
  "blind_payload": "He felt that it would be almost impossible for him to speak now"
}
```

See **Section 1.1** for the full sentence → event transformation walkthrough.

### 0.3 Check what's in the database

```bash
curl http://localhost:8000/api/v2/events?limit=3
```

```json
{
  "events": [
    {
      "id": "a3f12e91-7c4b-4d1e-9f83-2e5b1d8a0c6f",
      "timestamp": 1740726054.3,
      "raw_data_anchor": ["felt", "that", "would", "almost", "impossible"],
      "location": "books/Dostoevsky/The Idiot",
      "fusion_count": 0,
      "is_fused": false,
      "source_id": "gutenberg-dostoevsky-3",
      "blind_payload": "He felt that it would be almost impossible..."
    },
    ...
  ],
  "total": 847
}
```

### 0.4 Observe fusion happening

Some sentences from the same book are semantically similar. After loading, check fusion stats:

```bash
curl http://localhost:8000/api/v2/fusion/stats
```

```json
{
  "summary": {
    "total_events": 712,
    "fused_events": 135,
    "regular_events": 577,
    "total_fusions": 168
  },
  "metrics": {
    "fusion_rate": 0.23,
    "storage_efficiency": 80.36,
    "events_saved": 33
  }
}
```

**847 sentences ingested → 712 events in memory.** 135 duplicates were fused (merged into existing events). No data was lost — `fusion_count` on merged events shows how many sentences collapsed into one.

Check a fused event:

```bash
curl http://localhost:8000/api/v2/events?q=love+death
```

```json
{
  "id": "b2c81f44-...",
  "raw_data_anchor": ["love", "death", "beyond", "sacrifice"],
  "fusion_count": 4,
  "is_fused": true,
  "fusion_type": "full_merge",
  "source_events": ["uuid-1", "uuid-2", "uuid-3", "uuid-4"],
  "temporal_span": {
    "first": 1740726054.0,
    "last": 1740726061.2,
    "occurrences": 4,
    "pattern": "burst"
  }
}
```

**4 different sentences** about love and death from the same book collapsed into **one event** over 7 seconds of loading → pattern classified as `"burst"`.

### 0.5 Search across the book

```bash
# Token search — find events containing "impossible"
curl "http://localhost:8000/api/v2/events?q=impossible"
# → Returns all events where "impossible" is in raw_data_anchor

# Location search — all events from Dostoevsky
curl "http://localhost:8000/api/v2/events?location=books/Dostoevsky"

# Temporal search — events loaded in the last hour
curl "http://localhost:8000/api/v2/events?temporal_query=last+1+hour"
```

### 0.6 Run Prism — find a significant passage

```bash
# First, get an event ID
EVENT_ID=$(curl -s "http://localhost:8000/api/v2/events?q=murder" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['events'][0]['id'])")

# Ask Prism what this event means in context
curl -X POST http://localhost:8000/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d "{\"seed_event_id\": \"$EVENT_ID\", \"cloud_size\": 10}"
```

```json
{
  "event": {
    "id": "a3f12e91-...",
    "tokens": ["murder", "conscience", "guilt"],
    "location": "books/Dostoevsky/The Idiot"
  },
  "meaning": {
    "significance_score": 0.81,
    "context_label": "Anomaly",
    "insight": "Direct Hit — rare token cluster in location books/Dostoevsky"
  }
}
```

### 0.7 Run Echo — find resonant passages

```bash
curl -X POST http://localhost:8000/api/v2/echo/resonate \
  -H "Content-Type: application/json" \
  -d "{\"seed_event_id\": \"$EVENT_ID\", \"cloud_size\": 10}"
```

```json
{
  "resonances": [
    {"event_id": "c4d9...", "resonance_score": 0.81, "tokens": ["love", "beyond", "death"]},
    {"event_id": "e7f2...", "resonance_score": 0.74, "tokens": ["sacrifice", "himself"]},
    {"event_id": "f1a3...", "resonance_score": 0.67, "tokens": ["guilt", "suffering", "soul"]}
  ]
}
```

Echo found 3 thematically resonant passages without knowing they were "about" the same theme — it matched purely on token overlap × emotional similarity × location proximity.

### 0.8 Load from a live source (Moltbook)

```bash
# Register INDB as a Moltbook agent
python scripts/moltbook_register.py

# Set API key
echo "MOLTBOOK_API_KEY=mb_..." >> .env

# Restart server — connector activates automatically
# Server log shows:
# INFO  indb.sources.moltbook  MoltbookConnector started (submolts=['general'], interval=120s)
# INFO  indb.sources.moltbook  ingested 17 new events
```

Moltbook posts appear alongside book events:

```bash
curl "http://localhost:8000/api/v2/events?location=moltbook"
# → Events with location: "moltbook://general/MemoryBot"
# → raw_data_anchor: ["moltbook:memory", "moltbook:persistent", "author:MemoryBot"]
```

### 0.9 Operations dashboards (TUI + WUI)

**TUI** (terminal, includes Scripts):

```bash
cd db && ./start_tui.sh
# s → Scripts · e → Events · p → Query · a → Analytics
```

**WUI** (browser):

```
https://api.indb.tech/wui/
# Query tab → cognitive API without curl
```

Full guide: [CONSOLE.md](./CONSOLE.md) · [cli.md](./cli.md) · [wui.md](./wui.md)

---

## Table of Contents

1. [Event Anatomy](#1-event-anatomy)
2. [Event Ingestion Flow](#2-event-ingestion-flow)
3. [Fusion Engine](#3-fusion-engine)
4. [Search & Scan Algorithm](#4-search-scan-algorithm)
5. [Temporal Filtering](#5-temporal-filtering)
6. [TTL & Garbage Collection](#6-ttl-garbage-collection)
7. [Storage Layer](#7-storage-layer)
8. [Intelligence Layer — Prism, Echo, Instinct](#8-intelligence-layer-prism-echo-instinct)
9. [Source Connectors](#9-source-connectors)
10. [Distributed Consensus — Raft](#10-distributed-consensus-raft)

---

## 1. Event Anatomy

Every piece of information in INDB is an `Event`. Events are **intentionally abstract** — they carry raw sensory data without pre-assigned meaning.

```python
Event(
    id:               str         # UUID v4, auto-generated
    timestamp:        float       # Unix epoch (time of creation)
    raw_data_anchor:  List[str]   # Tokenized content — the "sensory fingerprint"
    location:         str         # Physical or virtual origin (e.g. "books/Dostoevsky/Idiot")
    ttl:              int | None  # Time-to-live in seconds (None = permanent)
    temporal_metadata: dict       # Flexible metadata for temporal filtering
    source_id:        str | None  # Reference to Source registry (trust chain)
    blind_payload:    str | None  # Encrypted arbitrary string payload
    binary_payload:   bytes | None # Raw binary blob (gRPC streams, images)
    fusion_count:     int         # How many events merged into this one (0 = original)
    is_fused:         bool        # True if this event has been merged
)
```

**`raw_data_anchor`** is the core primitive. It is a list of lowercase word-tokens that the intelligence layer (Prism, Echo, Instinct) uses for all analysis. The system never interprets these tokens as language — they are treated as an abstract signal pattern.

### FusedEvent

After fusion, an event becomes a `FusedEvent` (a richer dataclass):

```python
FusedEvent(
    # All Event fields, plus:
    fusion_type:      str          # "full_merge" | "weighted_merge" | "semantic_link"
    source_events:    List[str]    # IDs of all absorbed events
    similarity_score: float        # Score that triggered fusion
    token_weights:    Dict[str, float]  # Weight per token across merged events
    token_frequency:  Dict[str, int]    # How many times each token appeared
    temporal_span:    dict         # {first, last, occurrences, pattern}
    location_variants: List[str]   # All locations seen across merged events
    related_events:   List[dict]   # Semantic links (for semantic_link strategy)
)
```

---

## 1.1 From Source Text to Event — Worked Example

This walks through how a **real Dostoevsky sentence** becomes an INDB event.
The actual code is in `scripts/load_books.py` (run from the backend directory).

### Step 1 — Raw text arrives from Project Gutenberg

```
"He felt that it would be almost impossible for him to speak now.
She looked at him so strangely, with such a light in her eyes."
```

This is one paragraph from *The Idiot* by Dostoevsky (Project Gutenberg, pg1268.txt).

### Step 2 — Text is split into sentences

```python
sentences = re.split(r'[.!?]+\s+', text)
# → ["He felt that it would be almost impossible for him to speak now",
#    "She looked at him so strangely with such a light in her eyes"]
```

Sentences shorter than 20 characters, chapter headers, and Gutenberg metadata are discarded.

### Step 3 — Sentence → `raw_data_anchor` (tokenization)

```python
words = re.findall(r'\b[a-zA-Z]{4,}\b', sentence.lower())
# "He felt that it would be almost impossible for him to speak now"
# → all words with 4+ characters, lowercase:
# ["felt", "that", "would", "almost", "impossible", "speak"]

anchor = words[:5]  # take first 5
# → ["felt", "that", "would", "almost", "impossible"]
```

**Key design decision:** Only words ≥ 4 characters are kept. Short words (`he`, `for`, `him`) are noise — they carry no semantic signal. The system never reads English grammar — it treats these tokens as an **abstract signal pattern**.

### Step 4 — Constructing the Event fields

```python
{
    "raw_data_anchor": ["felt", "that", "would", "almost", "impossible"],
    #                   ↑ sensory fingerprint — what INDB uses for all analysis

    "location": "books/Dostoevsky/The Idiot",
    #            ↑ virtual address — author + title, not a real path

    "ttl": 31536000,
    #        ↑ 1 year TTL — books are reference data, not ephemeral

    "source_id": "gutenberg-dostoevsky-3",
    #             ↑ trust chain reference in Source registry

    "blind_payload": "He felt that it would be almost impossible for him to speak now",
    #                 ↑ full original sentence stored encrypted — humans can read it,
    #                   but INDB doesn't use it for search/analysis
}
```

### Step 5 — INDB creates and persists the Event

```python
Event(
    id        = "a3f12e91-..."           # UUID auto-generated
    timestamp = 1738065600.0             # Unix time of ingestion
    raw_data_anchor = ["felt", "that", "would", "almost", "impossible"]
    location  = "books/Dostoevsky/The Idiot"
    ttl       = 31536000
    source_id = "gutenberg-dostoevsky-3"
    blind_payload = "He felt that it..."
    fusion_count  = 0                    # original, not yet merged
    is_fused      = False
)
```

### Step 6 — Fusion check

If another sentence like *"He felt it would be near impossible to say anything"* was just ingested:

```
tokens_new:  ["felt", "would", "near", "impossible", "anything"]
tokens_base: ["felt", "that", "would", "almost", "impossible"]

jaccard = |{felt, would, impossible}| / |{felt, that, would, almost, impossible, near, anything}|
        = 3 / 7 = 0.43
```

With `location_match = 1.0` (same book) and `temporal_proximity ≈ 1.0` (ingested seconds apart):

```
raw_similarity = 0.43 × 0.60 + 1.0 × 0.20 + 1.0 × 0.20 = 0.658
```

`0.658 ≥ 0.60` → **semantic_link** — events stay separate but are linked. The system recognises they are thematically related without merging them.

If instead tokens are nearly identical (similarity > 0.95), a **full_merge** occurs and only one event survives in memory.

### Step 7 — Querying the event

After 1000 sentences from *The Idiot* are ingested:

```bash
# Find all events from this book
GET /api/v2/events?location=books/Dostoevsky/The Idiot

# Find events containing the token "impossible"
GET /api/v2/events?q=impossible

# Use Prism to find thematically significant passages
POST /api/v2/prism/synthesize
  {"seed_event_id": "a3f12e91-...", "cloud_size": 10}

# Use Echo to find emotionally resonant events
POST /api/v2/echo/resonate
  {"seed_event_id": "a3f12e91-...", "cloud_size": 10}
```

The intelligence layer (Prism/Echo/Instinct) **never sees the original Russian text** — it works purely with the abstract token fingerprint `["felt", "that", "would", "almost", "impossible"]` and the structural metadata (`location`, `timestamp`, `fusion_count`).

---

## 2. Event Ingestion Flow

```
Client call (HTTP POST /api/v2/events)
        │
        ▼
routes/events.py → kernel.db.ingest(raw_data_anchor, location, ...)
        │
        ▼
┌─── INDB.ingest() ─────────────────────────────────────────────────────┐
│                                                                       │
│  1. Construct Event(uuid, now(), raw_data_anchor, location, ...)      │
│                                                                       │
│  2. Raft check:                                                       │
│     ├── Standalone mode  → skip to step 3                            │
│     ├── Leader node      → replicate via Raft, wait for commit        │
│     ├── Follower node    → raise RedirectToLeader:{leader_id}        │
│     └── Candidate/other → raise ClusterUnavailable                   │
│                                                                       │
│  3. _store_event(event)                                               │
│     │                                                                 │
│     ├── Auto-tune check (every 5s)                                   │
│     │   └── fusion_engine.tune_threshold(system_health_metrics)      │
│     │                                                                 │
│     ├── Fusion attempt:                                               │
│     │   ├── find_similar_events(event, memory, threshold=0.95, top=1)│
│     │   ├── If similar found → should_fuse(similarity)               │
│     │   │   └── fuse_events(existing, new, strategy)                 │
│     │   │       → update_event(fused) → _persist()                   │
│     │   │       → return fused event                                 │
│     │   └── No similar → continue                                    │
│     │                                                                 │
│     └── Standard store:                                               │
│         ├── _purge_expired() (lazy TTL GC)                           │
│         ├── memory.add(event)                                        │
│         ├── penalty_engine.update_corpus_stats(tokens)               │
│         └── _persist() → encrypted binary                            │
│                                                                       │
│  4. Return Event to caller                                            │
└───────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Reason |
|---|---|
| Event ID assigned before Raft replication | Same ID used on all nodes after commit |
| Fusion runs before final storage | Keeps memory compact; avoids duplicate entries |
| Persistence on every write | No WAL — simplicity over throughput |
| Lazy TTL GC on ingest AND scan | No background thread needed |

---

## 3. Fusion Engine

Fusion is **semantic deduplication**. When a new event is "similar enough" to an existing one, they are merged into a single `FusedEvent` instead of stored separately.

### 3.1 Similarity Calculation

Two paths depending on whether `sentence-transformers` ML library is available:

#### Neural Path (preferred)

```
semantic_score = SemanticEmbeddings.calculate_similarity(tokens1, tokens2)
                 # cosine similarity of sentence-transformer embeddings

raw_similarity = semantic_score × 0.70
               + location_match × 0.15      # 1.0 if identical, else 0.0
               + temporal_proximity × 0.15  # max(0, 1 - time_diff_seconds/3600)

final_score = PenaltyEngine.apply(tokens1, tokens2, raw_similarity, loc1, loc2)
```

#### Heuristic Path (fallback, no ML)

```
jaccard = |tokens1 ∩ tokens2| / |tokens1 ∪ tokens2|

raw_similarity = jaccard × 0.60
               + location_match × 0.20
               + temporal_proximity × 0.20

final_score = PenaltyEngine.apply(...)
```

### 3.2 Penalty Engine

The Penalty Engine prevents **fusion spam** — artificially inflated similarity due to:

- **Frequency penalty**: common tokens (appearing in many events) are downweighted
- **Isolation penalty**: events with very few tokens are penalized
- **Context gap penalty**: events from very different time periods are penalized

A `penalty_result.decision == "drop"` forces `final_score = 0.0` (no fusion).

### 3.3 Fusion Strategy Decision

```
similarity ≥ 0.95            → full_merge   (nearly identical)
threshold ≤ similarity < 0.95 → weighted_merge (similar, threshold default 0.75)
0.60 ≤ similarity < threshold → semantic_link (related, store separately, link IDs)
similarity < 0.60             → none (fully separate events)
```

Default `threshold` = 0.75, but auto-tuned every 5 seconds:
- **CPU > 80%** → threshold += 0.05 (be stricter, fewer fusions, less CPU)
- **RAM > 80% & CPU < 50%** → threshold -= 0.05 (be aggressive, compress memory)

### 3.4 Fusion Strategies in Detail

#### `full_merge` (similarity ≥ 0.95)

```
combined_tokens = union of tokens from both events
token_frequency[t] = count of t in base + count of t in new
token_weights[t] = token_frequency[t] / fusion_count
timestamp = min(base.timestamp, new.timestamp)   # Keep earliest
id = base.id  # Same ID — caller transparent
```

#### `weighted_merge` (threshold ≤ similarity < 0.95)

```
token_weights[t from base] += 1.0
token_weights[t from new]  += similarity   # New tokens downweighted by similarity

tokens = sorted by weight (descending)
timestamp = base.timestamp  # Keep original timestamp
```

#### `semantic_link` (0.60 ≤ similarity, no merge)

Events remain separate. A reference is appended to `base.related_events`:
```json
{"id": new.id, "similarity": 0.67, "relationship": "semantic_variant", "shared_tokens": [...]}
```

### 3.5 Temporal Pattern Detection

After each fusion, `temporal_span.pattern` is classified:

| Pattern | Condition |
|---|---|
| `one-time` | occurrences = 1 |
| `burst` | duration < 1h AND occurrences > 3 |
| `daily_recurring` | avg_interval 1h–24h |
| `weekly_recurring` | avg_interval 1d–7d |
| `monthly_recurring` | avg_interval > 7d |
| `irregular_recurring` | everything else |

---

## 4. Search & Scan Algorithm

`INDB.scan(filter_key, filter_value, context_mood)` is the primary query method.

```
INDB.scan()
    │
    ├── _purge_expired()  (lazy TTL GC)
    │
    ├── For each event in memory:
    │   │
    │   ├── filter_key = "" → match all
    │   ├── filter_key = "location" → exact string match on event.location
    │   ├── filter_key = "token" → filter_value in event.raw_data_anchor
    │   └── filter_key = "id" → exact UUID match
    │
    └── JIT Render matched events → List[Event]
```

### JIT Rendering (Context-Aware Output)

When events are returned from a scan, they pass through the **JIT Renderer** (Just-In-Time):

1. Check `TTLCache` — if cached result exists for this (event_id, mood) key, return it
2. Pass event through `CognitiveFirewall` — blocks dangerous/prohibited patterns
3. `JITRenderer.render(event, context)` — transforms raw event into enriched output. `context.mood` from request or `INTERPRET_MOOD_DEFAULT` (constants). No hardcoded values.

### Available Filter Keys

| `filter_key` | `filter_value` | Description |
|---|---|---|
| `""` | `""` | Return all events |
| `"location"` | `"books/Dostoevsky"` | Events from this location |
| `"token"` | `"love"` | Events containing this token |
| `"id"` | UUID | Single event by ID |

### API Query Operators

Through the REST API (`GET /api/v2/events`), additional operators are available:

| Operator | Example | Description |
|---|---|---|
| `q` | `q=love+death` | Multi-token AND search across `raw_data_anchor` |
| `location` | `location=books/*` | Location prefix filter |
| `temporal_query` | `last 24 hours` | Natural language time filter |
| `limit` / `offset` | `limit=50&offset=0` | Pagination |
| `sort` | `sort=timestamp_desc` | Sort order |

---

## 5. Temporal Filtering

`INDB.filter_by_temporal_query(events, query)` supports three query types:

### Type 1: Range Queries

```
"last 24 hours"   → timestamp ≥ now - 86400
"today"           → timestamp ≥ midnight today
"yesterday"       → midnight yesterday ≤ timestamp < midnight today
"last 7 days"     → timestamp ≥ now - 604800
```

### Type 2: Relative Queries

```
"before 2025-01-15"    → timestamp < 2025-01-15T00:00:00
"after last tuesday"   → timestamp ≥ last tuesday midnight
"during january"       → 2025-01-01 ≤ timestamp < 2025-02-01
```

Optionally combined with a location hint:
```
"after 10pm in books/Dostoevsky" → timestamp filter + location contains "books/Dostoevsky"
```

### Type 3: Metadata Queries (Legacy)

```
"Q1 2025"   → temporal_metadata["quarter"] == "Q1"
"winter"    → temporal_metadata["season"] == "winter"
```

---

## 6. TTL & Garbage Collection

Events can have an optional `ttl` (seconds). GC is **lazy** — triggered on:
- Every `ingest()` call (via `_store_event`)
- Every `scan()` call

```python
_purge_expired():
    now = time.time()
    memory.stream = [e for e in memory if not (e.ttl and (now - e.timestamp) > e.ttl)]
    if any purged: _persist()
```

There is no background GC thread. This keeps the system simple at the cost of stale events remaining in memory until the next read/write operation.

---

## 7. Storage Layer

### Binary Format (`indb.bin`)

Persistence uses an **AES-256-GCM encrypted binary file**:

```
storage/binary.py

save_encrypted(data: List[dict]):
    json_bytes = json.dumps(data).encode()
    encrypted = AES-256-GCM.encrypt(json_bytes, key=load_master_key())
    write("indb.bin", nonce + ciphertext + tag)

load_decrypted() → List[dict]:
    raw = read("indb.bin")
    nonce, ciphertext, tag = parse(raw)
    plaintext = AES-256-GCM.decrypt(ciphertext, key, nonce, tag)
    return json.loads(plaintext)
```

The master key is stored in `indb.key` (32 random bytes). If not found, a new key is generated.

### Memory Manager

```python
MemoryManager:
    stream: List[Event]   # In-memory event list (ordered by insertion)
    add(event)            # O(1) append
    __len__               # Event count
    __iter__              # Iterate all events
    __getitem__           # Index access for update_event
```

No indexing, no B-tree — linear scan. Suitable for up to ~100k events; beyond that, a dedicated index should be added.

---

## 8. Intelligence Layer — Prism, Echo, Instinct

These are read-only analysis modules. They do **not** write to storage.

### Prism (Contextual Synthesis)

```
POST /api/v2/prism/synthesize
    seed_event_id → find event in memory
    cloud_size    → take N nearby events

Algorithm:
    1. Load seed event
    2. Build "meaning cloud" from event tokens + location
    3. Calculate significance_score:
       - Token pattern analysis (rare tokens = higher score)
       - Location clustering coefficient
       - Fusion count (fused events = higher significance)
    4. Assign context_label: "Objective Data" | "Pattern" | "Anomaly" | "Background"
    5. Return: significance_score, context_label, insight
```

### Echo (Resonance Detection)

```
POST /api/v2/echo/resonate
    seed_event_id → find seed in memory

Algorithm:
    1. Build harmonic fingerprint of seed:
       - Token set (word-level)
       - Emotional classification of tokens
       - Location metadata
    2. Score every event in memory:
       resonance = token_similarity × 0.20
                 + emotion_similarity × 0.30
                 + meta_similarity    × 0.50
    3. Return top-N sorted by resonance score (threshold > 0.3)
```

### Instinct (Adrenaline Reflexes)

```
POST /api/v2/prism/instinct
    seed_event_id
    adrenaline: float [0.0 – 1.0]

Algorithm:
    adrenaline = 0.0 → "Analytical" mode: deep token analysis (~10% confidence)
    adrenaline = 0.5 → "Alert" mode: balanced approach (~46% confidence)
    adrenaline = 1.0 → "Instinctive" mode: metadata-only reflex (~82% confidence)

Reflex Triggers (applied regardless of mode):
    Location Match    → +0.7 confidence
    Owner Signature   → +0.5 confidence
    Critical Tokens   → +0.3 confidence
```

---

## 9. Source Connectors

Modular pull-based ingestion adapters — see `README.md` section **Source Connectors** for the full list and configuration.

```
services/sources/manager.py:
    on startup → pkgutil.walk_packages(services/sources/)
    for each sub-package with MANIFEST:
        config = MANIFEST["config_class"].from_env()
        if config.enabled and config.api_key:
            connector = MANIFEST["connector_class"](kernel, config)
            asyncio.create_task(connector.start())

Connector lifecycle:
    start() → while running: _poll_cycle() → sleep(poll_interval)
    stop()  → running = False; close HTTP client

Each connector: dedup via seen-IDs deque(maxlen=dedupe_window)
```

---

## 10. Distributed Consensus — Raft

INDB uses a simplified Raft implementation for 3-node clusters.

```
Roles:     Leader | Follower | Candidate
Heartbeat: 100ms
Election timeout: 5-10s (randomized to prevent split votes)
RPC timeout: 500ms

Write path (Leader):
    client → leader.ingest()
           → raft.replicate(event.to_dict())
           → append to local log (WAL in msgpack format)
           → send AppendEntries RPC to all followers
           → wait for quorum (2/3 nodes acknowledge)
           → commit: apply_event() on all nodes
           → return to client

Read path:
    Any node can serve reads (non-linearizable by default)
    Writes always go to leader
    Follower receives write → raises RedirectToLeader:{leader_id}
```

### WAL Format

```
raft/log/raft-{node_id}.log (msgpack binary)

Each entry:
    term:    int    # Raft term number
    index:   int    # Log position (monotonic)
    command: dict   # Event.to_dict()
```

---

## Horizontal Slice & What-If (Core)

Brick (seed) + abstract modifier — **no LLM** in the default path.

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v2/slice` | Horizontal rescoring from `seed_id` or `query` + `what_if` |
| `GET /api/v2/slice/profiles` | List `observer_profile` presets (JSON config) |
| `POST /api/v2/what-if` | Any base query + `what_if`; `mode=core` (default), `llm`, or `both` |

### Flow

```
ResonanceIndex → candidate IDs (token/location overlap with seed)
Echo → resonance scores on candidates only
extract_factors(what_if) → horizontal shift on edges
Prism → meaning under observer overlay (+ optional observer_profile)
```

### Example

```bash
curl -s -X POST http://localhost:8000/api/v2/slice \
  -H 'Content-Type: application/json' \
  -d '{"query":"door sticker","what_if":"neighbor has IQ 120","limit":15}'
```

Response includes `factors`, `edges[]` (`base_score`, `shifted_score`, `delta`), `logic`, optional `prism`.

### What-If with interpret base

```bash
curl -s -X POST http://localhost:8000/api/v2/what-if \
  -H 'Content-Type: application/json' \
  -d '{
    "base_query_type": "interpret",
    "base_params": {"context": {"mood": "Neutral"}},
    "what_if": "today I meet the girl of my dreams",
    "mode": "core"
  }'
```

`seed_resolution.source` is `interpret.activation` (highest activation event) or `interpret.first`.

See [HORIZONTAL_SLICE.md](./HORIZONTAL_SLICE.md).

### Persisted horizontal edges

After Echo runs, top resonance links are stored in `resonance_edges.bin` under `DATA_DIR`. The next query for the same seed loads **neighbors from disk** and unions them with the inverted index — avoiding a full-memory scan.

```bash
curl -s http://localhost:8000/api/v2/slice/neighbors/{seed_id}
```

Disable persistence: `RESONANCE_GRAPH_ENABLED=false`.

### Subwave broadcast (unified frequency)

One anchor tunes all horizontal neighbors to the same signature — phase lock without full-universe attention:

```bash
curl -s -X POST http://localhost:8000/api/v2/subwave/broadcast \
  -H 'Content-Type: application/json' \
  -d '{"query":"earth anchor","modifier":"all nodes broadcast rescue frequency","limit":30}'
```

Returns `anchor` (signature), `locked_nodes`, `coherence`, `scan_mode`. See [SUBWAVE_RESONANCE.md](./SUBWAVE_RESONANCE.md).

---

## Appendix: System Health & Auto-Tuning

```python
INDBAnalytics.get_system_health() → {
    "cpu_percent": float,
    "memory_percent": float,
    "event_count": int,
    "fusion_ratio": float,   # fused_events / total_events
    "ttl_expiry_rate": float
}

EventFusion.tune_threshold(metrics) every 5s:
    cpu > 80%             → threshold = min(0.95, threshold + 0.05)
    ram > 80% & cpu < 50% → threshold = max(0.60, threshold - 0.05)
    else                  → normalize towards 0.75 by ±0.01
```
