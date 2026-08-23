# Angle: Grain — Signal Through Noise

**Best for:** HN Phase 2, Lobsters, DEV.to part 2, technical Twitter  
**Hook:** Any verification is signal detection in noise.

---

## Problem (2 sentences)

Barcode, QR, biometric signature, and SynthID each solve **one point** on the noise-tolerance axis. Real memory needs all four — strict axioms *and* tolerant recall — in the same pipeline as reputation and signed events.

---

## INDB answer

**Grain** — kernel module, four tiers, one API:

| Tier | Analog | Mechanism |
|------|--------|-----------|
| exact | EAN-13 | Ed25519 |
| redundant | QR | N-of-M signed cluster |
| resonant | Handwriting | Echo × reputation, FAR/FRR |
| statistical | SynthID | n-gram p-value |

`tier: auto` · `tolerance: 0.0–1.0` · verdicts include `insufficient_signal`

---

## Proof URLs

```
GET  https://api.indb.tech/api/v2/grain/tiers
POST https://api.indb.tech/api/v2/grain/verify
Docs https://docs.indb.tech/GRAIN/
Site https://indb.tech/#grain
```

---

## Copy block (paragraph)

> INDB Grain unifies the noise-tolerance spectrum inside the kernel — from barcode-exact Ed25519 to SynthID-style statistical fingerprints — with honest uncertainty (`false_accept_risk`, `insufficient_signal`). External tools give you one tier per product; INDB gives you memory-aware verification in the same engine that ingests, fuses, and signs.

---

## Combine with channels

- HN: [../channels/01-hacker-news.md](../channels/01-hacker-news.md) Phase 2 title
- DEV.to: [../channels/04-dev-to.md](../channels/04-dev-to.md) Grain article
