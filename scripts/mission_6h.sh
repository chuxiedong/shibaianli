#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

DURATION_SECONDS="${DURATION_SECONDS:-21600}"
CYCLE_SECONDS="${CYCLE_SECONDS:-900}"
BACKUP_EVERY_N="${BACKUP_EVERY_N:-4}"
MAX_RETRIES="${MAX_RETRIES:-3}"
LOG_FILE="$ROOT_DIR/logs/mission_6h.log"
STATUS_FILE="$ROOT_DIR/reports/mission_6h_status.md"
LOCK_DIR="$ROOT_DIR/.mission_6h.lock"
PID_FILE="$LOCK_DIR/pid"
HEARTBEAT_FILE="$LOCK_DIR/heartbeat"
STALE_LOCK_SECONDS="${STALE_LOCK_SECONDS:-1800}"
CYCLE_CSV="$ROOT_DIR/reports/mission_cycles.csv"
MAX_URLS="${MAX_URLS:-120}"
HEARTBEAT_TICK_SECONDS="${HEARTBEAT_TICK_SECONDS:-30}"

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/reports"

if [ -d "$LOCK_DIR" ]; then
  stale=1
  if [ -f "$HEARTBEAT_FILE" ]; then
    now_ts="$(date +%s)"
    hb_ts="$(cat "$HEARTBEAT_FILE" 2>/dev/null || echo 0)"
    if [ $((now_ts - hb_ts)) -lt "$STALE_LOCK_SECONDS" ]; then
      stale=0
    fi
  fi
  if [ "$stale" -eq 1 ]; then
    rm -rf "$LOCK_DIR"
  else
    echo "mission lock exists and active: $LOCK_DIR"
    exit 0
  fi
fi

mkdir -p "$LOCK_DIR"
echo "$$" > "$PID_FILE"
date +%s > "$HEARTBEAT_FILE"
trap 'rm -rf "$LOCK_DIR" >/dev/null 2>&1 || true' EXIT

log() {
  TS="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[$TS] $*" | tee -a "$LOG_FILE"
}

record_step() {
  ts="$1"
  cycle_id="$2"
  step="$3"
  result="$4"
  note="$5"
  if [ ! -f "$CYCLE_CSV" ]; then
    echo "timestamp,cycle,step,result,note" > "$CYCLE_CSV"
  fi
  # Replace commas in note to keep CSV shape stable.
  safe_note="$(echo "$note" | tr ',' ';')"
  echo "$ts,$cycle_id,$step,$result,$safe_note" >> "$CYCLE_CSV"
}

run_with_retry() {
  name="$1"
  shift
  i=1
  while [ "$i" -le "$MAX_RETRIES" ]; do
    if "$@" >>"$LOG_FILE" 2>&1; then
      log "step ok: $name (try=$i)"
      return 0
    fi
    log "step failed: $name (try=$i)"
    sleep "$((i * 2))"
    i=$((i + 1))
  done
  log "step hard-failed: $name"
  return 1
}

start_epoch="$(date +%s)"
end_epoch=$((start_epoch + DURATION_SECONDS))
cycle=0

log "mission start duration=${DURATION_SECONDS}s cycle=${CYCLE_SECONDS}s backup_every=${BACKUP_EVERY_N}"
if run_with_retry "init_db" python3 -c "from backend.app import init_db; init_db(); print('db initialized')"; then
  record_step "$(date '+%Y-%m-%d %H:%M:%S')" "0" "init_db" "ok" "database ready"
else
  record_step "$(date '+%Y-%m-%d %H:%M:%S')" "0" "init_db" "fail" "database init failed"
fi

while [ "$(date +%s)" -lt "$end_epoch" ]; do
  date +%s > "$HEARTBEAT_FILE"
  cycle=$((cycle + 1))
  log "cycle begin #$cycle"

  now="$(date '+%Y-%m-%d %H:%M:%S')"
  remaining=$((end_epoch - $(date +%s)))
  [ "$remaining" -lt 0 ] && remaining=0
  cat > "$STATUS_FILE" <<EOF
# 6小时任务状态

