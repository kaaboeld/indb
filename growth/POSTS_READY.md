# Готовые тексты — copy-paste по шагам

Всё ниже — финальный текст. Копируй как есть. Ссылки только канонические.

> **HN Show HN заблокирован?** → [HN_WARMUP.md](./HN_WARMUP.md) — Plan B: начни с **ШАГ 2** (Lobsters), не с ШАГ 1.

---

## ШАГ 0 — перед публикацией (5 минут)

1. Открой https://indb.tech — страница грузится
2. Открой https://api.indb.tech/health — ответ OK
3. Открой https://api.indb.tech/api/v2/grain/tiers — JSON с 4 tier'ами
4. Открой https://indb.tech/#contact — форма на месте
5. Запиши дату/время старта в `METRICS.md`

---

## ШАГ 1 — Hacker News (День 0) ⏸ если restriction

**Если HN пишет *«temporarily restricting Show HNs»* — пропусти этот шаг.**  
См. [HN_WARMUP.md](./HN_WARMUP.md). Начни с **ШАГ 2** (Lobsters).

**URL формы:** https://news.ycombinator.com/submit

### 1.1 Поле «title» — скопируй целиком:

```
Show HN: INDB – Interpretational database, signed memory, zero-knowledge storage
```

### 1.2 Поле «url» — скопируй:

```
https://indb.tech
```

### 1.3 Поле «text» (если есть) — скопируй целиком:

```
When everyone lies, INDB remembers what you saw.

INDB is an interpretational database — not a row store. Meaning is produced when you query (Prism, Echo, Instinct), not frozen when you ingest.

Inhale → accept raw events (HTTP, UDP, gRPC, WebSocket).
Exhale → fusion compresses noise; reputation is gravity (Mass = Count × Reputation²).
Axiom → Ed25519-signed core.

Modules:
• Prism — paradox-aware synthesis (competing readings, perception gap)
• Echo — resonance across tokens, emotion, location
• Instinct — adrenaline reflexes (analytical → instinctive)
• Deduction — evidence chains from seeds
• Blind — blind_payload: encrypted client-side; engine never reads it; no key on server
• Grain — identity verification across noise: exact → redundant → resonant → statistical (barcode to SynthID axis in one kernel API)

Live: https://indb.tech
API: https://api.indb.tech/docs
Docs: https://docs.indb.tech
Grain: https://docs.indb.tech/GRAIN/
Try: https://api.indb.tech/api/v2/grain/tiers
```

### 1.4 Нажми Submit

### 1.5 Сразу после публикации — первый комментарий от себя под постом:

```
Author here.

We built INDB because most systems treat data as storage. We treat it as memory: it fuses, decays, and sometimes contradicts itself — and that's signal, not bug.

Three things that aren't marketing:
1. blind_payload — server stores ciphertext, has no decryption key. Presence (time + location) is still anchored.
2. Signed events — client signs with private key; server only verifies public key + signature. Recovery by key_id, never by private key.
3. Grain — one API for verification from strict Ed25519 (0% noise) to statistical fingerprint (SynthID-like). tier:auto picks the tier.

Happy to go deep on architecture, self-host (Docker), or any module. What would you stress-test first?
```

### 1.6 Ответы на типовые комментарии (копируй по ситуации)

**«How is this different from Postgres?»**
```
Postgres stores rows with fixed schema. INDB stores events as token + location observations; meaning is computed at query time (Prism/Echo). Fusion deduplicates semantically. Grain verifies identity across noise — not a DB constraint. Different category: interpretational database, not CRUD replacement.
```

**«Open source?»**
```
Core is proprietary. API, Swagger, and full docs are public. You can self-host via Docker Compose (see docs). Architecture guarantees (Blind contract, Grain tiers) are documented openly because they're structural, not secret sauce.
```

**«blind_payload — how do we trust you don't read it?»**
```
No key on server — by architecture, not policy. blind_payload is stored as opaque blob; query paths don't decrypt it. Trade-off: you prove presence (timestamp + location mandatory), not content. Docs: https://docs.indb.tech/PHILOSOPHY.md — Black Box Contract.
```

