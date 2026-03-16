#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin not found"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found"
  exit 1
fi

echo "[deploy] building and starting services..."
docker compose up -d --build

echo "[deploy] waiting for app health..."
tries=0
until curl -fsS "http://127.0.0.1:8080/api/health" >/dev/null 2>&1; do
  tries=$((tries + 1))
  if [ "$tries" -gt 30 ]; then
    echo "[deploy] health check timeout"
    docker compose ps
    exit 1
  fi
  sleep 2
done

echo "[deploy] initial public-page ingest..."
docker compose run --rm --no-deps updater python3 scripts/ingest_public_pages.py || true

echo "[deploy] done"
echo "Visit: http://<server-ip>:8080"
