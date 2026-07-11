# Web Console (WUI)

The **INDB Web Console (WUI)** is a browser dashboard — a Vue 3 SPA that mirrors the TUI feature set. Use it for daily operations, demos, and Query Lab without installing Textual.

- **Production:** [https://api.indb.tech/wui/](https://api.indb.tech/wui/)
- **Local API:** [http://localhost:8000/wui/](http://localhost:8000/wui/) (after `npm run build`)

Terminal equivalent: [CLI & TUI](./cli.md) · Combined guide: [Console Guide](./CONSOLE.md).

---

## Architecture

```
Browser  →  /wui/  (FastAPI StaticFiles)
              ↓ fetch
         /health, /api/v2/*, /raft/status
              ↓
         INDB API (same origin or configured URL)
```

WUI is **read/query only** — it does not run local subprocesses (no Scripts tab). Use TUI or CLI for script execution.

---

## Quick start

### Use production (zero setup)

Open [https://api.indb.tech/wui/](https://api.indb.tech/wui/).  
Leave the API URL field **empty** — the console uses the same origin.

### Local development (hot reload)

```bash
cd db/wui
npm install
npm run dev
```

Open [http://localhost:5174/wui/](http://localhost:5174/wui/).  
Vite proxies API calls to `https://api.indb.tech` by default. Override:

```bash
INDB_API_URL=http://localhost:8888 npm run dev
```

### Production build (served by FastAPI)

```bash
cd db/wui
npm install
npm run build
```

Requires `db/wui/dist/` — mounted automatically by `core/app_factory.py` at `/wui/`.

Restart API server, then open `http://localhost:8000/wui/`.

---

## Interface overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [IN] INDB Console          API URL [________] [Connect] [Refresh]      │
│ WUI 2026-07-11 · 12:34:56                                               │
│ ◉Control  ≡Events  ⬡Modules  ◎Cluster  ⌁Query  ◈Analytics              │
├─────────────────────────────────────────────────────────────────────────┤
│  [ tab content — cards, tables, query form, JSON output ]               │
├─────────────────────────────────────────────────────────────────────────┤
│  INDB Web Console · API Docs                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Visual language:** dark INDB theme (`#0a0a0a` background, `#e63329` accent, IBM Plex).  
**Dropdowns** show a red **▾** arrow on the **left** to distinguish them from text inputs.

---

## Header controls

| Control | Purpose |
|---------|---------|
| **API URL** | Base URL for all requests. Empty = current page origin. Saved to `localStorage.indb_api_url`. |
| **Connect** | Apply URL and reload data |
| **Refresh** | Manual full refresh |
| Loading indicator | Yellow pulse + phase message during fetch |

Auto-refresh: every **5 seconds** for Control stats and the active data tab.

---

## Tab — Control

**Purpose:** System health at a glance — same role as TUI Control.

| Stat card | Source |
|-----------|--------|
| Events | `analytics/overview` → `database.total_events` |
| Fusion | fusion compression / fusion rate % |
| Server | `/health` |

Below: optional CPU/RAM line from `system_health`.

**System log** panel with **Copy log** (bottom-right): connection messages, API errors, refresh timestamps.

**When to use:** First tab after opening WUI. If Server shows Down, fix API URL before other tabs.

---

## Tab — Events

**Purpose:** Browse live memory — events table with filtering and server search.

| Control | Behavior |
|---------|----------|
| **▾ Source** | All sources (mixed per top location), Latest, or specific location |
| **Filter** | Client-side substring filter |
| **Reload** | Re-fetch from API |
| **API Search** | `GET /api/v2/search?q=...` |

| Column | Description |
|--------|-------------|
| ID | Short id; ⚡ prefix if fused |
| Time | Formatted timestamp |
| Location | Source path |
| Content | Token anchor preview |

### Example

1. Source: **All sources**
2. Filter: `1984` → **API Search**
3. Note an event ID for Query → Echo

```bash
curl "https://api.indb.tech/api/v2/events?limit=50&filter_key=location&filter_value=books/Orwell/1984"
```

---

## Tab — Modules

**Purpose:** Connector health and transport protocols.

**Source Connectors** — `GET /api/v2/modules`

**Active Protocols** — `GET /api/v2/system/protocols`

Status colors: green = running, yellow = warning, red = error/disabled.

---

## Tab — Cluster

**Purpose:** Endpoint and Raft status.

Polls each node from `VITE_INDB_CLUSTER_NODES` (build time) or the configured API URL.

| Column | Meaning |
|--------|---------|
| Endpoint | Node name / hostname |
| Status | UP / DOWN badge |
| Port | 443, 8000, … |
| Raft | Leader ★ or role |
| Term | Raft term |

---

## Tab — Query

**Purpose:** **Query Lab** — full cognitive API without curl.

### Form layout

```
[ ▾ Mode        ] [ Primary input……… ] [ Secondary… ] [ Tertiary… ] [ Run ]
Hint: required fields for selected mode
```

### All modes

Same as TUI — see [Console Guide — Query Lab](./CONSOLE.md#query-lab--all-modes-with-examples).

| Mode | Primary example |
|------|-----------------|
| Interpret (Exhale) | `Neutral \| books/Orwell/1984` |
| Prism Synthesize | `would have died` |
| Prism Instinct | `query \| 0.8` |
| Lens Query | `recent \| historical` |
| Echo Resonate | `<uuid>` |
| Deduction | `birthday cheese` |
| What-If | `whale \| captain` |
| Context Slice | `lord \| holy` |
| Paradox Create | sources in Primary; modes in Secondary/Tertiary |
| Paradox Read | paradox UUID |
| Recovery Identity | key_id |

Click **Run** or press Enter in Primary. JSON output below with **Copy log**.

---

## Tab — Analytics

**Purpose:** Extended metrics and raw JSON dumps.

| Stat | Source |
|------|--------|
| Health | overview health score |
| Locations | unique location count |
| Tokens | token statistics |
| Fusion Rate | fusion metrics |
| WS Clients | websocket stats |

**Insights** — top bullets from `/api/v2/analytics/insights`.

**Output** — formatted JSON: Database, Fusion, Temporal, Performance, Cognitive, WebSocket.

---

## Configuration

| Setting | Where | Purpose |
|---------|-------|---------|
| `VITE_INDB_API_URL` | Build-time `.env` | Default API when not same-origin |
| `VITE_INDB_CLUSTER_NODES` | Build-time | Comma-separated cluster URLs |
| `localStorage.indb_api_url` | Browser | Runtime API override (Connect button) |
| `INDB_API_URL` | `npm run dev` env | Vite dev proxy target |

### Example `.env` for local cluster dev

```bash
# db/wui/.env
VITE_INDB_API_URL=http://localhost:8888
```

---

## WUI vs TUI

| Feature | WUI | TUI |
|---------|-----|-----|
| Control / Events / Modules / Cluster / Query / Analytics | ✅ | ✅ |
| Scripts runner | ❌ | ✅ |
| Run Tests / Audit / Restart | ❌ | ✅ (local) |
| Copy log | ✅ button | ✅ button + `y` |
| Works over SSH | ❌ | ✅ |
| Shareable URL | ✅ `/wui/` | ❌ |
| Dropdown UX | Native `<select>` + ▾ | Textual inline picker |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Blank page at `/wui/` | Run `cd db/wui && npm run build` |
| CORS in dev | Use `npm run dev` (proxy), not `file://` |
| All stats `—` | Click Connect with valid API URL |
| 404 on API calls | Check URL has no trailing path; use base only |
| Stale UI after deploy | Hard refresh (Cmd+Shift+R) |

---

## Development

```bash
cd db/wui
npm install
npm run dev      # dev server
npm run build    # dist/ for FastAPI
npm run preview  # preview production build
```

Source: `db/wui/src/` — Vue 3 + TypeScript + Tailwind.

---

## Related

- [Console Guide](./CONSOLE.md)
- [CLI & TUI](./cli.md)
- [Query Cookbook](./QUERY_COOKBOOK.md)
- [API Reference](./API.md)
