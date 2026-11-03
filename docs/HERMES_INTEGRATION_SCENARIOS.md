# INDB + Hermes — Integration Test Scenarios

## Context

**INDB** — epistemological engine. Stores events, signs every response with Ed25519, handles paradoxes via Prism. Runs as Raft cluster.

**Hermes** — autonomous AI agent. Works with Ollama (`qwen3-coder-next` at `http://localhost:11434`). Sessions in `~/.hermes/sessions/`, memory in `~/.hermes/memories/`.

**Bridge between them — two channels:**

- **MCP** — Hermes calls INDB tools (`query_events`, `ingest_event`, `get_stats`)
- **Source Connector** — INDB polls Hermes sessions and ingests as events

**Addresses:**

| Service | URL |
|---------|-----|
| INDB API (loadbalancer) | http://localhost:8888 |
| INDB node-1 (direct) | http://localhost:8000 |
| Ollama | http://localhost:11434 |
| MCP SSE endpoint | http://localhost:8888/api/v2/mcp/sse |
| TUI | `INDB_API_URL=http://localhost:8888 python -m cli.tui.app` |

---

## Scenario 1 — Basic ping: Hermes sees INDB

**Purpose:** Verify Hermes can reach INDB via REST and get a meaningful response. Zero level — no MCP, no connector, just HTTP.

**Command:**
```bash
hermes
```

**Chat input:**
```
Make a GET request to http://localhost:8888/health and tell me what the server returned
```

**Expected:**
```json
{"status": "ok", "version": "0.11.1"}
```

Hermes reads the response and explains it. Confirms: agent sees the network, INDB is alive.

---

## Scenario 2 — Hermes ingests event via REST

**Purpose:** Hermes via terminal tool runs curl and writes an event to INDB. Test without MCP — pure REST channel check.

**Chat input:**
```
Write an event to INDB: POST to http://localhost:8888/api/v2/events
Body:
{
  "raw_data_anchor": ["hermes", "test", "integration", "scenario-2"],
  "location": "hermes://test/scenario-2"
}
```

**Expected:**
```json
{"data": {"id": "...", "location": "hermes://test/scenario-2", ...}, "status": "success"}
```

**Verify after:**
```bash
curl -s "http://localhost:8888/api/v2/events?limit=10" | python3 -m json.tool | grep scenario-2
```

---

## Scenario 3 — MCP: Hermes calls `get_stats`

**Purpose:** First Hermes call to INDB via MCP protocol. Simplest tool with no args — verify MCP stack is alive.

**Setup (if not done):**
```bash
hermes config set CUSTOM_MCP_SERVERS '{"indb": {"url": "http://localhost:8888/api/v2/mcp/sse"}}'
```

**Chat input:**
```
Use MCP tool get_stats from INDB and show me the database statistics
```

**Expected:** Hermes calls `get_stats` and returns JSON with `total_events`, `version` and other metrics. If response received — MCP channel works.

---

## Scenario 4 — MCP: full cycle `ingest_event` + `query_events`

**Purpose:** Hermes writes a fact to INDB, then reads it back. Verifies bidirectionality via MCP: write → store → read.

**Chat input:**
```
Using MCP INDB do two steps:
1. Write an event via ingest_event: content="epistemology paradox memory truth", location="hermes://mcp/test"
2. Then run query_events with filter_value="hermes" and show what was found
```

**Expected:**
- `ingest_event` returns `id` of new event
- `query_events` finds the just-written event
- Hermes comments on the result meaningfully

---

## Scenario 5 — Source Connector: INDB reads Hermes session

**Purpose:** Hermes writes dialog → saves session → INDB polls `~/.hermes/sessions/` and ingests content. Verifies autonomous connector channel.

**Steps:**

1. Conduct dialog with Hermes:
```bash
hermes
```
```
Tell me about the paradox of perception and why INDB preserves it
```
End session: `Ctrl+D` or `/exit`

2. Verify file was created:
```bash
ls ~/.hermes/sessions/
```

3. Wait 60 seconds (poll_interval) and check events in INDB:
```bash
curl -s "http://localhost:8888/api/v2/events?limit=50" | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']
hermes_events = [e for e in data if e.get('location','').startswith('hermes')]
print(f'Hermes events: {len(hermes_events)}')
for e in hermes_events[:3]:
    print(e['location'], e['raw_data_anchor'][:3])
"
```

**Expected:** Events with `location: hermes://user/...` and `hermes://assistant/...`.

---

## Scenario 6 — Prism: paradox from two Hermes claims