**«What's Grain?»**
```
Unified noise-tolerance axis for identity verification:
• exact — Ed25519 (~0% noise, like barcode)
• redundant — N-of-M signed events (~30%, like QR)
• resonant — Echo × reputation (~30–50%, like signature biometrics)
• statistical — n-gram p-value (SynthID-like)

One endpoint: POST /api/v2/grain/verify with tier:auto
Live catalog: https://api.indb.tech/api/v2/grain/tiers
```

**«Buzzword soup»**
```
Fair. Skip the philosophy — curl https://api.indb.tech/api/v2/grain/tiers and read the JSON. If that's not interesting for your use case, no worries. We're targeting signed memory under manipulation, not generic CRUD.
```

---

## ШАГ 2 — Lobsters (День +1, через ~24ч после HN)

**URL:** https://lobste.rs/submit

### 2.1 Title:

```
INDB – Interpretational database: signed memory, Grain verification, zero-knowledge blind storage
```

### 2.2 URL:

```
https://indb.tech
```

### 2.3 Description:

```
Not a database — interpretational engine. Inhale / exhale / axiom. Prism, Echo, Instinct, Deduction, Blind (engine never reads blind_payload). Grain: barcode→QR→signature→SynthID verification tiers in one kernel API. Ed25519 signed events optional. Docker self-host.

https://api.indb.tech/docs
https://docs.indb.tech/GRAIN/
```

### 2.4 Submit

---

## ШАГ 3 — Reddit r/selfhosted (День +1, через ~2ч после Lobsters)

**URL:** https://www.reddit.com/r/selfhosted/submit

### 3.1 Flair:

```
Software
```
(или `Show and Tell` — что доступно)

### 3.2 Title:

```
INDB – self-hosted interpretational engine: signed memory, blind storage, Grain identity verification
```

### 3.3 Post body — скопируй целиком:

```
Built something different from "another database" — INDB is an interpretational engine you can self-host (Docker Compose, Fly).

What it does:

**Signed memory** — events optionally Ed25519-signed at ingest. Client keeps private key; server stores public key + signature only. Restore by public key_id fingerprint.

**Blind storage** — `blind_payload`: you encrypt client-side, we store ciphertext. No decryption key on server. Architecturally unreadable. But timestamp + location are mandatory — you can hide content, not presence.

**Grain** — new module: identity verification across noise in one API. Strict Ed25519 (exact) → N-of-M cluster (redundant) → Echo × reputation (resonant) → statistical fingerprint (SynthID-like). `tier: auto` picks the tier.

**Cognitive layer** — Prism (paradox-aware meaning), Echo (resonance), Instinct (urgency reflexes), Deduction (evidence chains), Fusion (semantic dedup).

Multi-protocol: HTTP, UDP, gRPC, WebSocket. WUI dashboard at /wui/.

Use cases: audit trails, compliance, journalism source protection, IoT with signed events.

Links:
- Site: https://indb.tech
- Docs: https://docs.indb.tech
- API: https://api.indb.tech/docs
- Grain: https://docs.indb.tech/GRAIN/
- Live proof: https://api.indb.tech/api/v2/grain/tiers

Would love feedback from self-hosters — especially around signed export and blind zones.
```

### 3.4 Submit

---

## ШАГ 4 — DEV.to (День +3 … +5)

> **Рекомендуется:** уникальная статья → [`channels/DEV_TO_UNIQUE.md`](./channels/DEV_TO_UNIQUE.md)  
> (угол «Memory acts, not CRUD» — не дублирует generic ниже)

**URL:** https://dev.to/new

### 4.1 Title:

```
We Built a Database That Cannot Read Your Data
```

### 4.2 Tags (через запятую):

```
database, privacy, architecture, security
```

### 4.3 Body — скопируй целиком (Markdown):

