# INDB Console Guide

INDB ships two operational dashboards that mirror each other:

| Interface | Best for | URL / command |
|-----------|----------|---------------|
| **WUI** (Web Console) | Daily ops, demos, sharing links, Query Lab | `https://api.indb.tech/wui/` or `http://localhost:8000/wui/` |
| **TUI** (Terminal UI) | SSH sessions, low bandwidth, script runner | `cd db && ./start_tui.sh` |

Both talk to the **same live API**. Neither stores data locally — they poll and query the configured endpoint.

**Default production API:** `https://api.indb.tech`

**Local cluster (load balancer):** `http://localhost:8888`

---

## Quick start

### Web Console (WUI)

```bash
# Production (already deployed with API)
open https://api.indb.tech/wui/

# Local dev (hot reload)
cd db/wui && npm install && npm run dev
# → http://localhost:5174/wui/

# Rebuild static bundle served by FastAPI
cd db/wui && npm run build
# → http://localhost:8000/wui/
```

In the header, leave **API URL** empty to use the same origin, or paste e.g. `https://api.indb.tech` and click **Connect**.

### Terminal UI (TUI)

```bash
cd db
./start_tui.sh

# Explicit API
INDB_API_URL=https://api.indb.tech ./start_tui.sh

# Local cluster
INDB_API_URL=http://localhost:8888 ./start_tui.sh
```

On startup, check the **Control** log for:

```
TUI build 2026-07-11e picker=inline-dropdown-v2
```

---

## Shared tabs (what each section is for)

| Tab | Purpose | Who uses it |
|-----|---------|-------------|
| **Control** | Is the system alive? How many events? Fusion rate? CPU/RAM? | Everyone — first screen |
| **Events** | Browse and search raw memory — see what INDB actually holds | Debugging ingest, corpus inspection |
| **Modules** | Source connectors (Hermes, Moltbook, …) and transport protocols | Ops / integration |
| **Cluster** | API + Raft health per endpoint | Cluster / SRE |
| **Query** | Cognitive API playground — interpret, prism, echo, paradox, … | Developers, analysts |
| **Analytics** | Deep metrics, insights, fusion/temporal/cognitive JSON | Performance tuning |
| **Scripts** *(TUI only)* | Run read-only maintenance scripts against live API | Local dev / CI checks |

---

## Query Lab — all modes with examples

Use the **Query** tab in WUI or TUI. Fields use `|` as separator inside **Primary** unless noted.

Set API base first (WUI header or `INDB_API_URL` for TUI).

### Interpret (Exhale) — contextual recall

**What it does:** Returns events matching mood + location (+ optional goal). This is the core “exhale” — meaning at query time.

| Field | Example |
|-------|---------|
| Primary | `Neutral \| books/Orwell/1984` |
| Secondary | `surveillance` *(optional goal)* |

```bash
curl -X POST https://api.indb.tech/api/v2/interpret \
  -H "Content-Type: application/json" \
  -d '{"context":{"mood":"Neutral","location":"books/Orwell/1984","goal":"surveillance"},"limit":5}'
```

### Prism Synthesize — meaning from text or event ID

**Primary:** `would have died` or a full event UUID

```bash
curl -X POST https://api.indb.tech/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d '{"query":"would have died","limit":10}'
```

### Prism Instinct — adrenaline-weighted reflex

**Primary:** `birthday cheese | 0.8` — or query in Primary, adrenaline in Secondary

```bash
curl -X POST https://api.indb.tech/api/v2/prism/instinct \
  -H "Content-Type: application/json" \
  -d '{"query":"birthday cheese","adrenaline":0.8,"limit":10}'
```

### Lens Query — blend two contexts

**Primary:** `recent | historical`

```bash
curl -X POST https://api.indb.tech/api/v2/lens/query \
  -H "Content-Type: application/json" \
  -d '{"context_a":"recent","context_b":"historical","ratio":[0.5,0.5],"limit":20}'
```

### Echo Resonate — harmonic ripples from seed event

**Primary:** event UUID (copy from Events tab)

```bash
curl -X POST https://api.indb.tech/api/v2/echo/resonate \
  -H "Content-Type: application/json" \
  -d '{"seed_id":"<uuid>","radius":0.3,"limit":20}'
```

### Deduction — evidence chains

**Primary:** `birthday cheese`

