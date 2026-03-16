#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

STALE_LOCK_SECONDS="${STALE_LOCK_SECONDS:-1800}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-30}"
LOG_FILE="$ROOT_DIR/logs/mission_watchdog.log"
LOCK_DIR="$ROOT_DIR/.mission_6h.lock"
HEARTBEAT_FILE="$LOCK_DIR/heartbeat"
WD_LOCK_DIR="$ROOT_DIR/.mission_watchdog.lock"
EVENTS_CSV="$ROOT_DIR/reports/watchdog_events.csv"
STALE_AGE=0
loop_count=0
MAINTENANCE_EVERY="${MAINTENANCE_EVERY:-10}"

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/reports"

if ! mkdir "$WD_LOCK_DIR" 2>/dev/null; then
  echo "watchdog lock exists: $WD_LOCK_DIR"
  exit 0
fi
trap 'rm -rf "$WD_LOCK_DIR" >/dev/null 2>&1 || true' EXIT

log() {
  TS="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$TS] $*" | tee -a "$LOG_FILE"
}

record_event() {
  ts="$1"
  event="$2"
  details="$3"
  if [ ! -f "$EVENTS_CSV" ]; then
    echo "timestamp,event,details" > "$EVENTS_CSV"
  fi
  safe_details="$(echo "$details" | tr ',' ';')"
  echo "$ts,$event,$safe_details" >> "$EVENTS_CSV"
}

is_stale() {
  if [ ! -d "$LOCK_DIR" ]; then
    return 0
  fi
  if [ ! -f "$HEARTBEAT_FILE" ]; then
    return 0
  fi
  now_ts="$(date +%s)"
  hb_ts="$(cat "$HEARTBEAT_FILE" 2>/dev/null || echo 0)"
  STALE_AGE=$((now_ts - hb_ts))
  [ "$STALE_AGE" -gt "$STALE_LOCK_SECONDS" ]
}

log "watchdog start interval=${CHECK_INTERVAL_SECONDS}s stale=${STALE_LOCK_SECONDS}s"
record_event "$(date '+%Y-%m-%d %H:%M:%S')" "watchdog_start" "interval=${CHECK_INTERVAL_SECONDS}s stale=${STALE_LOCK_SECONDS}s"

while true; do
  loop_count=$((loop_count + 1))
  if is_stale; then
    log "mission stale or absent, restarting"
    record_event "$(date '+%Y-%m-%d %H:%M:%S')" "mission_restart" "stale_age=${STALE_AGE}"
    rm -rf "$LOCK_DIR" || true
    MAX_URLS="${MAX_URLS:-80}" DURATION_SECONDS="${DURATION_SECONDS:-21600}" CYCLE_SECONDS="${CYCLE_SECONDS:-900}" HEARTBEAT_TICK_SECONDS="${HEARTBEAT_TICK_SECONDS:-30}" BACKUP_EVERY_N="${BACKUP_EVERY_N:-4}" BACKUP_KEEP="${BACKUP_KEEP:-14}" MAX_RETRIES="${MAX_RETRIES:-3}" STALE_LOCK_SECONDS="$STALE_LOCK_SECONDS" /bin/sh "$ROOT_DIR/scripts/start_mission.sh" >>"$LOG_FILE" 2>&1 || true
    record_event "$(date '+%Y-%m-%d %H:%M:%S')" "mission_restart_done" "requested"
  fi
  /bin/sh "$ROOT_DIR/scripts/runtime_report.sh" >>"$LOG_FILE" 2>&1 || true
  python3 "$ROOT_DIR/scripts/mission_audit.py" >>"$LOG_FILE" 2>&1 || true
  python3 "$ROOT_DIR/scripts/mission_alerts.py" >>"$LOG_FILE" 2>&1 || true
  python3 "$ROOT_DIR/scripts/mission_retro.py" >>"$LOG_FILE" 2>&1 || true
  python3 "$ROOT_DIR/scripts/next_actions.py" >>"$LOG_FILE" 2>&1 || true
  python3 "$ROOT_DIR/scripts/acceleration_engine.py" >>"$LOG_FILE" 2>&1 || true
  if [ $((loop_count % MAINTENANCE_EVERY)) -eq 0 ]; then
    python3 "$ROOT_DIR/scripts/maintenance.py" >>"$LOG_FILE" 2>&1 || true
    record_event "$(date '+%Y-%m-%d %H:%M:%S')" "maintenance" "loop=${loop_count}"
  fi
  sleep "$CHECK_INTERVAL_SECONDS"
done