```markdown
# We Built a Database That Cannot Read Your Data

> "When everyone lies, INDB remembers what you saw."

Most databases store rows. **INDB stores memory** — it ingests chaos, compresses noise, and keeps a signed core. Meaning is produced when you *query*, not when you *insert*.

We call it an **interpretational database**.

---

## The problem

How do you preserve what happened when:

- PDFs get edited after the fact
- Logs can be rewritten
- Crowds scream louder than one sensor
- You must **prove presence** without revealing **content**

---

## Inhale → Exhale → Axiom

**Inhale** — multi-protocol ingest (HTTP, UDP, gRPC, WebSocket). Accept raw events: tokens + location. No fixed schema. Sub-millisecond ingestion target.

**Exhale** — fusion engine semantically deduplicates. Repetition fades. Noise loses mass.

```
Mass = Count × Reputation²
```

A thousand bot messages weigh less than one signed sensor heartbeat.

**Axiom** — what survives is optionally Ed25519-signed. Tamper-evident. Recovery by public `key_id` — private keys never touch the server.

---

## Blind: we store it, we never read it

`blind_payload` is encrypted **before** it reaches INDB.

- No decryption key on the server
- No backdoor by policy — **architecturally** unreachable
- But: `timestamp` and `location` are **mandatory**

The contract:

> You may hide what is inside.  
> You may not hide that you were here.

For auditors: *Something was here. This place. This time.* What it was — unknown by design.

---

## Cognitive modules (ways of recalling)

| Module | What it does |
|--------|----------------|
| **Prism** | Synthesis with paradox — competing readings, perception gap |
| **Echo** | Resonance — similar events by token, emotion, location |
| **Instinct** | Urgency modes — deep analysis vs instant reflex |
| **Deduction** | Evidence chains — seeds → expansion → conclusion |
| **Fusion** | Semantic dedup — memory breathes |

---

## Grain: signal detection in noise

Any verification is **signal detection in noise**.

| Analog | Tolerance | INDB Grain tier |
|--------|-----------|-----------------|
| Barcode (EAN-13) | ~0% | **exact** — Ed25519 |
| QR code | ~30% | **redundant** — N-of-M signatures |
| Handwritten signature | ~30–50% | **resonant** — Echo × reputation |
| SynthID / watermark | p-value | **statistical** — n-gram fingerprint |

External world: four different tools, four silos.

INDB: one kernel API — `POST /api/v2/grain/verify` with `tier: auto`.

Response includes honest uncertainty: `false_accept_risk`, `false_reject_risk`, `insufficient_signal` when the text is too short for statistical detection.

Try it:

```bash
curl https://api.indb.tech/api/v2/grain/tiers
```

---

## Who is this for?

- Legal / compliance — signed events, recovery proofs
- Healthcare / HR — blind zones with presence anchoring
- Journalism — protect sources, prove timing
- IoT / ops — crowd noise vs sensor truth (Reality Guard)
- Anyone tired of "we promise not to read your data"

---

## Links

- **Site:** https://indb.tech
- **Docs:** https://docs.indb.tech
- **Grain:** https://docs.indb.tech/GRAIN/
- **API (Swagger):** https://api.indb.tech/docs
- **Contact:** https://indb.tech/#contact

Feedback welcome — especially from people building audit or self-hosted pipelines.
```

### 4.4 Publish

---

## ШАГ 5 — Hacker News Phase 2 (Неделя 2, отдельный пост про Grain)

**URL:** https://news.ycombinator.com/submit

### 5.1 Title:

```
Show HN: INDB Grain – barcode to SynthID identity verification in one kernel
```

### 5.2 URL:

```
https://docs.indb.tech/GRAIN/
```

### 5.3 Text:

