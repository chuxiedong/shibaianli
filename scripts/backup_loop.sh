#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"

echo "[backup-loop] start interval=${BACKUP_INTERVAL_SECONDS}s keep=${BACKUP_KEEP}"

while true; do
  BACKUP_KEEP="$BACKUP_KEEP" /bin/sh "$ROOT_DIR/scripts/backup_data.sh" || true
  sleep "$BACKUP_INTERVAL_SECONDS"
done
