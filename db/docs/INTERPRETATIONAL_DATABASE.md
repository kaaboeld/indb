# INDB — Interpretational Database

**INDB** = **I**nterpretational **D**ata**b**ase.

A new class of system — alongside relational, document, graph, and vector stores — defined by one rule:

> **Meaning is not stored at write time. It is produced at read time.**

---

## Not a database. Not an archive.

| | Classical DB / archive | Interpretational DB (INDB) |
|---|----------------------|----------------------------|
| Unit | Row / document | **Event** (anchor, not conclusion) |
| Write | Record final state | **Inhale** raw observation |
| Read | Fetch what was stored | **Interpret**, **Prism**, **Echo**, **Subwave** |
| Growth | More data = heavier | **Fusion** + **forgetting** (salience, cold tier) |
| Contradiction | Error or overwrite | **Signal** (`perception_gap`, paradox) |
| Privacy | Access control | **Black Box** + signed presence |

Archive preserves the past. **Memory** compresses, fades, and wakes on resonance.

---

## Interpretation stack (API surface)

| Phase | Endpoints / engines |
|-------|---------------------|
| Inhale | `POST /events`, UDP, gRPC, MCP ingest |
| Exhale | Fusion, TTL, entropy prune → **sleep** (not erase by default) |
| Resonate | Echo, Subwave, horizontal graph + index |
| Interpret | `POST /interpret`, Prism, Deduction |
| What-if | `POST /slice`, `POST /what-if` (core = no LLM) |
| Axiom | Ed25519 on responses; `blind_payload` contract |

LLM (Hermes/Ollama) is optional **voice** — not the interpretational core.

---

## One sentence

**INDB is an interpretational database: signed cognitive memory where context, observer, and «what if» reshape meaning without rewriting facts.**

---

## Related docs

- [PHILOSOPHY.md](./PHILOSOPHY.md) — Inhale / Exhale / Axiom
- [MEMORY_LIFECYCLE.md](./MEMORY_LIFECYCLE.md) — forgetting and wake
- [HORIZONTAL_SLICE.md](./HORIZONTAL_SLICE.md) — subwave resonance
- [TECHNICAL_REFERENCE.md](./TECHNICAL_REFERENCE.md) — how it runs
