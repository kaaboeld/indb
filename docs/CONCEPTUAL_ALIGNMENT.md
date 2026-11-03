# INDB: Conceptual Alignment

> Alignment of code, documentation, and philosophy. Inhale — Exhale — Axiom.

**Date:** 2026-09-22  
**Version:** 0.11.1

---

## 1. Core: Inhale → Exhale → Axiom

| Phase | Meaning | Endpoint / Protocol | Pre-Hermes | With Hermes |
|-------|---------|---------------------|------------|-------------|
| **Inhale** | Accept raw reality | `POST /events`, UDP, gRPC, WebSocket | ✅ | ✅ + MCP `ingest_event` |
| **Exhale** | Compress noise, exhale meaning | Fusion + `POST /interpret` | ✅ | ✅ (same backend) |
| **Axiom** | Signed, immutable memory | All responses Ed25519 | ✅ | ✅ |
| **Resonate** | Semantic search | `GET /search`, Echo, Prism | ✅ | ✅ + MCP `query_events` |

**Conclusion:** Hermes is another Inhale source (MCP) and Exhale consumer (query). Same INDB, same flow. Conceptually nothing changes.

---

## 1.1. Hermes is a Module — Pluggable

Hermes is a **module** like any other (moltbook, etc.). It is **pluggable** — the system must work when Hermes is connected or disconnected.

- **Hermes enabled:** MCP ingest/query, HermesConnector polls sessions. Extra Inhale/Exhale paths.
- **Hermes disabled:** `HERMES_ENABLED=false` — connector does not start. REST, UDP, gRPC, other modules unchanged.
- **No Hermes at all:** INDB core (ingest, fusion, interpret, search, echo, prism) works via REST. No dependency on Hermes.

All modules follow this principle: **enable/disable without breaking core.**

---

## 2. No Hardcoding (PHILOSOPHY.md §7)

> "No hardcoded values — meaning is observer-dependent, context-dependent, never fixed"

**Implementation:**
- All thresholds, defaults, placeholders — in `core/constants.py`
- `INTERPRET_*`, `EVENT_RESPONSE_MISSING_*`, `PRISM_*`, `ECHO_*`, etc.
- JITRenderer, routes, kernel, indb — use constants
- When input is missing — fallback from constants, not magic strings

**Documentation:** `docs/index.md` — "Zero Hardcoded Values ✅"

---

## 3. docs/* Alignment

| Document | Key Points | Status |
|----------|------------|--------|
| `PHILOSOPHY.md` | Inhale/Exhale, no hardcode, observer context | ✅ |
| `README.md` | Inhale-Exhale-Axiom, Mass = Count × Rep² | ✅ |
| `USE_CASES.md` | Legal, Healthcare, Finance, Journalism, IoT | ✅ |
| `API.md` | POST /interpret = Exhale, not Lens | ✅ fixed |
| `TECHNICAL_REFERENCE.md` | scan(), JITRenderer, filter_key | ✅ |
| `CONTEXTUAL_LENS.md` | Triple-Half, POST /lens/query | ✅ |
| `HERMES_INDB_WORKFLOW.md` | MCP ingest/query, HermesConnector | ✅ |
| `HERMES_INTEGRATION_SCENARIOS.md` | Scenarios 1–5 | ✅ |
| `QUERY_COOKBOOK.md` | /events, /search, /interpret | ✅ |
| `PSYCHO.md` | Weight ablation, `POST /psycho/path` | ✅ 0.8.0 |
| `GRAIN.md` | exact → statistical identity | ✅ 0.8.0 |

---

## 4. Interpret vs Lens Separation

| Endpoint | Purpose | Concept |
|----------|---------|---------|
| `POST /interpret` | Scan memory with mood/goal, JIT rendering | **Exhale** — exhale meaning |
| `POST /lens/query` | Triple-Half (context_a + context_b, ratio) | **Contextual Lens** — blend perspectives |
| `POST /prism/synthesize` | Perception paradox, alternative_readings | **Prism** — competing readings |

Previously API.md 1.4 had "Contextual Scan (Lens)" for `/interpret` — fixed to "Exhale — Contextual Interpretation".

---

## 5. Flow Before and After Hermes

### Before Hermes
```
Client → POST /events (ingest)
Client → GET /events (list)
Client → POST /interpret (exhale)
Client → GET /search (resonate)
```

### With Hermes
```
Hermes → MCP ingest_event  → POST /events (same)
Hermes → MCP query_events  → kernel.query() → scan() (same)
Hermes → MCP get_stats     → stats
```

**Source Connector:** INDB polls `~/.hermes/sessions/` → ingests as events. Another Inhale source.

---

## 6. Constants (core/constants.py)

**Interpretation:**
- `INTERPRET_MOOD_DEFAULT`, `INTERPRET_FIREWALL_MODE_DEFAULT`
- `INTERPRET_ACTIVATION_*`, `INTERPRET_TEMPORAL_*`
- `INTERPRET_EMPTY_*`, `EVENT_RESPONSE_MISSING_*`
- `INTERPRET_TOKEN_NEGATIVE/POSITIVE/HIGH_ENERGY`

**Principle:** Input (request, event) → output (response). When input is missing — use constant, do not invent.

---

## 7. Integrity Checklist

- [x] All philosophy — in PHILOSOPHY.md
- [x] All architecture — in README, TECHNICAL_REFERENCE
- [x] API — in API.md, QUERY_COOKBOOK
- [x] Hermes — in HERMES_*.md (as pluggable module)
- [x] No hardcoding — in constants.py
- [x] Interpret ≠ Lens — in API.md
- [x] Inhale/Exhale/Resonate — in API.md, index.md
- [x] Psycho and Grain — in PSYCHO.md, GRAIN.md, API.md, release 0.8.0

---

*"Inhale the chaos. Exhale the noise. Remember the Axiom."*
