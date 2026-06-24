#!/bin/bash
# Setup Hermes to use INDB via MCP — input and output through INDB
#
# Hermes will:
# - fetch data (fetch, summarize) and write to INDB via ingest_event
# - answer abstract queries by querying INDB via query_events
#
set -e

HERMES_CONFIG="${HOME}/.hermes/config.yaml"
INDB_MCP_URL="${INDB_MCP_URL:-http://localhost:8888/api/v2/mcp/sse}"

echo "=== Hermes + INDB MCP Setup ==="
echo "  Config: $HERMES_CONFIG"
echo "  INDB MCP: $INDB_MCP_URL"
echo ""

if [ ! -f "$HERMES_CONFIG" ]; then
    echo "ERROR: Hermes config not found. Run 'hermes setup' first."
    exit 1
fi

# Check if indb is already in mcp_servers
if grep -q "indb:" "$HERMES_CONFIG" 2>/dev/null; then
    echo "INDB MCP already configured."
    grep -A2 "indb:" "$HERMES_CONFIG" || true
    exit 0
fi

# Create backup
cp "$HERMES_CONFIG" "${HERMES_CONFIG}.bak.$(date +%Y%m%d%H%M%S)"

# Add indb to mcp_servers
python3 << PYEOF
import re, os
path = os.path.expanduser("~/.hermes/config.yaml")
url = os.environ.get("INDB_MCP_URL", "http://localhost:8888/api/v2/mcp/sse")
with open(path) as f:
    content = f.read()
if "indb:" in content:
    print("indb already in config")
else:
    block = '''
  indb:
    url: "''' + url + '''"
'''
    if "mcp_servers:" in content:
        content = content.replace("mcp_servers:", "mcp_servers:" + block, 1)
    else:
        content += "\nmcp_servers:" + block
    with open(path, "w") as f:
        f.write(content)
    print("Added indb MCP")
PYEOF

echo ""
echo "Done. Hermes now has INDB tools: mcp_indb_query_events, mcp_indb_ingest_event, mcp_indb_get_stats"
echo ""
echo "Reload MCP: send /reload-mcp in Hermes chat, or restart Hermes."
echo ""
echo "Test: hermes chat -q 'Use mcp_indb_get_stats and show me INDB database stats'"
