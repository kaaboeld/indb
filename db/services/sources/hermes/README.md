# Hermes Integration

Source connector that ingests [Hermes Agent](https://hermes-agent.nousresearch.com/) activity into INDB.

**Hermes is a module** — pluggable like any other. INDB works with or without Hermes. Enable/disable via `HERMES_ENABLED`; core (REST, fusion, interpret, search) is unaffected.

## Two integration paths

### 1. MCP (primary) — Hermes uses INDB as memory

Hermes connects to INDB's MCP server and gets tools: `query_events`, `ingest_event`, `get_stats`.

Configure Hermes to use INDB MCP:

```yaml
# ~/.hermes/config.yaml or hermes config set
mcp_servers:
  indb:
    url: http://localhost:8000/api/v2/mcp/sse
```

When INDB runs in Docker, use `http://host.docker.internal:8000/api/v2/mcp/sse` or the host IP.

### 2. Source connector — INDB ingests Hermes sessions

This connector polls Hermes session and memory files, transforming agent conversations into INDB Events.

**Local (INDB on host):**

- Default paths: `~/.hermes/sessions`, `~/.hermes/memories`
- Set `HERMES_ENABLED=true` in `.env`

**Docker:**

- Mount `~/.hermes:/hermes:ro` (already in `docker-compose.yml`)
- `HERMES_SESSIONS_PATH=/hermes/sessions`, `HERMES_MEMORIES_PATH=/hermes/memories`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ENABLED` | `true` | Enable/disable connector |
| `HERMES_SESSIONS_PATH` | `~/.hermes/sessions` | Poll session JSON files |
| `HERMES_MEMORIES_PATH` | `~/.hermes/memories` | Poll MEMORY.md, USER.md |
| `HERMES_POLL_INTERVAL` | `60` | Seconds between polls |
| `HERMES_DEDUPE_WINDOW` | `5000` | Rolling dedup window |

## Verification

```bash
# Events from Hermes have location hermes://...
curl -s "http://localhost:8000/api/v2/events?limit=10" | jq '.[] | select(.location | startswith("hermes"))'
```