- 当前时间: $now
- 已执行周期: $cycle
- 当前步骤: watch_updates
- 周期长度: ${CYCLE_SECONDS} 秒
- 预计剩余: ${remaining} 秒
- MAX_URLS: ${MAX_URLS}
- 日志文件: $LOG_FILE
EOF

  if run_with_retry "watch_updates" env MAX_URLS="$MAX_URLS" python3 scripts/watch_updates.py; then
    record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "watch_updates" "ok" "watch updates done"
  else
    record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "watch_updates" "fail" "watch updates failed"
  fi

  now="$(date '+%Y-%m-%d %H:%M:%S')"
  remaining=$((end_epoch - $(date +%s)))
  [ "$remaining" -lt 0 ] && remaining=0
  cat > "$STATUS_FILE" <<EOF
# 6小时任务状态

- 当前时间: $now
- 已执行周期: $cycle
- 当前步骤: ingest_public_pages
- 周期长度: ${CYCLE_SECONDS} 秒
- 预计剩余: ${remaining} 秒
- MAX_URLS: ${MAX_URLS}
- 日志文件: $LOG_FILE
EOF
  if run_with_retry "ingest_public_pages" python3 scripts/ingest_public_pages.py; then
    record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "ingest_public_pages" "ok" "ingest done"
  else
    record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "ingest_public_pages" "fail" "ingest failed"
  fi

  if [ $((cycle % BACKUP_EVERY_N)) -eq 0 ]; then
    now="$(date '+%Y-%m-%d %H:%M:%S')"
    remaining=$((end_epoch - $(date +%s)))
    [ "$remaining" -lt 0 ] && remaining=0
    cat > "$STATUS_FILE" <<EOF
# 6小时任务状态

- 当前时间: $now
- 已执行周期: $cycle
- 当前步骤: backup_data
- 周期长度: ${CYCLE_SECONDS} 秒
- 预计剩余: ${remaining} 秒
- MAX_URLS: ${MAX_URLS}
- 日志文件: $LOG_FILE
EOF
    if run_with_retry "backup_data" /bin/sh scripts/backup_data.sh; then
      record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "backup_data" "ok" "backup done"
    else
      record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "backup_data" "fail" "backup failed"
    fi
  fi

  now="$(date '+%Y-%m-%d %H:%M:%S')"
  remaining=$((end_epoch - $(date +%s)))
  [ "$remaining" -lt 0 ] && remaining=0
  cat > "$STATUS_FILE" <<EOF
# 6小时任务状态

- 当前时间: $now
- 已执行周期: $cycle
- 当前步骤: db_metrics
- 周期长度: ${CYCLE_SECONDS} 秒
- 预计剩余: ${remaining} 秒
- MAX_URLS: ${MAX_URLS}
- 日志文件: $LOG_FILE
EOF
  if run_with_retry "db_metrics" python3 -c "import sqlite3; conn=sqlite3.connect('data.db'); cur=conn.cursor(); cur.execute('select count(*) from startups'); s=cur.fetchone()[0]; cur.execute('select count(*) from mirrored_pages'); m=cur.fetchone()[0]; cur.execute('select count(*) from mirrored_page_versions'); v=cur.fetchone()[0]; conn.close(); print(f'metrics startups={s} mirrored_pages={m} mirrored_versions={v}')"; then
    record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "db_metrics" "ok" "metrics collected"
  else
    record_step "$(date '+%Y-%m-%d %H:%M:%S')" "$cycle" "db_metrics" "fail" "metrics failed"
  fi

  now="$(date '+%Y-%m-%d %H:%M:%S')"
  remaining=$((end_epoch - $(date +%s)))
  [ "$remaining" -lt 0 ] && remaining=0
  cat > "$STATUS_FILE" <<EOF
# 6小时任务状态

- 当前时间: $now
- 已执行周期: $cycle
- 当前步骤: sleep
- 周期长度: ${CYCLE_SECONDS} 秒
- 预计剩余: ${remaining} 秒
- MAX_URLS: ${MAX_URLS}
- 日志文件: $LOG_FILE
EOF

  log "cycle end #$cycle"
  date +%s > "$HEARTBEAT_FILE"
  sleep_left="$CYCLE_SECONDS"
  while [ "$sleep_left" -gt 0 ]; do
    tick="$HEARTBEAT_TICK_SECONDS"
    if [ "$sleep_left" -lt "$tick" ]; then
      tick="$sleep_left"
    fi
    sleep "$tick"
    date +%s > "$HEARTBEAT_FILE"
    sleep_left=$((sleep_left - tick))
  done
done

log "mission complete cycles=$cycle"