```bash
curl -X POST https://api.indb.tech/api/v2/deduction/deduce \
  -H "Content-Type: application/json" \
  -d '{"query":"birthday cheese","limit":15}'
```

### What-If — hypothesis on search results

**Primary:** `whale | moby`

```bash
curl -X POST https://api.indb.tech/api/v2/what-if \
  -H "Content-Type: application/json" \
  -d '{"base_query_type":"search","base_params":{"q":"whale"},"what_if":"moby","mode":"core"}'
```

### Context Slice — slice + counterfactual

**Primary:** `lord | holy`

```bash
curl -X POST https://api.indb.tech/api/v2/slice \
  -H "Content-Type: application/json" \
  -d '{"query":"lord","what_if":"holy","limit":20}'
```

### Paradox Create / Read

**Create — Primary:** comma-separated source event IDs  
**Secondary:** `generation_mode` (e.g. `resonance_weighted`)  
**Tertiary:** `collapse_mode` (e.g. `sample_once`)

**Read — Primary:** paradox UUID

See [PARADOX.md](./PARADOX.md) for semantics.

### Recovery Identity

**Primary:** SHA-256 `key_id` of a public signing key

```bash
curl https://api.indb.tech/api/v2/recovery/identity/<key_id>
```

---

## Events tab — workflow

1. **Source dropdown** (▾ on the left in WUI):
   - **All sources** — mixed sample from each top location (not only newest batch)
   - **Latest** — 50 most recent events globally
   - **Specific location** — e.g. `books/Bible/KJV`
2. **Filter** — client-side substring match across all fields
3. **API Search** — server-side `GET /api/v2/search?q=...`

```bash
# Latest 50 events
curl "https://api.indb.tech/api/v2/events?limit=50"

# By location
curl "https://api.indb.tech/api/v2/events?limit=50&filter_key=location&filter_value=books/Orwell/1984"

# Search
curl "https://api.indb.tech/api/v2/search?q=1984&limit=20"
```

Fused events show **⚡** in the ID column (`fusion_count > 0` or `is_fused`).

---

## Scripts (TUI only)

Read-only scripts; output streams to the log. **Copy log** is bottom-right on every log panel.

| Button | Script | What it does |
|--------|--------|--------------|
| 🩺 Integrity Check | `tests/integrity_check.py` | 7-point startup integrity |
| 🔍 Explore DB | `scripts/explore_db.py` | Interactive corpus browse |
| 🛡️ Audit Protocols | `scripts/audit_protocols.py` | Transport layer audit |
| 📊 Analyze Sources | `scripts/analyze_books.py` | Analytics per source/location |
| 💬 Query Examples | `scripts/query_examples.py` | Live search + interpret demos |
| 🦉 Hermes Integration | `scripts/test_hermes_integration.sh` | MCP connector smoke test |

Run manually:

```bash
cd db
INDB_API_URL=https://api.indb.tech python3 scripts/query_examples.py
```

---

## Configuration

| Variable | Default | Applies to |
|----------|---------|------------|
| `INDB_API_URL` | `https://api.indb.tech` (TUI) / same-origin (WUI) | API base |
| `INDB_CLUSTER_NODES` | configured API only | Cluster tab extra nodes |
| `INDB_IN_DOCKER` | `false` | TUI: hides Run Tests / Audit / Restart |
| `VITE_INDB_API_URL` | — | WUI build-time API default |
| Browser `localStorage.indb_api_url` | — | WUI runtime override |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Server: Down** / empty stats | Check API URL, `curl $INDB_API_URL/health` |
| **TUI picker crash (PickerOverlay)** | Kill old process; use `./start_tui.sh`; verify build `2026-07-11e` |
| **WUI 404 at /wui/** | Run `cd db/wui && npm run build` |
| **CORS errors** (WUI dev on :5174) | Use Vite proxy (default) or serve from same origin |
| **Interpret HTTP 500** | Known server-side issue in some builds — try Search or Prism instead |
| **Empty Events** | Production may be warming up; try **All sources** or run Query Examples script |

---

## Further reading

- [CLI & TUI (detailed)](./cli.md)
- [Web Console / WUI (detailed)](./wui.md)
- [Query Cookbook](./QUERY_COOKBOOK.md) — curl recipes + JSON samples
- [API Reference](./API.md)
- [Hermes scenarios](./HERMES_INTEGRATION_SCENARIOS.md)
