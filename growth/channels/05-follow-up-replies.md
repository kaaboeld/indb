# Follow-up replies — FAQ patterns

Use in HN, Reddit, Lobsters comments. Adapt tone to thread.

---

## «How is this different from PostgreSQL + signatures?»

PostgreSQL stores rows; INDB stores **memory** — fusion, TTL decay, reputation-weighted verification. Grain isn't a trigger on insert; it's an epistemological layer: exact when you need axioms, resonant when memory tolerates rewrite. Prism/Echo run at query time on the same event stream.

---

## «blind_payload — how do we know you don't read it?»

No key on server — architecturally, not policy. Engine stores ciphertext blob; protocol forbids server-side decrypt for blind zones. Presence (`timestamp` + `location`) is mandatory; content is not accessible to query paths. Docs: Black Box Contract in PHILOSOPHY.md.

---

## «What's Grain / SynthID comparison?»

SynthID embeds at generation time; INDB ingests. Grain's statistical tier compares token n-gram distributions across event clusters — optional watermark at connector ingest. All four tiers (barcode→SynthID analog) in one API: https://docs.indb.tech/GRAIN/

Live: `curl https://api.indb.tech/api/v2/grain/tiers`

---

## «Is it open source?»

Proprietary core. Public API, docs, Swagger. Self-host via Docker/Fly. Architecture and contracts documented for audit.

---

## «Show HN timing / why now?»

Grain shipped as kernel module — unified identity verification was the missing piece between signed axioms and Echo resonance. Site + docs + API live.

---

## «Performance / production ready?»

0.11.1 (fusion scores shared tokens; 0.11.0 edges fade). Local tree, not yet the Fly image. Raft cluster for multi-node. Metrics in docs. Happy to share stress test notes from README.

---

## «Use case X?»

- **Legal / audit:** signed events + recovery by key_id
- **Healthcare:** blind_payload + presence proof
- **Crowd vs sensor:** Reality Guard — reputation gravity (see angles/reality-guard.md)
- **Partial quotes / rewrites:** Grain resonant tier

---

## Negative: «This is buzzword soup»

Fair pushback. Pick one path: (1) curl grain/tiers and verify JSON, (2) read GRAIN.md tier table, (3) skip if not your problem domain. We're optimizing for signed memory under manipulation, not CRUD replacement.

---

## CTA (always end helpful replies with)

```
Docs: https://docs.indb.tech
Contact: https://indb.tech/#contact
```
