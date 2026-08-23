# Your API Shouldn't Expose Tables. It Should Expose Memory Acts.

> *"When everyone lies, INDB remembers what you saw."*

We didn't set out to build a faster PostgreSQL.

We set out to build something awkward to categorize: an **Interpretational Database** — memory where **meaning is read, not filed**. Not an archive that swells. A system that inhales chaos, exhales noise, and keeps a signed core.

Live at [indb.tech](https://indb.tech). Docs at [docs.indb.tech](https://docs.indb.tech). This is what we actually shipped in v0.7.

---

## The category mistake

Most data systems assume:

1. You **define** meaning at write time (schema, types, migrations)
2. You **store** rows
3. You **query** with SQL-shaped verbs

Human memory doesn't work like that.

You **observe** first. Meaning arrives later — context-dependent, sometimes contradictory. Repetition compresses into habit. Some things you store but never consciously access.

INDB models that pipeline explicitly:

| Phase | Metaphor | What happens |
|-------|----------|--------------|
| **Inhale** | Ingest | Accept raw events — tokens + location, no judgment |
| **Exhale** | Fusion | Compress repetition; reputation filters noise |
| **Axiom** | Sign | What survives can be Ed25519-signed, tamper-evident |

That's not marketing poetry. It's how the API is organized.

---

## Seven fields. No schema. On purpose.

INDB has **no migrations**. No column types in the SQL sense. Everything is an `Event` — a universal container:

| Field | Type | Role |
|-------|------|------|
| `id` | string | UUID v4 — auto-generated, immutable |
| `timestamp` | float | Unix epoch — time of observation |
| `raw_data_anchor` | string[] | Tokenized signal — abstract fingerprint |
| `location` | string \| OSM | Spatial anchor — path or geo object |
| `ttl` | int \| null | Decay in seconds (null = permanent) |
| `fusion_count` | int | How many observations merged |
| `source_id` | string \| null | Trust chain / reputation |
| `blind_payload` | string \| null | Zero-knowledge encrypted blob |
| `binary_payload` | bytes \| null | Raw binary — images, streams, gRPC |

If you need forty columns, you're probably modeling an archive — not memory.

**Inhale** an event:

```bash
curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data_anchor": ["server", "heartbeat", "ok"],
    "location": "infra/edge/eu-west",
    "ttl": 86400
  }'
```

You're not inserting a row. You're teaching the engine a new fragment of reality.

---

## Semantic types, not SQL columns

Under those seven fields sits a **semantic type system** — types describe *what kind of thought* you're storing, not how many bytes it occupies:

| Type | Role |
|------|------|
| **`location`** | The Anchor — spatial grounding via OSM |
| **`blind`** | The Secret — client-encrypted, server-opaque |
| **`binary`** | The Payload — raw media, sensor streams, files |
| **`struct`** | The Graph — nested, recursively validated objects |
| **`bigint`** | The Scale — nanosecond precision, crypto integers > 2⁵³ |
| **`string`** | The Narrative — text with optional regex/length constraints |
| **`number`** | The Value — quantifiable floats and ints |
| **`null`** | The Void — explicit absence |

On ingest, INDB **infers** intent: a dict with `lat`/`lon` becomes `location`; raw bytes become `binary`; nested dicts become `struct`. You don't declare `ALTER TABLE` — you send data, the kernel classifies it.

The distinction that matters for privacy:

- **`binary`** — server knows it's binary, validates size and MIME, but does not interpret content
- **`blind`** — server does not know what's inside; ChaCha20-encrypted client-side, stored as Base64 opaque blob. Cognitive modules skip it entirely

Full spec: [docs.indb.tech/TYPING/](https://docs.indb.tech/TYPING/)

---

## Space is index

The `location` field is not a tag. It is a **spatial anchor** — the Cognitive Engine uses it for proximity, clustering, and relevance.

**Format A — virtual namespace** (logical paths, agents, books, services):

```json
{ "location": "books/Dostoevsky/The_Idiot" }
```

**Format B — OSM geo object** (real-world grounding):

```json
{
  "location": {
    "lat": 55.7558,
    "lon": 37.6173,
    "osm_id": "node/1234567"
  }
}
```

Coordinates are validated (`lat` −90…90, `lon` −180…180). `osm_id` accepts all three OpenStreetMap entity types — `node/`, `way/`, `relation/`. A café, a street, a district — all valid anchors.

Geo also lives in tokens. Prefix `osm:` in `raw_data_anchor` (e.g. `osm:London, UK`) ties the signal to a place without duplicating the location field.

What the engine does with it:

- **Echo** harmonic analysis weights **meta-location at 50%** — events anchored to the same OSM object resonate stronger
- **Fusion** penalises multiple `osm:` tokens in one event — prevents over-clustering on geographic coincidence alone
- **Haversine distance** between coordinate pairs drives proximity scoring across the cluster

Same event, two ways to ground it — namespace for fiction and agents, OSM for sensors and field work:

```bash
curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data_anchor": ["sensor", "temperature", "22.4", "osm:Jerusalem, Israel"],
    "location": {"lat": 31.7683, "lon": 35.2137, "osm_id": "node/26131744"}
  }'
```

---

## Cognitive verbs, not CRUD

Our public API reads like **memory acts**, not database operations:

| Verb | Endpoint | Question it answers |
|------|----------|---------------------|
| **Inhale** | `POST /api/v2/events` | Remember this moment |
| **Lens** | `POST /api/v2/interpret` | How do *you* see it? (context, mood) |
| **Echo** | search / resonate | Who else feels like this? |
| **Subwave** | `POST /api/v2/subwave/broadcast` | Broadcast one frequency — horizontal resonance |
| **Slice** | `POST /api/v2/slice` | Shift the reading (what-if + observer profile) |
| **Paradox** | `POST /api/v2/paradox` | Hold superposition *before* content exists |
| **Recovery** | `GET /api/v2/recovery/key/{key_id}` | Restore by public identity — never private key |

Six protocols on the wire: HTTP, GraphQL, WebSocket, gRPC, UDP, MCP. **Zero** Redis, Postgres, or Mongo in the kernel — we meant that literally.

---

## Layer 2: what encryption alone can't give you

AES-256-GCM and TLS are Layer 1. Every vendor has them.

INDB's Layer 2 is structural:

### Signed memory

Clients sign events locally. The server stores `public_key + signature` — **private keys never traverse the API**. Recovery uses `key_id = SHA-256(public_key)`, a public fingerprint. API responses are also sealed with Ed25519.

### `blind_payload` — the engine is a witness without eyes

You encrypt client-side. INDB stores an opaque blob. Replicates it across Raft nodes. Returns it on request.

It **never reads it**. No decryption key on server. Prism, Echo, Instinct work only on `raw_data_anchor` tokens — analytics without access to secrets.

The **Black Box Contract** is enforced at protocol level:

> You may hide what is inside.  
> You may not hide that you were here.

When `blind_payload` is set, `timestamp` and `location` are **mandatory** — not a form validation quirk, a condition of existence. If authorities ask, the system has one answer:

*"Something was here. This location. This time."*  
What it was — architecturally unknown.

We call this **impossible to exfiltrate** — not because we promise nicely, but because there's nothing to hand over.

*(Client-side caveat: architecture breaks if your SDK logs keys into analytics. We document that boundary explicitly.)*

---

## Two kinds of paradox (same word, different phase)

This confused us internally until we named it:

**Paradox (type)** — *before* observation.  
`POST /api/v2/paradox` with empty `raw_data_anchor`. Context only. Content collapses when someone observes — `sample_once` births a signed Event; `sample_on_read` stays ephemeral.

**Prism paradox** — *after* observation.  
Fixed event, competing readings. Prism returns `meaning`, `alternative_readings`, `perception_gap`, `is_paradoxical`. The engine **surfaces** contradiction instead of picking a winner.

Same word. Different layer of memory. Both are signals, not errors.

Try Prism with observer context — meaning is relational, not baked in:

```bash
curl -X POST https://api.indb.tech/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "query": "felt almost impossible",
    "observer_context": {
      "token_weights": {"silence": 2.0},
      "vocabulary": {"Subjective": ["felt", "almost"]},
      "harmonic_weights": {"emotion": 0.8}
    }
  }'
```

Same tokens. Different observer. Different reading. System doesn't decide who's "right."

---

## Grain: when barcode logic meets human memory

Strict Ed25519 is **barcode-tier** verification: ~0% noise tolerance. Correct for axioms. Wrong for memory — partial quotes, export damage, surface change.

So we shipped **Grain** — one kernel module, four tiers on the noise-tolerance axis:

| Tier | Real-world analog | INDB mechanism |
|------|-------------------|----------------|
| **exact** | EAN-13 barcode | Ed25519 / `key_id` |
| **redundant** | QR Reed–Solomon | N-of-M signed cluster (~30% damage) |
| **resonant** | Handwriting biometrics | Echo × source reputation, FAR/FRR knob |
| **statistical** | SynthID-style watermark | Token n-gram p-value |

One endpoint. `tier: auto` picks from evidence. Responses expose uncertainty — `false_accept_risk`, `insufficient_signal` when the text is too short for statistical detection (honest floor, not fake confidence).

```bash
curl https://api.indb.tech/api/v2/grain/tiers
```

Full spec: [docs.indb.tech/GRAIN/](https://docs.indb.tech/GRAIN/)

External world: four silos (barcode SDK, QR lib, biometric FAR/FRR, generative watermark). INDB: one spectrum inside the same pipeline that ingests, fuses, and signs.

---

## Memory compresses (35:1 verified)

Repetition isn't data — it's pattern.

Three `"home arrived"` events fuse into one with `fusion_count: 3`. Routine compresses. An `"alarm at 3am"` stays distinct. Fusion ratio in testing: **35:1**.

Reputation is gravity:

```
Mass = Count × Reputation²
```

A thousand bot messages (rep 0.01) weigh less than one sensor heartbeat (rep 0.99). The system exhales crowd noise as waste heat.

---

## Pluggable, not monolithic

Hermes connector: LLM agent memory via MCP (`ingest_event`, `query_events`).  
Moltbook connector: AI agent social feed → events at `moltbook://{submolt}/{author}`.

Disable a connector — core still breathes. Modularity, not singleton.

Ops: browser **WUI** at [api.indb.tech/wui/](https://api.indb.tech/wui/) or terminal **TUI** (`./start_tui.sh`).

---

## Numbers we publish (v0.7 production)

- **<1ms** ingestion (standalone)
- **99.7%** success under load (997/1000 events)
- **~20ms** Prism · **<30ms** Echo · **~25ms** Instinct
- **0** external databases in the stack
- **6** wire protocols including MCP for agents

Raft 3-node cluster for self-hosters who want consensus — Docker Compose in docs.

---

## Who is this for?

Not everyone. INDB is for systems where:

- You need **signed, tamper-evident** history
- You must **prove presence** without exposing **content**
- Contradictions should be **surfaced**, not silently resolved
- Identity verification must tolerate **noise** without abandoning **axioms**
- AI agents need **persistent interpretational memory**, not another vector table bolted on

Legal evidence. Healthcare audit trails. Journalism source protection. IoT with UDP ingest and fusion. Agent memory (Hermes/MCP).

---

## Try it in five minutes

```bash
# Health
curl https://api.indb.tech/health

# Inhale
curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor":["devto","reader","hello"],"location":"blog/intro"}'

# Grain spectrum
curl https://api.indb.tech/api/v2/grain/tiers

# Swagger
open https://api.indb.tech/docs
```

---

## Links

- **Site:** [indb.tech](https://indb.tech)
- **Documentation:** [docs.indb.tech](https://docs.indb.tech)
- **Grain:** [docs.indb.tech/GRAIN/](https://docs.indb.tech/GRAIN/)
- **API:** [api.indb.tech/docs](https://api.indb.tech/docs)
- **Contact:** [indb.tech/#contact](https://indb.tech/#contact)

---

We're building for truth in the age of manipulation. If your stack treats data as memory — not filing cabinets — we'd love to hear what you'd stress-test first.

*Inhale the chaos. Exhale the noise. Remember the Axiom.*
