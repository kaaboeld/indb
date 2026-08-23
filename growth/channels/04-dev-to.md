# DEV.to — full article

**New post:** https://dev.to/new

> **Основная статья (уникальная):** [`DEV_TO_UNIQUE.md`](./DEV_TO_UNIQUE.md)  
> Угол «Memory acts, not CRUD» — copy-paste оттуда.

**Tags (unique):** `architecture` `database` `api` `security` `ai`

---

## Title (unique — recommended)

```
Your API Shouldn't Expose Tables. It Should Expose Memory Acts.
```

## Title (generic fallback)

```
We Built a Database That Cannot Read Your Data
```

**Grain follow-up title:**
```
INDB Grain: When Identity Verification Is Signal Detection in Noise
```

---

## Body (Markdown) — Phase 1

```markdown
# We Built a Database That Cannot Read Your Data

> "When everyone lies, INDB remembers what you saw."

INDB is not a database. It's an **interpretational database** — meaning is produced when you query, not frozen when you ingest.

## The Problem

How do you maintain objective reality when collective gaslighting can rewrite history? When PDFs can be edited, logs altered, timestamps faked?

## The Approach

Treat data as a **biological process**: inhale, exhale, axiom.

- **Inhale** — accept raw reality. Multi-protocol (UDP, gRPC, HTTP, WebSocket). <1ms ingestion.
- **Exhale** — compress truth, purge noise. `Mass = Count × Reputation²`.
- **Axiom** — what remains is Ed25519-signed.

## The Cognitive Layer

- **Prism** — paradox-aware synthesis. Competing readings, perception gap.
- **Echo** — resonance across tokens, emotion, location.
- **Instinct** — adrenaline reflexes (analytical → instinctive).
- **Deduction** — evidence chains from seeds.
- **Blind** — `blind_payload`: encrypted before server touch. We store. We never read. No backdoor.

## The Black Box Contract

When you use `blind_payload`:
- You may hide what is inside.
- You may not hide that you were here.

`timestamp` and `location` are mandatory. Presence is provable; content is not.

## Grain — Signal Through Noise (new)

Any verification is **signal detection in noise**:

| Analog | Tolerance | INDB Grain tier |
|--------|-----------|-----------------|
| Barcode | ~0% | exact (Ed25519) |
| QR | ~30% | redundant (N-of-M) |
| Signature | ~30–50% | resonant (Echo × reputation) |
| SynthID | p-value | statistical (n-gram) |

One kernel API: `POST /api/v2/grain/verify` with `tier: auto`.

Try: https://api.indb.tech/api/v2/grain/tiers

## Links

- **Site:** https://indb.tech
- **Docs:** https://docs.indb.tech
- **Grain:** https://docs.indb.tech/GRAIN/
- **API:** https://api.indb.tech/docs

Feedback welcome — especially from anyone building audit or compliance pipelines.
```

---

## Body excerpt — Grain-only article (Phase 2)

Use content from [../angles/grain.md](../angles/grain.md) sections «Problem» and «Why kernel-level».
