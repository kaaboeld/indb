# CLI & TUI Guide

The **INDB Terminal User Interface (TUI)** is a full-screen dashboard built with [Textual](https://textual.textualize.io/). It connects to a live INDB API (production or local cluster) and provides monitoring, event inspection, cognitive queries, and one-click scripts.

For the browser equivalent, see [Web Console (WUI)](./wui.md).  
Overview of both: [Console Guide](./CONSOLE.md).

---

## Starting the TUI

Always launch from the **`db/`** directory using the helper script (clears stale Python cache):

```bash
cd db
./start_tui.sh
```

Alternative:

```bash
cd db
python3 -m cli.tui.app
```

### API endpoints

| Target | Command |
|--------|---------|
| **Production** (default) | `./start_tui.sh` |
| **Production explicit** | `INDB_API_URL=https://api.indb.tech ./start_tui.sh` |
| **Local load balancer** | `INDB_API_URL=http://localhost:8888 ./start_tui.sh` |
| **Single node** | `INDB_API_URL=http://localhost:8000 ./start_tui.sh` |

The TUI loads `.env` from `db/` via `python-dotenv`. Production is the default when `INDB_API_URL` is unset.

### Docker

```bash
docker compose --profile tools run --rm tui
```

In Docker (`INDB_IN_DOCKER=true`), the **Run Tests / Run Audit / Restart** buttons on Control are hidden.

### Verify correct version

On startup, stderr shows:

```
picker=inline-dropdown-v2 widgets=.../db/cli/tui/widgets.py
INDB TUI 2026-07-11e
```

The Control log must contain:

```
TUI build 2026-07-11e picker=inline-dropdown-v2
```

If you see `PickerOverlay` errors, kill old processes (`pkill -f cli.tui.app`) and restart with `./start_tui.sh`.

---

## Interface layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  INDB                          https://api.indb.tech · clock             │
│  [████████░░░░] Loading Events…                                          │  ← loading bar
├──────────────────────────────────────────────────────────────────────────┤
│ Control │ Events │ Modules │ Cluster │ Query │ Analytics │ Scripts       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                     [ active tab content ]                               │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│  q Quit   r Refresh   e Events   m Modules   p Query   a Analytics  …    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Tab 1 — Control

**Purpose:** Answer “is INDB up and healthy?” in one glance. This is the home tab.

### Stats bar (refreshes ~every 3–5 s)

| Card | Meaning | API source |
|------|---------|------------|
| **Events** | Total events in memory | `GET /api/v2/analytics/overview` → `database.total_events` |
| **Fusion %** | Semantic compression rate | `performance.fusion_compression_rate` or `fusion.fusion_rate` |
| **Server** | `Running` / `Down` | `GET /health` → `status: ok` |

### System log

Scrollable, selectable log (mouse + Cmd/Ctrl+C, or **Copy log** bottom-right, or `y`):

- Startup build id and API URL
- Connection note when API is probed
- Periodic CPU % and RAM from `system_health`
- Output from Run Tests / Run Audit / Restart

### Control actions (local mode only)

| Button | Action |
|--------|--------|
| **Run Tests** | `pytest tests/unit -v --tb=short` |
| **Run Audit** | `./run_audit.sh` or `scripts/audit_protocols.py` |
| **Restart** | `./start.sh` in background |

Hidden when `INDB_IN_DOCKER=true`.

---

## Tab 2 — Events

**Purpose:** See what INDB remembers — raw event stream with search.

### Toolbar (one row)

| Control | Action |
|---------|--------|
| **Source ▾** | `All sources` (mixed per location), `Latest`, or a specific book/location |
| **Filter** | Client-side filter; press Enter or **Filter** |
| **API Search** | `GET /api/v2/search?q=...` server-side |

### Table columns

| Column | Description |
|--------|-------------|
| **ID** | Short UUID; **⚡** = fused event |
| **Time** | Local `HH:MM:SS` |
| **Location** | e.g. `books/Orwell/1984` |
| **Content** | Token anchor text (truncated) |

### Example workflow

1. Open Events → source **All sources**
2. Type `kjv` in filter → **API Search**
3. Copy an event ID → switch to **Query** → Echo Resonate

---

## Tab 3 — Modules

**Purpose:** Monitor ingest connectors and system protocols.

### Source connectors

`GET /api/v2/modules` — polled on refresh.

| Column | Meaning |
|--------|---------|
| **Module** | Connector name (`hermes`, `moltbook`, …) |
| **Enabled** | ✓ / ✗ |
| **Status** | `running`, `no_api_key`, `disabled`, `error` |
| **API Key** | ✓ / ✗ / — |

### Active protocols

`GET /api/v2/system/protocols` — HTTP, gRPC, UDP, WebSocket, etc.

**Shortcut:** `m` → Modules tab.

---

## Tab 4 — Cluster

**Purpose:** Check API reachability and Raft role for configured endpoints.

Polls `/health` and `/raft/status` per node from `INDB_CLUSTER_NODES` or the main API URL.

| Column | Meaning |
|--------|---------|
| **Endpoint** | Host label |
| **Status** | UP / DOWN |
| **Port** | 443, 8000, … |
| **Raft** | Leader (★) or Follower |
| **Term** | Current Raft term |

Summary line: `Endpoints N/M up · Raft <status>`

---

## Tab 5 — Query

**Purpose:** Interactive **Query Lab** — run cognitive API calls without curl.

### Toolbar

| Control | Role |
|---------|------|
| **Mode ▾** | Dropdown with ▾ marker (inline overlay, not modal) |
| **Primary** | Main input; use `\|` for compound values |
| **Secondary** | Optional second parameter |
| **Tertiary** | Third parameter (paradox modes) |
| **Run** | Execute query |
| Hint line | Required fields for selected mode |

### Modes and examples

| Mode | Primary example | Notes |
|------|-----------------|-------|
| **Interpret** | `Neutral \| books/Bible/KJV \| peace` | mood \| location [\| goal] |
| **Prism Synthesize** | `would have died` | text or event UUID |
| **Prism Instinct** | `query text \| 0.7` | adrenaline 0.0–1.0 |
| **Lens Query** | `recent \| historical` | context_a \| context_b |
| **Echo Resonate** | `<event-uuid>` | seed from Events tab |
| **Deduction** | `birthday cheese` | evidence text |
| **What-If** | `whale \| captain` | base \| modifier |
| **Context Slice** | `lord \| holy` | query \| modifier |
| **Paradox Create** | `id1,id2` | Secondary=generation_mode, Tertiary=collapse_mode |
| **Paradox Read** | `<paradox-uuid>` | |
| **Recovery Identity** | `<key_id sha256>` | |

Press **Enter** in Primary or Secondary to run.

Output appears in the log below with **Copy log** (bottom-right).

**Shortcut:** `p` → Query tab.

See [Console Guide — Query Lab](./CONSOLE.md#query-lab--all-modes-with-examples) for curl equivalents.

---

## Tab 6 — Analytics

**Purpose:** Deep system analytics beyond the Control summary.

### Stats

| Card | Source |
|------|--------|
| Health | `health_score` |
| Locations | `database.unique_locations` |
| Tokens | `tokens.unique_tokens` |
| Fusion Rate | fusion metrics |
| WS Clients | `websocket/stats` |

### Insights

Bullet list from `GET /api/v2/analytics/insights`.

### Detail log

JSON sections: Database, Fusion, Temporal, Performance, Cognitive, WebSocket.

**Shortcut:** `a` → Analytics tab.

---

## Tab 7 — Scripts

**Purpose:** Run maintenance/diagnostic scripts against the live API. stdout/stderr stream line-by-line into the log.

| Button | Script |
|--------|--------|
| 🩺 Integrity Check | `tests/integrity_check.py` |
| 🔍 Explore DB | `scripts/explore_db.py` |
| 🛡️ Audit Protocols | `scripts/audit_protocols.py` |
| 📊 Analyze Sources | `scripts/analyze_books.py` |
| 💬 Query Examples | `scripts/query_examples.py` |
| 🦉 Hermes Integration | `scripts/test_hermes_integration.sh` |

Scripts receive `INDB_API_URL` from the TUI config. Only one script runs at a time.

**Shortcut:** `s` → Scripts tab.

---

## Key bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh all pollable tabs |
| `1`–`7` | Jump to tab by number |
| `e` | Events |
| `m` | Modules |
| `p` | Query |
| `a` | Analytics |
| `s` | Scripts |
| `y` | Copy log (when log focused) |

`Ctrl+C` is **not** bound to quit (so copy works).

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `INDB_API_URL` | `https://api.indb.tech` | API base URL |
| `INDB_CLUSTER_NODES` | — | Comma-separated URLs for Cluster tab |
| `INDB_IN_DOCKER` | `false` | Hides local control buttons |
| `INDB_VERSION` | `0.11.1` | Shown in header |

---

## CLI entry point

```bash
cd db
python3 -m cli.indb_cli tui
python3 -m cli.indb_cli tui --api https://api.indb.tech
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Server: Down` | Check `curl $INDB_API_URL/health` |
| Empty Events | Try **All sources**; verify production has data |
| Dropdown crash (`PickerOverlay`) | Stale process — `pkill -f cli.tui.app`; `./start_tui.sh` |
| Log one long line | Fixed in build `2026-07-11e` — restart TUI |
| Vertical lines on inputs | Fixed — flat `solid` borders in app CSS |
| Script stuck | Wait for `Done (Exit N)`; scripts cannot be cancelled |

---

## Related docs

- [Console Guide (TUI + WUI)](./CONSOLE.md)
- [WUI Guide](./wui.md)
- [Query Cookbook](./QUERY_COOKBOOK.md)
