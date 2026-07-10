# Hermes ↔ INDB: Input and Output

Hermes is the agent at input and output: receives raw data, processes it, writes to INDB; answers abstract queries by reading from INDB.

**Hermes is a module** — pluggable like moltbook and others. The system works when Hermes is connected or disconnected. With Hermes disabled, core INDB (REST ingest, fusion, interpret, search, echo, prism) works unchanged.

## Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hermes Agent                              │
│  (Ollama / local model)                                          │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
        MCP tools                             │
                │                             │
                ▼                             ▼
┌───────────────────────────────────────────────────────────────────┐
│                         INDB                                       │
│  ingest_event  ←  write facts      query_events  →  read          │
│  get_stats     ←  statistics                                      │
└───────────────────────────────────────────────────────────────────┘
                ▲                             │
                │                             │
        HermesConnector                       │
        (poll ~/.hermes/sessions)             │
                │                             │
                └─────────────────────────────┘
                    Hermes sessions → INDB
```

## 1. Setup (one-time)

```bash
cd backend
./scripts/setup_hermes_indb.sh
```

Adds INDB MCP to `~/.hermes/config.yaml`. Restart Hermes or send `/reload-mcp` in chat.

## 2. Input: Hermes collects data and writes to INDB

**Via MCP ingest_event** — Hermes decides what and how to write:

```
Find a brief definition of epistemology on the web and save it to INDB
via MCP tool ingest_event. location: hermes://fetch/epistemology
```

```
Read the Wikipedia article on Raft consensus and write key points
to INDB via ingest_event. location: hermes://wikipedia/raft
```

**Via HermesConnector** — any Hermes dialog is saved to `~/.hermes/sessions/`, INDB polls and ingests. Just chat:

```bash
hermes chat
```

```
Tell me about the paradox of perception and how INDB preserves it
```

The session will reach INDB via the connector (poll every 60s).

## 3. Output: Hermes answers abstract queries from INDB

```
Use mcp_indb_query_events to find all events about epistemology and memory.
Summarize what you found.
```

```
What do we know about misinformation and gaslighting in the database? Use INDB.
```

```
Show INDB statistics via get_stats
```

## 4. Full cycle (non-interactive)

```bash
# Hermes (MCP)
hermes chat -Q -q "Fetch a short definition of collective memory from web. Store it in INDB via ingest_event: content='tokens from definition', location='hermes://fetch/collective-memory'"
hermes chat -Q -q "Use mcp_indb_query_events with filter_key=memory and filter_value= to find events about memory. Summarize what you found."

# REST fallback (if MCP unavailable)
./scripts/hermes_indb_cycle.sh rest   # 5 requests: ingest→query→ingest→query→stats
```

## MCP Tools

| Tool | Purpose |
|------|----------|
| `mcp_indb_ingest_event` | Write fact: content (space-separated tokens), location |
| `mcp_indb_query_events` | Search: filter_key=location + filter_value, or filter_key=word for content search |
| `mcp_indb_get_stats` | Database statistics |

## Requirements

- INDB: `http://localhost:8888` (HAProxy) or `http://localhost:8000` (standalone)
- Hermes: `pip install hermes-agent[mcp]`
- Ollama: running for local model
