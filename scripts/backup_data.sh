#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$ROOT_DIR/backups"
mkdir -p "$OUT_DIR"

DB_FILE="$ROOT_DIR/data.db"
REPORT_DIR="$ROOT_DIR/reports"
OUT_FILE="$OUT_DIR/lootdrop-backup-$TS.tar.gz"
BACKUP_KEEP="${BACKUP_KEEP:-14}"

tar -czf "$OUT_FILE" "$DB_FILE" "$REPORT_DIR" 2>/dev/null || true

# Keep only the newest N backups.
if [ "$BACKUP_KEEP" -gt 0 ] 2>/dev/null; then
  ls -1t "$OUT_DIR"/lootdrop-backup-*.tar.gz 2>/dev/null | awk "NR>$BACKUP_KEEP" | xargs -r rm -f
fi

echo "$OUT_FILE"
