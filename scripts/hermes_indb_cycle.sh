#!/bin/bash
# Hermes INDB Cycle: data collection via Hermes → INDB, query via Hermes ← INDB
#
# Usage:
#   ./hermes_indb_cycle.sh ingest "topic to search"   # Hermes fetches and writes to INDB
#   ./hermes_indb_cycle.sh query "abstract query"      # Hermes answers from INDB
#   ./hermes_indb_cycle.sh both "topic"               # ingest + query
#   ./hermes_indb_cycle.sh rest                       # REST fallback (5 requests)
#   ./hermes_indb_cycle.sh full                       # 5 Hermes requests (ingest→query→ingest→query→stats)
#
set -e

MODE="${1:-both}"
TOPIC="${2:-epistemology}"

case "$MODE" in
  ingest)
    PROMPT="Find information about '$TOPIC' on the web. Summarize key points in 5-10 tokens. Store in INDB via mcp_indb_ingest_event: content='your tokens here', location='hermes://fetch/$TOPIC'"
    ;;
  query)
    PROMPT="Use mcp_indb_query_events to find events about '$TOPIC'. filter_key='$TOPIC' or filter_key=location filter_value=$TOPIC. Summarize what INDB contains."
    ;;
  both)
    PROMPT="1) Fetch a short definition of '$TOPIC' from web. Store in INDB via mcp_indb_ingest_event. 2) Then use mcp_indb_query_events to find events about $TOPIC. Summarize both steps."
    ;;
  stats)
    PROMPT="Use mcp_indb_get_stats and show me INDB database statistics."
    ;;
  rest)
    echo "=== REST INDB Cycle (5 requests) ==="
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    exec python3 "$SCRIPT_DIR/rest_indb_cycle.py"
    ;;
  full)
    echo "=== Hermes INDB Cycle: 5 requests ==="
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    for i in 1 2 3 4 5; do
      case $i in
        1) hermes chat -Q -q "Use mcp_indb_ingest_event: content='epistemology branch philosophy knowledge truth', location='hermes://fetch/epistemology'. Confirm the event ID." ;;
        2) "$SCRIPT_DIR/hermes_indb_cycle.sh" query epistemology ;;
        3) hermes chat -Q -q "Use mcp_indb_ingest_event: content='collective memory shared pool memories', location='hermes://fetch/collective-memory'. Confirm the event ID." ;;
        4) "$SCRIPT_DIR/hermes_indb_cycle.sh" query memory ;;
        5) "$SCRIPT_DIR/hermes_indb_cycle.sh" stats ;;
      esac
      sleep 2
    done
    exit 0
    ;;
  *)
    echo "Usage: $0 {ingest|query|both|stats|rest|full} [topic]"
    exit 1
    ;;
esac

echo "=== Hermes INDB Cycle: $MODE ==="
echo "  Topic: $TOPIC"
echo "  Prompt: $PROMPT"
echo ""

hermes chat -Q -q "$PROMPT" 2>&1
