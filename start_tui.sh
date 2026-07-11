#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Drop stale bytecode so Textual always loads the latest app.py.
find cli/tui -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find cli/tui -name '*.pyc' -delete 2>/dev/null || true

export PYTHONDONTWRITEBYTECODE=1
echo "INDB TUI (inline picker, no ModalScreen) — use this launcher" >&2
exec python3 -m cli.tui.app "$@"
