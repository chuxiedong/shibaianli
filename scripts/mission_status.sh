#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

LOCK_DIR="$ROOT_DIR/.mission_6h.lock"
STATUS_FILE="$ROOT_DIR/reports/mission_6h_status.md"
NOHUP_LOG="$ROOT_DIR/logs/mission_6h.nohup.log"
MAIN_LOG="$ROOT_DIR/logs/mission_6h.log"

if [ -d "$LOCK_DIR" ]; then
  echo "lock: present"
  [ -f "$LOCK_DIR/pid" ] && echo "pid: $(cat "$LOCK_DIR/pid")"
  [ -f "$LOCK_DIR/heartbeat" ] && echo "heartbeat: $(cat "$LOCK_DIR/heartbeat")"
else
  echo "lock: absent"
fi

if [ -f "$STATUS_FILE" ]; then
  echo "--- status ---"
  cat "$STATUS_FILE"
fi

if [ -f "$NOHUP_LOG" ]; then
  echo "--- nohup tail ---"
  tail -n 20 "$NOHUP_LOG"
fi

if [ -f "$MAIN_LOG" ]; then
  echo "--- main tail ---"
  tail -n 20 "$MAIN_LOG"
fi
