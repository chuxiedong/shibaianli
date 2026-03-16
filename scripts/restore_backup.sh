#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ "${1:-}" = "" ]; then
  echo "usage: ./scripts/restore_backup.sh <backup-file.tar.gz>"
  exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "[restore] stopping compose services (if running)"
docker compose down >/dev/null 2>&1 || true

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[restore] extracting backup to temp: $TMP_DIR"
tar -xzf "$BACKUP_FILE" -C "$TMP_DIR"

echo "[restore] applying files"
FOUND_DB="$(find "$TMP_DIR" -name data.db -type f | head -n 1 || true)"
FOUND_REPORTS="$(find "$TMP_DIR" -name reports -type d | head -n 1 || true)"
if [ -n "$FOUND_DB" ]; then
  cp "$FOUND_DB" "$ROOT_DIR/data.db"
fi
if [ -n "$FOUND_REPORTS" ]; then
  rm -rf "$ROOT_DIR/reports"
  cp -R "$FOUND_REPORTS" "$ROOT_DIR/reports"
fi

echo "[restore] done"
echo "restored from: $BACKUP_FILE"
