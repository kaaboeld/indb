# What-If — Hypothetical Prediction (Hermes-gated)

## Concept

**What-If** is a cognitive modifier that takes any INDB query result and applies an abstract hypothetical: "What would this look like if X were different?"

Examples:
- *"What if it rains based on this data?"*
- *"What if this happened in Moscow instead of London?"*
- *"What if I was 4 years old instead of 20?"*

The LLM reasons over the real query result and produces a hypothetical prediction.

---

## Gate: Hermes Required

- **Hermes disabled** → `503 Service Unavailable` with `detail: "What-if requires Hermes. Set HERMES_ENABLED=true."`
- **Hermes enabled** → Feature available

Hermes being enabled implies the LLM stack (Ollama / Hermes) is available for inference.

---

## API

```
POST /api/v2/what-if
```

**Request:**
```json
{
  "base_query_type": "interpret" | "search" | "echo" | "prism" | "deduction",
  "base_params": { ... },
  "what_if": "what if it rains"
}
```

**Response:**
```json
{
  "data": {
    "base_result": { ... },
    "prediction": "If it were raining, the resonance pattern would shift...",
    "what_if": "what if it rains"
  },
  "status": "success"
}
```

---

## Flow

### mode=core (default, no Hermes)

1. Execute base query → `base_result`
2. Resolve seed from base (echo center, search top hit, or `seed_id` / `query` in params)
3. **Subwave** — unified frequency broadcast; `locked_nodes`, `coherence`
4. **Slice** — Echo → factor rescoring → Prism overlay on the same anchor
5. Return `base_result` + `subwave` + `slice` (`use_subwave=false` skips step 3)

See [HORIZONTAL_SLICE.md](./HORIZONTAL_SLICE.md).

### mode=llm | both

1. Gate: `HERMES_ENABLED` for LLM leg
2. Base query + optional slice logic fed to Ollama/Hermes
3. Return `prediction` (and `slice` when `both`)

---

## Supported Base Queries

| base_query_type | base_params |
|-----------------|-------------|
| `interpret` | `context`, `temporal_query`, `limit` |
| `search` | `q`, `limit`, `fuzzy` |
| `echo` | `seed_id`, `radius`, `limit` |
| `prism` | `query`, `radius`, `limit` |
| `deduction` | `query` or `seed_event_ids`, `radius`, `limit` |

---

## LLM Backend

1. **Ollama** (preferred): `POST http://localhost:11434/api/generate` — fast, no subprocess
2. **Hermes subprocess** (fallback): `hermes chat -Q -q "{prompt}"` — when Ollama not configured

Env: `OLLAMA_URL` (default `http://localhost:11434`), `OLLAMA_MODEL` (default `llama3.2` or Hermes model).
