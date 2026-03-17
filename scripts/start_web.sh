#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8090}"
PYTHON="${PYTHON:-python3}"
LOG_FILE="$ROOT_DIR/logs/web.nohup.log"
PID_FILE="$ROOT_DIR/.web.pid"

mkdir -p "$ROOT_DIR/logs"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null; then
  echo "web already running with pid $(cat "$PID_FILE")"
  exit 0
fi

nohup env HOST="$HOST" PORT="$PORT" "$PYTHON" backend/app.py \
  >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "web started pid=$(cat "$PID_FILE") host=$HOST port=$PORT log=$LOG_FILE"
