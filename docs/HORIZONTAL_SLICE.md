# Horizontal Slice — Brick + Factors (Core What-If)

> Walk the pavement **horizontally**: from one raised brick (seed), compare features across linked cells — without re-scanning the whole context window like a vertical LLM.

## Model

| Concept | INDB |
|---------|------|
| Pavement cell | `Event` (tokens + location + time) |
| Raised brick | `seed_id` or resolved `query` |
| Horizontal factors | Tokens extracted from `what_if` (any abstract phrase) |
| Slice | Rescored resonance edges + optional Prism with observer overlay |

## Flow

```
1. ResonanceIndex → candidate event IDs (token/location overlap with seed)
2. Echo → score candidates only (not full O(N) memory when index is warm)
3. extract_factors(what_if) → ["meet", "girl", "dreams", ...]
4. apply_horizontal_shift → base_score, shifted_score, matched_factors per edge
5. Prism.synthesize(observer overlay from factors) → relational meaning under hypothetical
```

No LLM in this path. Hermes optional only for `what-if?mode=llm|both`.

## API

### `POST /api/v2/slice`

Dedicated horizontal slice (always available).

```json
{
  "seed_id": "evt-…",
  "what_if": "today I meet the girl of my dreams",
  "radius": 0.3,
  "limit": 20,
  "observer_context": { "token_weights": { "love": 1.5 } }
}
```

Or resolve brick from text:

```json
{
  "query": "birthday party",
  "what_if": "there is a fight"
}
```

**Response** (`data`):

- `factors` — extracted modifier tokens
- `edges[]` — `base_score`, `shifted_score`, `delta`, `matched_factors`
- `prism` — Prism result under overlay (if cloud non-empty)
- `logic` — human-readable trace of weight changes

### `POST /api/v2/what-if`

Base query + modifier.

| `mode` | Behavior |
|--------|----------|
| `core` (default) | `base_result` + `slice` (kernel only) |
| `llm` | `base_result` + `prediction` (Hermes/Ollama) |
| `both` | `slice` + `prediction` |

## Performance

- **Before**: Echo scanned all events O(N).
- **After**: `ResonanceIndex` narrows candidates (cap `RESONANCE_INDEX_MAX_CANDIDATES`), then score O(candidates).
- Index maintained on ingest and fusion update; rebuilt on startup from memory.

## Constants

See `core/constants.py`: `RESONANCE_INDEX_MAX_CANDIDATES`, `SLICE_FACTOR_MIN_LEN`, `SLICE_SHIFT_MAX`, `WHAT_IF_MODE_*`.

## Observer profiles (config, not hardcoded)

Copy `data/observer_profiles.example.json` → `data/observer_profiles.json` or set `OBSERVER_PROFILES_PATH`.

```json
POST /api/v2/slice
{
  "seed_id": "…",
  "what_if": "there is a fight",
  "observer_profile": "tactical"
}
```

List presets: `GET /api/v2/slice/profiles`

Explicit `observer_context` overrides `observer_profile`.

## What-If seed resolution

`POST /api/v2/what-if` with `mode=core` returns `seed_resolution` (`source`: `echo.center`, `search.top_hit`, `interpret.activation`, etc.) before `slice`.

## Index sync

`ResonanceIndex` rebuilds automatically after memory prune or TTL compaction (`MemoryManager.on_compaction`).

## Persisted resonance graph

Echo materializes horizontal edges to `{DATA_DIR}/resonance_edges.bin` (encrypted, same format family as `indb.bin`).

- **Load** on startup with `ResonanceGraph.load()`
- **Record** after each Echo wave (`record_wave`)
- **Lookup** before scan: `graph` ∪ `index` candidates (not full memory)
- **Prune** when events leave RAM (compaction callback)

Env: `RESONANCE_GRAPH_ENABLED` (default `true`).

Inspect edges: `GET /api/v2/slice/neighbors/{seed_id}`

Slice responses include `graph` stats (`resonance_graph`, `causal_index`).

## Semantic neighbors (optional ML)

When `sentence-transformers` is installed and `RESONANCE_SEMANTIC_ENABLED=true`, Echo adds embedding-similar events to the candidate pool (`semantic` in scan mode).

Env: `RESONANCE_SEMANTIC_THRESHOLD`, `RESONANCE_SEMANTIC_TOP_K`, `RESONANCE_SEMANTIC_POOL_CAP`.

## Causal / temporal links

`CausalIndex` links events in the same `location` within `CAUSAL_TIME_WINDOW_SEC` (default 24h). Persisted to `causal_edges.bin`.

```bash
GET /api/v2/slice/causal/{seed_id}?direction=both&limit=20
```

Echo scan mode may include `causal` alongside `graph`, `index`, `semantic`.

## Subwave (unified broadcast)

One anchor, one frequency — all horizontal neighbors scored for **phase lock**:

```http
POST /api/v2/subwave/broadcast
```

See [SUBWAVE_RESONANCE.md](./SUBWAVE_RESONANCE.md).

`POST /api/v2/slice` runs **subwave → slice** by default (`use_subwave=true`). Response includes all slice fields plus top-level `subwave`.

## Relation to LLM

LLM remains useful for **natural language** answers. Core slice owns **structure**: which links strengthen or weaken under a hypothetical. Use `mode=both` when you need both the graph shift and a prose summary.
