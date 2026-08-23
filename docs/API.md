# INDB API Reference (v0.7.0)

**Base URL** (Docker compose): `http://localhost:8000/api/v2`  
**Note:** INDB is an **interpretational database** (memory, not archive). Engine: Inhale → Exhale → Axiom. Events are anchors; meaning comes from interpret, prism, echo, subwave.

**Breathing metaphor:**
- **Inhale:** `POST /events` — accept raw reality
- **Exhale:** `POST /interpret` — context-aware scan, JIT rendering
- **Resonate:** `GET /search` — semantic lookup
- **Axiom:** signed, immutable memory

All defaults and thresholds live in `core/constants.py` — no hardcoded values. Hermes MCP uses the same backend; REST and MCP share the same flow.

---

## Core Concepts

All INDB API responses may be **cryptographically signed** by the server (response sealing).
- **Signature Algorithm**: Ed25519
- **Server key**: `SIGNING_PRIVATE_KEY` env — never sent to clients
- **Verification**: Clients verify the response `signature` using the server public key (`GET /recovery/identity`)

Events may optionally carry **writer signatures** at ingest (`signature` block with `public_key` + proof).
- **Writer private key**: stays on the client — never in recovery API
- **Identity**: `key_id` = SHA-256(public key) — see [SIGNED_MEMORY_RECOVERY.md](./SIGNED_MEMORY_RECOVERY.md)

Events are the primary primitive. Everything you store is an `Event`:
- It can **age** (`ttl`, fusion).
- It can **change weight** (`fusion_count`, reputation).
- It can **hide meaning** (`blind_payload`).

---

## 1. Core API (recommended entrypoints)

Most integrations only need these **4 endpoints**.

### 1.1 Create Event
`POST /events`

Single event:
```json
{
  "raw_data_anchor": ["fast", "red", "loud"],
  "location": "Highway 101",
  "ttl": 3600,
  "blind_payload": null
}
```

