# Grain — Identity Tolerance Spectrum

**Grain** is INDB's identity verification module. It answers one question across four tiers of noise tolerance:

> *Is this the same origin — and how sure are we, given distortion?*

Where **Echo** finds *meaning* through resonance and **signing** delivers *binary axioms*, Grain unifies both into a single axis: from barcode-exact to SynthID-statistical.

```
Inhale identity. Tolerate noise. Verify the grain.
```

---

## The Problem

INDB stores **memory**, not frozen archives. Real memory tolerates:

- Partial quotes and rewrites (literary analysis)
- Surface change (signature on glass vs paper)
- Export damage (7 of 10 signed events survive backup loss)
- Long-run statistical fingerprints (token patterns over hundreds of events)

Ed25519 alone is **barcode-tier**: verified or rejected, ~0% tolerance. That is correct for Axioms — but insufficient for the full epistemological pipeline.

Grain fills the gap between **Axiom** (exact) and **Echo** (semantic resonance).

---

## The Noise-Tolerance Axis

From rigid binary data to flexible statistical patterns:

```
[Exact] ──────> [Redundant] ──────> [Resonant] ──────> [Statistical]
 ~0–5%              ~30%              ~30–50%           floating (p-value)
 Barcode            QR code           Signature         SynthID
 Ed25519            N-of-M cluster    Echo × rep        n-gram fingerprint
```

| Tier | Analogy | Mechanism | Verdict style |
|------|---------|-----------|---------------|
| **exact** | EAN-13 barcode | Ed25519 / `key_id` | `verified` or `rejected` |
| **redundant** | QR (Reed–Solomon H) | N-of-M signed events survive damage | `verified` / `likely_same_origin` |
| **resonant** | Handwritten signature | Echo resonance × source reputation + FAR/FRR | `likely_same_origin` |
| **statistical** | SynthID watermark | Token n-gram distribution vs reference cluster | p-value + length gate |

---

## Relationship to Other Modules

| Module | Layer | Question |
|--------|-------|----------|
| **Signing** | Storage | Is this cryptographically proven? |
| **Grain** | Identity | Same origin despite noise? |
| **Echo** | Meaning | What resonates with this? |
| **Prism** | Interpretation | What does it *mean* to this observer? |
| **Recovery** | Restore | Can we rebuild signed memory by `key_id`? |

Grain **uses** Echo internally for the resonant tier but does not replace it. Grain **wraps** signing for the exact tier but does not weaken Axiom requirements.

---

## API

### List tiers

```bash
curl https://api.indb.tech/api/v2/grain/tiers
```

### Verify identity

```bash
curl -X POST https://api.indb.tech/api/v2/grain/verify \
  -H "Content-Type: application/json" \
  -d '{
    "reference_event_id": "<seed-event-uuid>",
    "candidate": {
      "raw_data_anchor": ["partial", "rewrite", "summer", "wine"],
      "location": "books/test"
    },
    "tier": "auto",
    "tolerance": 0.5
  }'
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "tier_used": "resonant",
    "match_score": 0.62,
    "p_value": null,
    "signal_to_noise": 1.63,
    "verdict": "likely_same_origin",
    "false_accept_risk": 0.08,
    "false_reject_risk": 0.12,
    "insufficient_signal": false,
    "tokens_observed": 4,
    "min_tokens_required": 0,
    "key_id": null,
    "insight": "Resonance 0.71 × reputation 0.50 ≥ threshold 0.50 — likely same origin.",
    "meta": {
      "resonance": 0.71,
      "reputation": 0.5,
      "threshold": 0.5,
      "reference_id": "...",
      "candidate_id": "..."
    }
  }
}
```

### Request fields

| Field | Required | Description |
|-------|----------|-------------|
| `candidate` | yes | Event dict or partial event (`raw_data_anchor`, optional `signature`) |
| `reference_event_id` | resonant / statistical | Primary seed event |
| `reference_event_ids` | redundant | Cluster of signed events for N-of-M check |
| `expected_key_id` | exact / redundant | SHA-256 public identity hash |
| `tier` | no | `auto` (default), `exact`, `redundant`, `resonant`, `statistical` |
| `tolerance` | no | 0.0 = strict (high false reject) → 1.0 = permissive (high false accept) |
| `min_tokens` | no | Minimum tokens for statistical tier (default: 20) |
| `min_events` | no | Minimum events for redundant tier (default: 3) |
| `damage_ratio` | no | Max tolerated damage for redundant tier (default: 0.30) |

