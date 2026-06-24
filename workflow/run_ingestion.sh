#!/bin/bash
# Hermes ingestion only
set -e
cd "$(dirname "$0")/.."
export TARGET_EVENTS="${TARGET_EVENTS:-5000}"
export INDB_API_URL="${INDB_API_URL:-http://localhost:8888}"
python3 workflow/hermes_ingestion.py
