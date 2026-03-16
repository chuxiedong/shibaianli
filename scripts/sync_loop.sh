#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

INTERVAL_SECONDS="${INTERVAL_SECONDS:-21600}"
echo "[sync_loop] start interval=${INTERVAL_SECONDS}s"

while true; do
  python3 scripts/watch_updates.py || true
  python3 scripts/ingest_public_pages.py || true
  sleep "$INTERVAL_SECONDS"
done