**Signed event** (optional — client signs locally; requires explicit `id`):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1770018534.0,
  "raw_data_anchor": ["rain", "memory"],
  "location": "demo/signed",
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "BASE64_PUBLIC_KEY",
    "signature": "BASE64_SIGNATURE",
    "key_id": "64_CHAR_HEX_FINGERPRINT"
  }
}
```

Private signing keys are **never** sent. See [SIGNED_MEMORY_RECOVERY.md](./SIGNED_MEMORY_RECOVERY.md) for full patterns.

**Black Box Contract** — if `blind_payload` is set, both `location` and `timestamp` become mandatory at the protocol level. An empty or missing location will be rejected:

```json
{
  "raw_data_anchor": ["private", "moment"],
  "location": "city/amsterdam/canals",
  "timestamp": 1741219285.0,
  "blind_payload": "encrypted-content-here"
}
```

> *You may hide what is inside. You may not hide that you were here.*

The engine has no decryption key for `blind_payload`. This is architectural — not policy.

Batch (alternative form using the same endpoint is supported via `/events/batch` in Advanced section):
```json
{
  "events": [
    { "raw_data_anchor": ["A"], "location": "Loc1" },
    { "raw_data_anchor": ["B"], "location": "Loc2" }
  ]
}
```

### 1.2 List Events
`GET /events`

Minimal usage:
- `limit` (int, default 100)

Advanced filters are documented below, but most clients start with:
- `GET /events?limit=50`

### 1.3 Cognitive Synthesis (Prism) — paradox-aware
`POST /api/v2/prism/synthesize`

The engine inhales the query, exhales meaning. Returns not just a result — returns its confidence in that result and any competing readings.

```json
{
  "query": "amsterdam bicycle evening",
  "identity_key": "user_123",
  "radius": 0.3,
  "limit": 20,
  "observer_context": {
    "token_weights": {"silence": 2.0, "rain": 1.5},
    "vocabulary": {"Personal": ["felt", "almost"], "Distant": ["reported", "observed"]},
    "harmonic_weights": {"emotion": 0.8, "token": 0.5, "meta": 0.3}
  }
}
```

`query` accepts **event_id OR text**. If the id is not found, the engine finds the closest matching event by text and uses it as the resonance seed.

`observer_context` is **optional**. Without it, system defaults apply. With it, meaning becomes observer-dependent — the same event returns different readings for different observers.

Response includes the **Perception Paradox**:

| Field | Type | Meaning |
|---|---|---|
| `meaning` | MeaningVector | Primary reading (winner) |
| `alternative_readings` | List[MeaningVector] | Competing readings — not discarded |
| `perception_gap` | float 0–1 | 0.0 = clear · 1.0 = maximum ambiguity |
| `is_paradoxical` | bool | True when gap ≥ 0.25: the system cannot decide |
| `has_unread_essence` | bool | True when blind_payload present: reality may differ |

When `is_paradoxical=True`: *what you see may not be what it is.*

### 1.4 Exhale — Contextual Interpretation
`POST /interpret`

**Concept:** The engine *exhales* — scans memory through a given context (mood, goal). JIT Renderer derives meaning from events at runtime. No hardcoded values; defaults from `core/constants.py`.

```json
{
  "context": { "mood": "Neutral", "goal": "Safety" },
  "temporal_query": "last 24 hours",
  "firewall_mode": "block",
  "limit": 10
}
```

Returns events filtered and interpreted by context. For Triple-Half blending (recent/historical) — use `POST /lens/query`. For paradox-aware synthesis — use `/prism/synthesize`.

### 1.5 Semantic Search (Resonate / Echo)
`GET /search`

Query parameters:
- `q` (str): Search query, e.g. `"blue ocean"`
- `fuzzy` (bool): Enable partial / fuzzy matching
- `limit` (int): Max results

Use this when you want **textual / semantic lookup**, not full contextual interpretation.

---

## 2. Advanced / Internal REST Endpoints

The following endpoints are fully supported but are usually not needed in the first integration.

### 2.1 Events (advanced)

#### Create Event (Batch, explicit)
`POST /events/batch`

Explicit batch ingestion:
```json
{
  "events": [
    { "raw_data_anchor": ["A"], "location": "Loc1" },
    { "raw_data_anchor": ["B"], "location": "Loc2" }
  ]
}
```

#### List Events with filters
`GET /events`

Additional query parameters:
- `offset` (int): Pagination
- `filter_key` (str): Metadata key
- `filter_value` (str): Value

---

### 2.2 Fusion & System Introspection

#### Fusion Stats
`GET /fusion/stats`

Returns compression ratios and fusion efficiency metrics (how well the memory is "breathing").

#### System Protocols
`GET /system/protocols`

Returns status of UDP, gRPC, and WebSocket interfaces.

---

### 2.3 Deduction (Sherlock Holmes) — chain inference
`POST /api/v2/deduction/deduce`

Given evidence (events), infers chains and conclusions.

**Request:**
```json
{
  "seed_event_ids": ["evt-1", "evt-2"],
  "query": "birthday cheese",
  "radius": 0.35,
  "limit": 15
}
```

- `seed_event_ids`: Direct event IDs (optional). If provided, `query` is ignored.
- `query`: Text search to resolve to seeds (e.g. "beach 2024", "birthday cheese").
- `radius`: Echo resonance radius for expanding evidence cloud.
- `limit`: Max events in chain.

**Response:**
```json
{
  "chain": [
    {"event_id": "evt-1", "reason": "Seed evidence", "step_type": "seed", "confidence": 0.9},
    {"event_id": "evt-2", "reason": "Temporal: after evt-1", "step_type": "temporal", "confidence": 0.85}
  ],
  "conclusion": "Evidence suggests a sequence across 5 events at beach. Thematic: cheese, birthday, sun.",
  "confidence": 0.82,
  "evidence_count": 5,
  "reasoning": "Seed → Temporal → Spatial → Token"
}
```

---

### 2.4 Grain (Identity Tolerance)
Prefix: `/api/v2/grain`

Verification across the noise-tolerance spectrum. See [GRAIN.md](./GRAIN.md).

| Endpoint | Purpose |
|----------|---------|
| `GET /grain/tiers` | Catalog: exact → redundant → resonant → statistical |
| `POST /grain/verify` | Verify candidate identity against reference event(s) |

**Verify request:**
```json
{
  "reference_event_id": "<seed-uuid>",
  "candidate": {
    "raw_data_anchor": ["partial", "rewrite", "summer"],
    "location": "books/test"
  },
  "tier": "auto",
  "tolerance": 0.5
}
```

**Response fields:** `tier_used`, `match_score`, `verdict`, `false_accept_risk`, `false_reject_risk`, `p_value` (statistical tier), `insufficient_signal`.

---

### 2.5 Signed Memory Recovery

Prefix: `/api/v2/recovery`

Recovery verifies Ed25519 proofs by **public** `key_id`. Private keys, seeds, and shared secrets are rejected.

| Endpoint | Purpose |
|----------|---------|
| `GET /recovery/identity` | Server response-signing public key + `key_id` |
| `GET /recovery/resolve-key?public_key=` | Derive `key_id` from public key |
| `GET /recovery/key/{key_id}` | Events signed by identity hash |
| `GET /recovery/verify/{event_id}` | Verify single event signature |
| `POST /recovery/restore` | Verify export; optional import |

**Restore request:**

```json
{
  "key_id": "64_CHAR_HEX_FINGERPRINT",
  "verify_only": false,
  "events": [
    {
      "id": "uuid",
      "timestamp": 1770018600.0,
      "raw_data_anchor": ["restore", "test"],
      "location": "recovery/lab",
      "signature": {
        "algorithm": "Ed25519",
        "public_key": "BASE64_PUBLIC_KEY",
        "signature": "BASE64_SIGNATURE",
        "key_id": "64_CHAR_HEX_FINGERPRINT"
      }
    }
  ]
}
```

Implementation examples for each pattern: [SIGNED_MEMORY_RECOVERY.md](./SIGNED_MEMORY_RECOVERY.md).

---

### 2.6 Paradox (type) — contract

> **Status:** API contract (v0.8). Prism read-time paradox (`is_paradoxical`) is live — see §1.3.

Paradox is **not** an Event flag. Separate store, empty anchor until observation.

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v2/paradox` | Create superposed paradox (context only) |
| `GET /api/v2/paradox/{id}?collapse=true` | Observe / collapse |

