# CLI & TUI Guide

INDB ships with a full-featured **Terminal User Interface** built on [Textual](https://textual.textualize.io/).
It provides real-time monitoring, event search, modules status (hermes, moltbook), cluster status, and one-click script execution — all from the terminal.

---

## Starting the TUI

### Local run

Run from the **backend** directory. Activate the virtual environment and ensure `.env` is loaded (the TUI uses `python-dotenv` automatically).

```bash
cd backend
source venv/bin/activate
python -m cli.tui.app

# With explicit API URL (cluster via load balancer)
INDB_API_URL=http://localhost:8888 python -m cli.tui.app

# Or direct to node-1 (standalone)
INDB_API_URL=http://localhost:8000 python -m cli.tui.app
```

Alternative launcher: `python cli/tui/launch.py`

### Docker mode

```bash
# Start TUI container (connects to the cluster via the internal Docker network)
docker compose --profile tools run --rm tui
```

In Docker mode the **Control Panel** (Restart / Run Tests / Run Audit buttons) is hidden — use scripts instead.

---

## Interface Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  INDB v1.2.0                   http://localhost:8888                │  ← Header
├──────────┬──────────┬──────────┬──────────────┬────────────────────┤
│ Control  │  Events  │ Modules  │ Load Balancer│  Scripts            │  ← Tabs
├──────────┴──────────┴──────────┴──────────────┴────────────────────┤
│                                                         │
│             [Tab content area]                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  q Quit   r Refresh   m Modules   s Scripts              │  ← Footer
└─────────────────────────────────────────────────────────┘
```

---

## Tab 1 — Control

The default view. Shows live system stats and a scrolling system log.

### Stats Bar

Three real-time counters updated every 3 seconds by polling `/api/v2/analytics/overview`:

| Widget | Value | Source |
|---|---|---|
| **Events** | Total event count in memory | `database.total_events` |
| **Fusion %** | Fusion compression rate | `performance.fusion_compression_rate` |
| **Server** | `Running` / `Stopped` / `Error` | `/health` endpoint |

### System Log

A live scrolling log showing:
- Console startup timestamp
- CPU % and RAM (MB) polled every 5 seconds from `system_health`
- Output from Control Panel button actions (tests, audit, restart)

### Control Panel (standalone mode only)

Three action buttons — only visible when **not** running in Docker:

| Button | Action |
|---|---|
| **Run Tests** | Runs `pytest tests/unit -v` and streams output to the log |
| **Run Audit** | Runs `./run_audit.sh` |
| **Restart** | Launches `./start.sh` in the background |

---

## Tab 2 — Events

Live searchable table of all events in memory.

### Search Bar

Type a query and press **Enter** or click **Search**. Client-side filter — searches across all event fields (location, tokens, ID, timestamp).

```
[ Search events (e.g. jerusalem)...   ] [Search]
```

### Events Table

| Column | Width | Content |
|---|---|---|
| **ID** | 12 | First 8 chars of UUID. `⚡` prefix = fused event |
| **Time** | 10 | `HH:MM:SS` from event timestamp |
| **Location** | 20 | Event location (truncated to 15 chars) |
| **Content** | 60 | First token, or `event:`/`quote:` prefix stripped |

The table fetches the latest 50 events from `GET /api/v2/events?limit=50` and refreshes every 3 seconds. While typing a filter, results update immediately on Enter.

**Fused events** (`fusion_count > 0`) are marked with `⚡` in the ID column.

---

## Tab 3 — Modules

Source connector modules (hermes, moltbook, etc.) and their status.

### Module Table

Polls `/api/v2/modules` every 3 seconds:

| Column | Content |
|---|---|
| **Module** | `hermes`, `moltbook`, etc. |
| **Enabled** | ✓ / ✗ |
| **Status** | 🟢 running, 🟡 no_api_key, ⚪ disabled, 🔴 error |
| **API Key** | ✓ / ✗ / — (if not required) |

**Shortcut:** Press `m` to jump to the Modules tab.

---

## Tab 4 — Load Balancer

Real-time Raft cluster status across all 3 nodes.

### Node Table

Polls `/health` and `/raft/status` on each node every 3 seconds:

| Column | Content |
|---|---|
| **Node** | `node-1`, `node-2`, `node-3` |
| **Status** | `✅ UP` / `❌ DOWN` / `⚠️ ERROR` |
| **Port** | External port (`8000`, `8004`, `8005`) |
| **Role** | `👑 LEADER` or `Follower` (from Raft state) |

### Cluster Health Summary

```
Active Nodes: 3/3 | Strategy: Round-Robin
```

Shows how many nodes are currently healthy and the load balancing strategy (HAProxy round-robin).

---

## Tab 5 — Scripts

One-click access to all operational scripts. Output streams live into the embedded log.

### Script Buttons

| Button | Script | Purpose |
|---|---|---|
| 🩺 **Integrity Check** | `tests/integrity_check.py` | 7-point startup integrity test |
| 🔍 **Explore DB** | `scripts/explore_db.py` | Browse events interactively |
| 📡 **Verify Cluster** | `scripts/verify_cluster.py` | Check all 3 Raft nodes |
| 🛡️ **Audit Protocols** | `scripts/audit_protocols.py` | Test all 6 transports |
| 📚 **Analyze Books** | `scripts/analyze_books.py` | Run book corpus analysis |
| 💬 **Query Examples** | `scripts/query_examples.py` | Demonstrate API queries |
| 📥 **Load 5k Events** | `scripts/load_5000_events.py` | Seed 5000 test events |
| 🦉 **Hermes Integration** | `scripts/test_hermes_integration.sh` | Test Hermes MCP and connector |

### Output Log

Script stdout and stderr stream line-by-line into the **Output** log area below the buttons. Both stdout and stderr are shown, with `[ERR]` prefix on stderr lines.

```
[08:15:32] ▶  🩺 Integrity Check
────────────────────────────────────────────────────────────
  INFO  indb.integrity  ✓  INDB initialises  (20 events in memory)
  INFO  indb.integrity  ✓  Storage loads without error  (20 raw items)
  ...
  INFO  indb.integrity  Result: 7/7 checks passed in 4212ms
[08:15:36] Done (Exit 0)
```

---

## Key Bindings

| Key | Action |
|---|---|
| `q` | Quit the TUI |
| `r` | Force refresh (re-poll all widgets) |
| `m` | Jump to the **Modules** tab |
| `s` | Jump to the **Scripts** tab |

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `INDB_API_URL` | `http://localhost:8888` | API endpoint (load balancer or single node) |
| `INDB_IN_DOCKER` | `false` | Hides Control Panel in Docker deployments |

The TUI loads `.env` from the project root automatically on startup (via `python-dotenv`).

---

## Troubleshooting

**`Server: Stopped`** in the stats bar
: The TUI cannot reach `INDB_API_URL/health`. Check that the server is running and the URL is correct.

**Empty Events table**
: No events in the database yet. Run `python scripts/load_books.py` or click **Load 5k Events** in the Scripts tab.

**All nodes show `❌ DOWN`**
: The cluster is not running. Use `docker compose up -d` or `./start.sh` to bring it up.

**Script output stuck**
: The script is long-running. Wait for `Done (Exit 0)` or restart the TUI. Scripts run as async subprocesses and cannot be cancelled mid-run.
