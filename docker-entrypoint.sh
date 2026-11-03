#!/bin/sh
# INDB entry — same idea as the official postgres image:
# prepare $DATA_DIR, then run the server (or tui/cli).
set -eu

DATA_DIR="${DATA_DIR:-/data}"
mkdir -p "$DATA_DIR"

if [ "$(id -u)" = "0" ]; then
  chown -R indb:indb "$DATA_DIR"
  exec gosu indb "$0" "$@"
fi

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "INDB ${INDB_VERSION:-}"
  echo "usage: docker run indb [api|tui|cli] [args...]"
  echo "data:  ${DATA_DIR}"
  exit 0
fi

# docker run indb --host 0.0.0.0  →  api --host ...
if [ $# -gt 0 ] && [ "${1#-}" != "$1" ]; then
  set -- api "$@"
fi

cmd="${1:-api}"
shift $(( $# > 0 ? 1 : 0 )) || true

case "$cmd" in
  api|server)
    exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 "$@"
    ;;
  tui)
    exec python3 -m cli.tui "$@"
    ;;
  cli)
    exec python3 -m cli.indb_cli "$@"
    ;;
  *)
    exec "$cmd" "$@"
    ;;
esac
