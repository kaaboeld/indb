#!/bin/bash
# INDB + Hermes Integration — Quick Test Script
# Usage: ./scripts/test_hermes_integration.sh [API_URL]

set -e
API_URL="${1:-${INDB_API_URL:-http://127.0.0.1:8000}}"

echo "=== INDB + Hermes Integration Test ==="
echo "API: $API_URL"
echo ""

# 1. Health
echo "1. Health check..."
if ! curl -sf "$API_URL/health" > /dev/null; then
  echo "   ❌ INDB not reachable at $API_URL"
  exit 1
fi
echo "   ✓ INDB is running"
echo ""

# 2. Modules
echo "2. Modules status..."
MODULES=$(curl -sf "$API_URL/api/v2/modules" | jq -r '.data[] | "\(.name): \(.status)"' 2>/dev/null || echo "")
if [ -z "$MODULES" ]; then
  echo "   ⚠ Could not fetch modules"
else
  echo "$MODULES" | while read line; do echo "   $line"; done
fi
echo ""

# 3. Ingest test event
echo "3. Ingest test event (hermes:integration:test)..."
RESP=$(curl -sf -X POST "$API_URL/api/v2/events" \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["hermes:integration", "hermes:test", "hermes:script"], "location": "hermes://integration-test"}')
EVENT_ID=$(echo "$RESP" | jq -r '.data.id // empty')
if [ -n "$EVENT_ID" ]; then
  echo "   ✓ Ingested event ID: ${EVENT_ID:0:8}..."
else
  echo "   ⚠ Ingest response: $RESP"
fi
echo ""

# 4. Query hermes events
echo "4. Query events from hermes..."
HERMES_COUNT=$(curl -sf "$API_URL/api/v2/events?limit=100" | jq '[.data[]? | select(.location | startswith("hermes"))] | length' 2>/dev/null || echo "0")
echo "   Found $HERMES_COUNT hermes events"
echo ""

# 5. Echo resonance (if we ingested)
if [ -n "$EVENT_ID" ]; then
  echo "5. Echo resonance test..."
  ECHO_RESULT=$(curl -sf -X POST "$API_URL/api/v2/echo/resonate" \
    -H "Content-Type: application/json" \
    -d '{"query_tokens": ["hermes", "integration"], "limit": 3}' 2>/dev/null || echo "{}")
  HITS=$(echo "$ECHO_RESULT" | jq '.data | length' 2>/dev/null || echo "0")
  echo "   Echo returned $HITS matching events"
fi
echo ""

echo "=== Done ==="
