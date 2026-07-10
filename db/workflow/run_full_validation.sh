#!/bin/bash
# INDB Full Validation — Hermes input/output, 5-10k events, MD reports
#
# Usage:
#   ./run_full_validation.sh           # full run
#   ./run_full_validation.sh quick     # quick check (~50 topics)
#   TARGET_EVENTS=500 ./run_full_validation.sh
#
set -e

cd "$(dirname "$0")/.."
REPORT_DIR="$(pwd)/reports"
mkdir -p "$REPORT_DIR"

TARGET="${1:-full}"
export TARGET_EVENTS="${TARGET_EVENTS:-5000}"
export INDB_API_URL="${INDB_API_URL:-http://localhost:8888}"

if [ "$TARGET" = "quick" ]; then
    export TARGET_EVENTS=500
    echo "=== Quick mode: target ~500 events ==="
else
    echo "=== Full validation: target ~$TARGET_EVENTS events ==="
fi

echo ""
echo "Phase 1: Hermes ingestion (raw → formulate → MCP ingest)"
echo "  INDB: $INDB_API_URL"
echo ""

python3 workflow/hermes_ingestion.py 2>&1 | tee "$REPORT_DIR/ingestion_stdout.log"

echo ""
echo "Phase 2: Verify mechanics (fusion, storage)"
echo ""
python3 workflow/verify_mechanics.py 2>&1 | tee "$REPORT_DIR/mechanics_stdout.log"

echo ""
echo "Phase 3: Abstract queries via Hermes"
echo ""
python3 workflow/abstract_queries.py 2>&1 | tee "$REPORT_DIR/queries_stdout.log"

echo ""
echo "Phase 4: Generate MD report"
echo ""
python3 workflow/report_generator.py 2>&1 | tee "$REPORT_DIR/report_stdout.log"

echo ""
echo "=== Done. Reports in $REPORT_DIR ==="
ls -la "$REPORT_DIR"/*.json "$REPORT_DIR"/*.md 2>/dev/null || true
