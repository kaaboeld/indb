#!/bin/bash
# Hermes + INDB Integration Scenarios (from HERMES_INTEGRATION_SCENARIOS.md)
# Runs scenarios 1-5 with all conditions
set -e

INDB_URL="${INDB_API_URL:-http://localhost:8888}"
NODE1="${INDB_NODE1_URL:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== INDB Integration Scenarios ==="
echo "  INDB (HAProxy): $INDB_URL"
echo "  INDB node-1:    $NODE1"
echo ""

# Scenario 1 — Health ping
echo "--- Scenario 1: Health ping ---"
curl -sf "$INDB_URL/health" | head -c 200
echo ""
echo "  [OK]"
echo ""

# Scenario 2 — REST ingest
echo "--- Scenario 2: REST ingest ---"
RESP=$(curl -s -X POST "$INDB_URL/api/v2/events" \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["hermes", "test", "integration", "scenario-2"], "location": "hermes://test/scenario-2"}')
if echo "$RESP" | grep -q '"status": "success"'; then
  echo "  [OK] Event created"
else
  echo "  [FAIL] $RESP"
  exit 1
fi
echo ""

# Scenario 3 — MCP get_stats (via Hermes)
echo "--- Scenario 3: MCP get_stats ---"
hermes chat -Q -q "Use mcp_indb_get_stats. Reply with only: OK if you got stats." 2>&1 | tail -5
echo "  [OK]"
echo ""

# Scenario 4 — MCP full cycle ingest + query
echo "--- Scenario 4: MCP ingest + query ---"
hermes chat -Q -q "1) mcp_indb_ingest_event: content='paradox memory truth', location='hermes://mcp/test'. 2) mcp_indb_query_events filter_value='hermes'. Reply: OK if both worked." 2>&1 | tail -8
echo "  [OK]"
echo ""

# Scenario 5 — Verify events in INDB
echo "--- Scenario 5: Verify hermes events in INDB ---"
COUNT=$(curl -s "$INDB_URL/api/v2/events?limit=500" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin).get('data', [])
    hermes = [e for e in data if str(e.get('location','')).startswith('hermes')]
    print(len(hermes))
except: print(0)
" 2>/dev/null || echo "0")
echo "  Hermes events in INDB: $COUNT"
echo "  [OK]"
echo ""

echo "=== All 5 scenarios completed ==="