```
Any verification is signal detection in noise.

Barcode: ~0% tolerance — binary pass/fail.
QR: ~30% damage, then cliff.
Signature biometrics: FAR/FRR tradeoff.
SynthID: p-value, length-dependent — 20 tokens = no signal, 500 = strong.

Each lives in a separate product. INDB Grain unifies all four inside the database kernel:

• exact — Ed25519
• redundant — N-of-M signed event cluster
• resonant — Echo × source reputation
• statistical — token n-gram distribution

POST /api/v2/grain/verify — tier:auto, tolerance knob for FAR/FRR, insufficient_signal when data is too short.

Part of INDB (interpretational database — memory, not archive).

Site: https://indb.tech/#grain
Docs: https://docs.indb.tech/GRAIN/
Try: curl https://api.indb.tech/api/v2/grain/tiers
```

### 5.4 First comment:

```
Author here — Grain shipped because signed Ed25519 alone is "barcode tier" (~0% noise). Real memory tolerates partial quotes, export loss, and surface change. We needed one axis from axiom to statistical fingerprint without bolting on four SDKs.

Happy to discuss tier selection, resonant vs exact trade-offs, or how this connects to reputation gravity (Mass = Count × Reputation²).
```

---

## ШАГ 6 — Lobsters Phase 2 (Grain)

**URL:** https://lobste.rs/submit

### 6.1 Title:

```
INDB Grain – unified noise-tolerance verification (barcode to SynthID) in the kernel
```

### 6.2 URL:

```
https://docs.indb.tech/GRAIN/
```

### 6.3 Description:

```
Four verification tiers, one API: exact (Ed25519) → redundant (N-of-M) → resonant (Echo×rep) → statistical (n-gram). tier:auto. Honest FAR/FRR and insufficient_signal. Part of interpretational database INDB.
```

---

## ШАГ 7 — Twitter/X thread (опционально, 6 твитов)

**Твит 1:**
```
Any verification is signal detection in noise.

Barcode → 0%
QR → 30%, cliff
Signature → FAR/FRR
SynthID → p-value, length-dependent

We put all four tiers inside one database kernel.

INDB Grain 🧵
```

**Твит 2:**
```
INDB isn't a row store. It's an interpretational database.

Meaning at query time — Prism, Echo, Instinct.
Memory that fuses and decays — not frozen archive.

Inhale. Exhale. Axiom.

https://indb.tech
```

**Твит 3:**
```
Grain tier: EXACT (~0% noise)

Ed25519 signatures. Binary: verified or rejected.

For axioms — the irreducible core that must not bend.

Same hand, but this is the barcode layer.
```

**Твит 4:**
```
Grain tier: RESONANT (~30–50%)

Echo resonance × source reputation.

Same origin, different surface — partial rewrite, fused event, "signature on glass vs paper."

FAR/FRR exposed in API response. No fake binary confidence.
```

**Твит 5:**
```
Grain tier: STATISTICAL (p-value)

SynthID-like: token n-gram distribution vs reference cluster.

20 tokens? insufficient_signal — honest floor.
500 tokens? strong fingerprint.

curl https://api.indb.tech/api/v2/grain/tiers
```

**Твит 6:**
```
One engine. Signed memory. Blind storage (engine never reads blind_payload).

Docs: https://docs.indb.tech/GRAIN/
Site: https://indb.tech/#grain

When everyone lies, INDB remembers what you saw.
```

---

## ШАГ 8 — после каждого поста

1. Ответить на каждый комментарий с вопросом — в течение 6h (HN) / 24h (остальное)
2. Проверить https://indb.tech/#contact — ответить на заявки < 48h
3. Записать в `METRICS.md`: дата, канал, ссылка на пост, points/upvotes, число комментариев, contact leads

---

## ШАГ 9 — email ответ на contact form (шаблон)

**Subject:** Re: INDB inquiry

```
Hi [NAME],

Thanks for reaching out about INDB.

[1–2 sentences answering their specific question]

Quick links:
• Overview: https://indb.tech
• Documentation: https://docs.indb.tech
• API: https://api.indb.tech/docs
• Grain module: https://docs.indb.tech/GRAIN/

If you're evaluating self-host: Docker Compose instructions are in the deployment docs.

Happy to go deeper on [their topic] if useful.

—
INDB
```

---

*Файл обновляй после каждого launch: что сработало, что спрашивали чаще всего.*
