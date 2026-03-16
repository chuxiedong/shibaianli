#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

LOCK_DIR="$ROOT_DIR/.mission_6h.lock"
PID_FILE="$LOCK_DIR/pid"

if [ -f "$PID_FILE" ]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$pid" ]; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
fi

rm -rf "$LOCK_DIR"
echo "mission stop requested"
