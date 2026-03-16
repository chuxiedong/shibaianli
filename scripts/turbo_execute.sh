#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MAX_URLS="${MAX_URLS:-60}"
LOG_FILE="$ROOT_DIR/logs/turbo_execute.log"
OUT_JSON="$ROOT_DIR/reports/turbo_last_run.json"

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/reports"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

step_start_epoch=0
start_step() {
  step_start_epoch="$(date +%s)"
  log "step begin: $1"
}
end_step() {
  end_epoch="$(date +%s)"
  elapsed=$((end_epoch - step_start_epoch))
  echo "[$(ts)] step end: $1 elapsed=${elapsed}s" >> "$LOG_FILE"
  echo "$elapsed"
}

RUN_TS="$(ts)"
TOTAL_START="$(date +%s)"

start_step watch_updates
MAX_URLS="$MAX_URLS" python3 scripts/watch_updates.py >>"$LOG_FILE" 2>&1 || true
ELAPSED_WATCH=$(end_step watch_updates)
/bin/sh scripts/record_manual_step.sh watch_updates_turbo ok "turbo run" turbo >>"$LOG_FILE" 2>&1 || true

start_step ingest_public_pages
python3 scripts/ingest_public_pages.py >>"$LOG_FILE" 2>&1 || true
ELAPSED_INGEST=$(end_step ingest_public_pages)
/bin/sh scripts/record_manual_step.sh ingest_public_pages_turbo ok "turbo run" turbo >>"$LOG_FILE" 2>&1 || true

start_step backup
BACKUP_KEEP="${BACKUP_KEEP:-30}" /bin/sh scripts/backup_data.sh >>"$LOG_FILE" 2>&1 || true
ELAPSED_BACKUP=$(end_step backup)
/bin/sh scripts/record_manual_step.sh backup_data_turbo ok "turbo run" turbo >>"$LOG_FILE" 2>&1 || true

start_step analytics
python3 scripts/mission_alerts.py >>"$LOG_FILE" 2>&1 || true
python3 scripts/mission_retro.py >>"$LOG_FILE" 2>&1 || true
python3 scripts/next_actions.py >>"$LOG_FILE" 2>&1 || true
python3 scripts/acceleration_engine.py >>"$LOG_FILE" 2>&1 || true
python3 scripts/mission_audit.py >>"$LOG_FILE" 2>&1 || true
python3 scripts/maintenance.py >>"$LOG_FILE" 2>&1 || true
ELAPSED_ANALYTICS=$(end_step analytics)

TOTAL_END="$(date +%s)"
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))

cat > "$OUT_JSON" <<EOF
{
  "run_at": "$RUN_TS",
  "max_urls": $MAX_URLS,
  "elapsed_seconds": $TOTAL_ELAPSED,
  "steps": {
    "watch_updates": $ELAPSED_WATCH,
    "ingest_public_pages": $ELAPSED_INGEST,
    "backup": $ELAPSED_BACKUP,
    "analytics": $ELAPSED_ANALYTICS
  },
  "log_file": "$LOG_FILE"
}
EOF

log "turbo run complete total=${TOTAL_ELAPSED}s"
echo "$OUT_JSON"
