# INDB Strategic Roadmap

> **Vision**: Autonomous, High-Performance Interpretative Database.
> **Current release**: **0.10.0 — Cold stays cold** (2026-11-03). Previous cuts in this tree: **0.9.1 — Direct recall**, **0.9.0 — Sleep & Wake**.

---

## 🟢 v0.3.0: The Cognitive Core (Completed)
**Focus**: Stability, Fusion, and Interpretation.
*Released: Q1 2026*

- [x] **Event Stream**: Immutable, time-ordered log.
- [x] **Event Fusion**: 35:1 Compression of repetitive signals.
- [x] **JIT Interpretation**: Context-aware retrieval ("Driver" vs "Analyst").
- [x] **Security**: Ed25519 Response Signing.
- [x] **Blind Store**: Basic Zero-Knowledge encrypted payloads (ChaCha20).
- [x] **Protocols**: HTTP/2, WebSocket, UDP.

---

## 🟢 v0.4.0: Distributed Autonomy (Completed)
**Focus**: Raft Consensus & Self-Healing.
*Released: Q1 2026*

- [x] **Raft Replication**: Robust Leader Election and Log Replication.
- [x] **Resilience**: Retry logic and partitioned networking handling.
- [x] **Persistence**: WAL (Write-Ahead Log) for atomic state preservation.
- [x] **State Machine**: Direct linkage between Raft Log and INDB Kernel Ingest.

---

## 🟢 v0.5.0: The Fortress (Completed)
**Focus**: Enterprise Security & Privacy.
*Released: Q1 2026*

- [x] **Immutable Audit**: Merkle Tree-backed audit logs for tamper evidence.
- [x] **RBAC**: Role-Based Access Control enforcing Least Privilege.
- [x] **Hardware Ops**: Deferred. Not part of 0.8.0.
- [x] **Defense-in-Depth**: Application-layer permission boundaries.

---

## 🟢 v0.6.0: Binary Stream (Completed)
**Focus**: Large Data Ingestion & Decoupling.
*Released: Q1 2026*

- [x] **gRPC Streaming**: `IngestStream` RPC for efficient chunked binary upload.
- [x] **Binary Payload**: Native support for `bytes` in Event model.
- [x] **Refactoring**: Decoupled `JITRenderer` from Core Storage for modular architecture.
- [x] **Async Bridge**: Standardized Async/Sync interop for Services.

---
 
## 🟢 v0.7.0: The Origin Layer (Completed)
**Focus**: Epistemology, Trust, and Source Verification.
*Released: Q1 2026*
 
- [x] **Source Entity**: First-class "Source" citizen with `SourceType` (Sensor, AI, Human, etc.).
- [x] **Source Registry**: Kernel-level registry for trusted agents and sensors.
- [x] **Provenance**: `source_id` linking for every Event to its origin.
- [x] **Weighted Consensus**: Using Source Reputation as gravity in Event Fusion.
- [x] **Signature Chain**: Cryptographic signing of events by Sources.
 
---

## 🟢 v0.8.0: Psycho & Grain
**Focus**: Weight ablation, identity tolerance, authenticated writes.
*Released: September 22, 2026 · image `indb:0.8.0` · git `e3e5882`*

- [x] **Psycho**: Factor-1 weight ablation on the resonance graph. Cost is `-log R + barrier`. The route is compared with the valuation and without it (`detour_cost`, `barrier_walked_into`, `identical_route`). `GET /api/v2/psycho/profiles`, `POST /api/v2/psycho/path`. See [PSYCHO.md](./PSYCHO.md).
- [x] **Grain**: Identity verification in the kernel, barcode to SynthID. Tiers: exact, redundant, resonant, statistical. `GET /api/v2/grain/tiers`, `POST /api/v2/grain/verify`. See [GRAIN.md](./GRAIN.md).
- [x] **Auth**: `AUTH_MODE`, RBAC roles, API keys. No anonymous writes.
- [x] **Product image**: API, cognitive modules, WUI, and TUI ship in `indb:0.8.0`. The landing site is a separate app.

### Already in this engine (not a separate version)

These are part of the engine. An earlier draft filed them under a 1.0.0 that was never cut.

- [x] AES-256-GCM at rest, TLS in transit, Ed25519 signatures
- [x] No external database: `indb.bin`, msgpack, in-process cache
- [x] Raft cluster, HAProxy compose, Fly deploy
- [x] WUI at `/wui/`, TUI, Prometheus `/metrics`
- [x] Optional embeddings (`sentence-transformers`); token overlap when the model is absent

---

## 🟢 v0.9.0: Sleep & Wake
**Focus**: Exhale keeps the event.
*Released: 2026-11-03*

- [x] Low-salience events leave hot memory for encrypted `cold.bin`.
- [x] Signed events and the recent tail stay hot.
- [x] A strong seed wakes a sleeper back into the resonance index.
- [x] `hot_events`, `cold_events`, `wake_count` on `/api/v2/health`.
- [x] See [MEMORY_LIFECYCLE.md](./MEMORY_LIFECYCLE.md).

---

## 🟢 v0.9.1: Direct recall
**Focus**: One id, no walk of the life.
*Released: 2026-11-03*

- [x] Hot memory keeps an id map.
- [x] `get_event`, `get_event_by_id`, and the Raft commit wait use that map.
- [x] A sleeping event is still returned by id from the cold tier.

---

## 🟢 v0.10.0: Cold stays cold (current)
**Focus**: The sleeper is the file.
*Released: 2026-11-03*

- [x] RAM keeps an id and its tokens, not the event body.
- [x] The body is read from `cold.bin` on wake, or when the id is asked for by name.
- [x] Scoring a seed uses the token trace, so noticing a sleeper does not load the life.

---

## 🔵 Next

The next version is not numbered. 1.0.0 does not exist.

---

## 📊 Progress

| Version | Status | Release |
|---------|--------|---------|
| v0.3.0 | ✅ Complete | Q1 2026 · cognitive core |
| v0.4.0 | ✅ Complete | Q1 2026 · Raft |
| v0.5.0 | ✅ Complete | Q1 2026 · audit and RBAC |
| v0.6.0 | ✅ Complete | Q1 2026 · gRPC binary stream |
| v0.7.0 | ✅ Complete | 2026-01-12 · origin layer |
| v0.8.0 | ✅ Complete | 2026-09-22 · Psycho & Grain |
| v0.9.0 | ✅ Complete | 2026-11-03 · Sleep & Wake |
| v0.9.1 | ✅ Complete | 2026-11-03 · Direct recall |
| v0.10.0 | ✅ **Current** | 2026-11-03 · Cold stays cold |

