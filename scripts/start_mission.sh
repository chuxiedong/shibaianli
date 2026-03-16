#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

DURATION_SECONDS="${DURATION_SECONDS:-21600}"
CYCLE_SECONDS="${CYCLE_SECONDS:-900}"
BACKUP_EVERY_N="${BACKUP_EVERY_N:-4}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
MAX_RETRIES="${MAX_RETRIES:-3}"
MAX_URLS="${MAX_URLS:-80}"
STALE_LOCK_SECONDS="${STALE_LOCK_SECONDS:-1800}"
HEARTBEAT_TICK_SECONDS="${HEARTBEAT_TICK_SECONDS:-30}"
LOCK_DIR="$ROOT_DIR/.mission_6h.lock"
HEARTBEAT_FILE="$LOCK_DIR/heartbeat"
PID_FILE="$LOCK_DIR/pid"

mkdir -p "$ROOT_DIR/logs"

if [ -d "$LOCK_DIR" ] && [ -f "$HEARTBEAT_FILE" ]; then
  now_ts="$(date +%s)"
  hb_ts="$(cat "$HEARTBEAT_FILE" 2>/dev/null || echo 0)"
  if [ $((now_ts - hb_ts)) -lt "$STALE_LOCK_SECONDS" ]; then
    if [ -f "$PID_FILE" ]; then
      cat "$PID_FILE"
    else
      echo "mission already running"
    fi
    exit 0
  fi
fi

nohup env \
  DURATION_SECONDS="$DURATION_SECONDS" \
  CYCLE_SECONDS="$CYCLE_SECONDS" \
  BACKUP_EVERY_N="$BACKUP_EVERY_N" \
  BACKUP_KEEP="$BACKUP_KEEP" \
  MAX_RETRIES="$MAX_RETRIES" \
  MAX_URLS="$MAX_URLS" \
  STALE_LOCK_SECONDS="$STALE_LOCK_SECONDS" \
  HEARTBEAT_TICK_SECONDS="$HEARTBEAT_TICK_SECONDS" \
  /bin/sh "$ROOT_DIR/scripts/mission_6h.sh" \
  >> "$ROOT_DIR/logs/mission_6h.nohup.log" 2>&1 &

echo $!
