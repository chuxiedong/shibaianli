#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

OUT_FILE="$ROOT_DIR/reports/runtime_report.md"
LOCK_DIR="$ROOT_DIR/.mission_6h.lock"
WD_LOCK_DIR="$ROOT_DIR/.mission_watchdog.lock"
STATUS_FILE="$ROOT_DIR/reports/mission_6h_status.md"
NOW_TS="$(date +%s)"
NOW_HUMAN="$(date '+%Y-%m-%d %H:%M:%S')"

mission_pid="-"
mission_hb="-"
mission_hb_age="-"
if [ -f "$LOCK_DIR/pid" ]; then
  mission_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo '-')"
fi
if [ -f "$LOCK_DIR/heartbeat" ]; then
  mission_hb="$(cat "$LOCK_DIR/heartbeat" 2>/dev/null || echo '-')"
  if [ "$mission_hb" != "-" ]; then
    mission_hb_age=$((NOW_TS - mission_hb))
  fi
fi

watchdog_state="stopped"
if [ -d "$WD_LOCK_DIR" ]; then
  watchdog_state="running"
fi

db_stats="$(python3 - <<'PY'
import sqlite3
conn=sqlite3.connect('data.db')
cur=conn.cursor()
vals=[]
for t in ['startups','updates','source_snapshots','mirrored_pages','mirrored_page_versions']:
    try:
        cur.execute(f'select count(*) from {t}')
        vals.append(f"{t}={cur.fetchone()[0]}")
    except Exception:
        vals.append(f"{t}=ERR")
conn.close()
print(' '.join(vals))
PY
)"

{
  echo "# Runtime Report"
  echo
  echo "- generated_at: $NOW_HUMAN"
  echo "- mission_pid: $mission_pid"
  echo "- mission_heartbeat_epoch: $mission_hb"
  echo "- mission_heartbeat_age_sec: $mission_hb_age"
  echo "- watchdog: $watchdog_state"
  echo "- db_stats: $db_stats"
  if [ -f "$STATUS_FILE" ]; then
    echo
    echo "## mission_status"
    cat "$STATUS_FILE"
  fi
} > "$OUT_FILE"

echo "$OUT_FILE"