**Purpose:** Hermes ingests two contradictory claims. INDB via Prism returns `is_paradoxical: true` and `alternative_readings`. Verifies INDB does not pick one opinion — stores both.

**Ingest two events:**
```bash
curl -X POST http://localhost:8888/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["hermes", "says", "memory", "is", "permanent", "truth"], "location": "hermes://claim/1"}'

curl -X POST http://localhost:8888/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["hermes", "says", "memory", "is", "ephemeral", "illusion"], "location": "hermes://claim/2"}'
```

**Prism request:**
```bash
curl -X POST http://localhost:8888/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "hermes memory truth illusion permanent ephemeral"}'
```

**Expected:**
```json
{
  "is_paradoxical": true,
  "perception_gap": 0.4,
  "alternative_readings": [...]
}
```

---

## Scenario 7 — Echo: Hermes finds resonance with old events

**Purpose:** Echo — semantic search by token resonance. After events accumulate (scenarios 2–5), verify similar queries find similar facts.

**Via Hermes:**
```
Use MCP query_events to find all events in INDB related to memory and truth.
Use filter_value="hermes" and limit=20
```

**Direct Echo request:**
```bash
curl -X POST http://localhost:8888/api/v2/echo/resonate \
  -H "Content-Type: application/json" \
  -d '{"query_tokens": ["hermes", "memory", "truth", "integration"], "limit": 10}'
```

**Expected:** List of events sorted by `score`. Closest by tokens — at top.

---

## Scenario 8 — Blind Payload: Hermes stores a secret

**Purpose:** Hermes ingests event with encrypted `blind_payload`. INDB stores presence of fact but never reads content. Verifies Black Box contract: «you may hide what. You may not hide that something was».

**Request:**
```bash
curl -X POST http://localhost:8888/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data_anchor": ["hermes", "secret", "private", "key"],
    "location": "hermes://secrets/private-key",
    "blind_payload": "ENCRYPTED:this_is_hermess_private_key_that_indb_never_reads"
  }'
```

**Verify:**
```bash
curl -s "http://localhost:8888/api/v2/events?limit=50" | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']
for e in data:
    if e.get('blind_payload'):
        print('blind_payload present:', bool(e['blind_payload']))
        print('location:', e['location'])
        print('anchor:', e['raw_data_anchor'])
        break
"
```

**Expected:** Event recorded by `location` and `raw_data_anchor`. Field `blind_payload` present but content hidden — engine does not interpret it.

---

## Scenario 9 — TUI: full picture in real time

**Purpose:** While running scenarios 1–8, TUI shows live statistics. Verifies entire pipeline is visible from inside.

**Run in parallel:**
```bash
cd backend
INDB_API_URL=http://localhost:8888 python -m cli.tui.app
```

**What to watch:**

| Tab | What should be visible |
|-----|-------------------------|
| **Control** | Events: counter grows after each ingest |
| **Modules** | `hermes` — 🟢 running · `moltbook` — 🟡 no_api_key |
| **Events** | Rows with `location: hermes://...` |
| **Load Balancer** | node-1 — 👑 LEADER · node-2/3 — ✅ UP |

---

## Quick sanity check

```bash
# Health
curl -s http://localhost:8888/health | python3 -c "import json,sys; d=json.load(sys.stdin); print('status:', d.get('status'))"

# Modules
curl -s http://localhost:8888/api/v2/modules | python3 -c "
import json,sys
for m in json.load(sys.stdin)['data']:
    icon = '🟢' if m['status']=='running' else '🟡' if m['status']=='no_api_key' else '🔴'
    print(icon, m['name'], '-', m['status'])
"

# Hermes events count
curl -s "http://localhost:8888/api/v2/events?limit=1000" | python3 -c "
import json,sys
data = json.load(sys.stdin)['data']
hermes = [e for e in data if e.get('location','').startswith('hermes')]
print(f'Total events: {len(data)} | Hermes events: {len(hermes)}')
"
```

---

## Summary Table

| # | Name | Channel | Key Check |
|---|------|---------|-----------|
| 1 | Basic ping | REST | Hermes sees INDB |
| 2 | Ingest via REST | REST | curl from Hermes → event in INDB |
| 3 | MCP get_stats | MCP | MCP stack alive |
| 4 | MCP write + read | MCP | Full cycle via MCP |
| 5 | Source Connector | Files | INDB reads Hermes sessions |
| 6 | Prism + paradox | REST | Two opinions → `is_paradoxical: true` |
| 7 | Echo resonance | REST / MCP | Semantic search works |
| 8 | Blind Payload | REST | Fact without content |
| 9 | TUI monitoring | UI | Full pipeline visible in real time |
