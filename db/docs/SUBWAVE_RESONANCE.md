# Subwave Resonance — Unified Horizontal Broadcast

## Metaphor (architecture, not magic)

In a collapsed context, memories float as isolated fragments. A vertical LLM retraces every pair via attention — expensive and unstable at scale.

INDB uses an **anchor** (seed event — the raised brick, the Earth locked to TARDIS):

1. **Echo** sends a wave across the horizontal plane (token, location, time).
2. **Subwave** tunes every reachable node to **one frequency** — a signature from the anchor (+ optional modifier).
3. Nodes that **lock in** form a coherent frame (materialized in `resonance_edges.bin`).
4. No need to recompute the whole universe — only nodes with real mass (events in memory) that answer the broadcast.

This is query-time graph coherence, not generative guessing.

## API

```http
POST /api/v2/subwave/broadcast
```

```json
{
  "seed_id": "evt-anchor",
  "modifier": "what if all planets broadcast the same rescue frequency",
  "radius": 0.3,
  "limit": 50,
  "lock_threshold": 0.35
}
```

Or resolve anchor by text:

```json
{
  "query": "earth tardis anchor",
  "modifier": "neighbor understands the sticker"
}
```

### Response

| Field | Meaning |
|-------|---------|
| `anchor` | Unified signature (tokens, location, factors) |
| `locked_nodes` | Events in phase (`lock_score`, alignments) |
| `coherence` | Mean lock score of tuned nodes |
| `scan_mode` | `graph+causal+index+semantic` or `full` |
| `nodes_tuned` / `nodes_locked` | Pool size vs locked count |

Locked ripples are persisted to the resonance graph (same as Echo).

## Lock score

```
lock = W_res * resonance + W_tok * token_alignment + W_fac * factor_alignment
```

Constants: `SUBWAVE_*` in `core/constants.py`.

## Related endpoints

| Endpoint | Role |
|----------|------|
| `POST /api/v2/echo/resonate` | Classic resonance cloud |
| `POST /api/v2/slice` | What-if horizontal shift on cloud |
| `POST /api/v2/what-if` | Base query + slice / LLM |
| `GET /api/v2/slice/neighbors/{id}` | Materialized edges |
| `GET /api/v2/slice/causal/{id}` | Temporal links |

See [HORIZONTAL_SLICE.md](./HORIZONTAL_SLICE.md).
