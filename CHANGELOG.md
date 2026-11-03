# Changelog

Current release: **0.10.0**. Source of truth for the running version is `VERSION` in `core/constants.py`. Packed notes live in `releases/manifest.json`.

1.0.0 has not been cut. Work stays local until this tree is packed.

---

## 0.10.0 — Cold stays cold

**Date:** 2026-11-03

A sleeper is the encrypted file, not a second copy of the life in RAM. The process keeps the id and the tokens, enough to notice a strong seed. The body is read from `cold.bin` when that seed wakes it, or when the id is asked for by name.

---

## 0.9.1 — Direct recall

**Date:** 2026-11-03

Hot memory keeps an id map. `get_event`, `get_event_by_id`, and the Raft commit wait resolve one event without walking the stream. A sleeping event is still found by id in the cold tier.

---

## 0.9.0 — Sleep & Wake

**Date:** 2026-11-03

- A full hot tier exhales low-salience events into encrypted `cold.bin`. They are not deleted.
- Signed events stay hot. The recent tail stays hot.
- A seed whose token overlap or stored graph edge reaches the wake threshold pulls the sleeper back, re-indexes it, and reinforces `fusion_count`.
- `/api/v2/health` reports `hot_events`, `cold_events`, and `wake_count` (wakes since process start).
- Reference: [docs/MEMORY_LIFECYCLE.md](docs/MEMORY_LIFECYCLE.md)

---

## 0.8.0 — Psycho & Grain

**Date:** 2026-09-22  
**Image:** `indb:0.8.0`  
**Git:** `e3e5882`

### Psycho

Pathfinding under weight ablation. Echo radiates; Psycho picks one route and prices what the observer's values did to it.

```
cost(a → b) = -log R(a, b) + barrier(b)
```

Minimising the sum of `-log R` maximises the product of resonances, so the cheapest path is the most plausible chain. `barrier` comes from the negative entries of the caller's `token_weights`.

The search runs twice — valuation honoured, valuation removed — and both routes are priced on the same scale.

- `GET /api/v2/psycho/profiles`
- `POST /api/v2/psycho/path` with `from`, `to`, `profile`, `compare_to`, `token_weights`
- Headline fields: `detour_cost`, `barrier_walked_into`, `identical_route`
- Profiles include `psychopath` (affect flat, distress ignored) and `empath`; the baseline is `neutral`
- Reference: [docs/PSYCHO.md](docs/PSYCHO.md)

### Grain

Identity verification in the kernel, from barcode-exact to a SynthID-style fingerprint.

| Tier | Analog | Tolerance |
|------|--------|-----------|
| exact | EAN-13 / Ed25519 | ~0–5% |
| redundant | QR-style N-of-M | ~30% |
| resonant | Echo × source reputation | ~30–50% |
| statistical | n-gram fingerprint | p-value |

- `GET /api/v2/grain/tiers`
- `POST /api/v2/grain/verify`
- Reference: [docs/GRAIN.md](docs/GRAIN.md)

### Auth

- `AUTH_MODE`, RBAC roles, API keys
- Anonymous writes are rejected

### Product image

`indb:0.8.0` ships the API, cognitive modules, WUI, and TUI. The landing site (`site/`) is a separate application.

---

## 0.7.0 — Origin layer

**Date:** 2026-01-12  
**Image:** `indb:0.7.0`

- Source entity (`Sensor`, `AI`, `Human`, …) and a kernel source registry
- Reputation-weighted fusion
- Ed25519 event signing and provenance (`source_id`)
- Prism perception paradox: `perception_gap`, `alternative_readings`, observer `token_weights`
- Signed memory recovery by public `key_id`

---

## Earlier milestones

These shipped before the packed catalog. They are in the 0.8.0 engine. They are not later version numbers.

### 0.6.0 — Binary stream

- gRPC `IngestStream`
- `binary_payload` on events
- JIT renderer decoupled from storage

### 0.5.0 — Fortress

- Audit log
- RBAC
- AES-256-GCM at rest, TLS in transit
- No external database: `indb.bin` and msgpack

### 0.4.0 — Raft

- Leader election and log replication
- Writes only on the leader

### 0.3.0 — Cognitive core

- Event stream
- Fusion
- JIT interpretation
- HTTP, WebSocket, UDP

---

## What was not a release

An earlier draft of this file called the current release 1.0.0 and assigned AES, caching, and a 100k events/sec benchmark to that number. 1.0.0 was never cut. Cluster throughput measured for the 3-node Raft setup remains 19–28 events/sec. Optional `sentence-transformers` embeddings fall back to token overlap when the model is not installed.