**Generation modes:** `resonance_weighted` · `pool` · `fusion`  
**Collapse modes:** `sample_once` (→ signed Event) · `sample_on_read` (ephemeral)

```json
{
  "location": "books/Dostoevsky",
  "paradox_context": {
    "themes": ["love", "death"],
    "token_pool": ["love", "death", "memory"]
  },
  "paradox_generation": {
    "mode": "pool",
    "collapse": "sample_once"
  }
}
```

Per-pattern curl and Python examples: [PARADOX.md](./PARADOX.md).

---

### 2.7 Webhooks

Register a webhook to receive outbound notifications (e.g., new Axioms).

`POST /webhooks`
```json
{ "url": "https://callback.com/hook" }
```

---

## 3. gRPC API (binary ingest)

**Port**: `50051`

### Stream Ingestion
`RPC IngestStream` (Client Stream)

Efficient chunked upload of binary data (images, audio, large blobs).

**Request stream**:
1. **Metadata Frame**:
   ```json
   { "metadata": { "raw_data_anchor": ["image"], "location": "Lab", "ttl": 60 } }
   ```
2. **Data Frames**:
   ```json
   { "chunk_data": "<binary_bytes>" }
   ```

**Response**:
```json
{ "id": "uuid", "status": "success", "message": "Ingested 10240 bytes" }
```