### Verdicts

| Verdict | Meaning |
|---------|---------|
| `verified` | Axiom-grade match (exact or full redundant cluster) |
| `likely_same_origin` | Probabilistic match — resonant or statistical |
| `insufficient_signal` | Too little data (e.g. 20 tokens for SynthID-like detection) |
| `rejected` | Origin not confirmed at chosen tier |

---

## Tier Details

### 1. Exact (~0–5%)

Uses `core/signing.py` — Ed25519 over canonical event fields.

```bash
curl -X POST https://api.indb.tech/api/v2/grain/verify \
  -H "Content-Type: application/json" \
  -d '{
    "candidate": { "...signed event..." },
    "tier": "exact",
    "expected_key_id": "<64-char-hex>"
  }'
```

Binary threshold: signature valid or not. Use for Axioms and recovery proofs.

### 2. Redundant (~30%)

QR-like: a cluster of signed events tolerates partial export loss.

```bash
curl -X POST https://api.indb.tech/api/v2/grain/verify \
  -H "Content-Type: application/json" \
  -d '{
    "reference_event_ids": ["id-1", "id-2", "id-3", "id-4"],
    "tier": "redundant",
    "damage_ratio": 0.30,
    "expected_key_id": "<key_id>"
  }'
```

Survival ratio = valid signatures / total. Default requires ≥70% valid (30% damage tolerance).

### 3. Resonant (~30–50%)

Signature biometrics: same hand, different surface.

```
match_score = resonance × (0.5 + reputation × 0.5)
threshold   = 0.70 − tolerance × 0.40
```

- **Low tolerance (0.0):** threshold ≈ 0.70 — strict, more false rejects
- **High tolerance (1.0):** threshold ≈ 0.30 — permissive, more false accepts

Use for: partial rewrites, fused events, cross-location echoes, Reality Guard signal vs crowd.

### 4. Statistical (floating p-value)

SynthID-like: compares candidate token n-grams to a reference cluster distribution.

**Length gate:** short candidates cannot be verified — same as SynthID in 20 words vs 500 words.

```
Reference cluster: ≥ min_tokens (default 20) across ≥ 2 events
Candidate:         ≥ max(5, min_tokens / 4) tokens
```

Optional watermark embedding for source connectors:

```python
from core.grain.statistical import embed_watermark_bias

tokens = embed_watermark_bias(
    tokens=["memory", "truth", "signal"],
    secret=b"source-watermark-secret",
    strength=0.15,
)
```

Call from `services/sources/*/transformer.py` at ingest time — not applied automatically.

---

## Auto Tier Selection

When `tier: "auto"`:

1. Candidate has `signature` → **exact**
2. Reference cluster ≥ `min_events` with signatures → **redundant**
3. Reference + candidate token counts meet statistical gates → **statistical**
4. Otherwise → **resonant** (requires `reference_event_id`)

---

## Use Cases

### Recovery after partial export

Export lost 2 of 5 signed events. Redundant tier: 3/5 = 60% < 70% → rejected at default; lower `damage_ratio` to 0.40 → `likely_same_origin`.

### Literary partial quote

Original event ingested from Dostoevsky. Candidate is a partial rewrite. Resonant tier with moderate tolerance confirms thematic origin without exact token match.

### Reality Guard

- Crowd events (low reputation) → resonant tier, high false_accept_risk
- Internal heartbeat (high reputation + exact signature) → exact tier, `verified`

### Source connector provenance

Long-running Hermes/Moltbook ingest builds statistical fingerprint per `key_id`. Later partial repost detected via statistical tier.

---

## Architecture

```
routes/grain.py
    └── GrainEngine (core/grain/engine.py)
            ├── exact.py      → core/signing.py
            ├── redundant.py  → exact × N
            ├── resonant.py   → core/echo.py + source reputation
            └── statistical.py → n-gram chi-squared
```

---

## Philosophy

Any verification is **signal detection in noise**.

- QR: digital signal — 100% or 0% at the cliff edge
- Signature / SynthID: analog signal — delta distance from reference, FAR/FRR tradeoff

INDB's Axiom layer stays exact. Grain makes the layers above it honest about uncertainty — without pretending memory is a barcode.

---

## See Also

- [Signed Memory Recovery](./SIGNED_MEMORY_RECOVERY.md) — exact-tier restore by `key_id`
- [Philosophy](./PHILOSOPHY.md) — perception gap, relational meaning
- [API Reference](./API.md) — full endpoint catalog
