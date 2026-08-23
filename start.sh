#!/bin/bash

# INDB Multi-Protocol Server Startup Script
# Starts HTTP, UDP, and WebSocket servers

echo "🚀 Starting INDB Multi-Protocol Server v1.0.0..."
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "✅ Starting server..."
echo ""

# Start launcher (module form, so package imports resolve)
python3 -m cli.launcher "$@"
