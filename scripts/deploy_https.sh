#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -z "${DOMAIN:-}" ]; then
  echo "missing DOMAIN env, example: DOMAIN=example.com ACME_EMAIL=ops@example.com ./scripts/deploy_https.sh"
  exit 1
fi

if [ -z "${ACME_EMAIL:-}" ]; then
  echo "missing ACME_EMAIL env"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found"
  exit 1
fi

echo "[deploy-https] starting app stack"
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build

echo "[deploy-https] warm ingest"
docker compose run --rm --no-deps updater python3 scripts/ingest_public_pages.py || true

echo "[deploy-https] done"
echo "HTTP:  http://$DOMAIN"
echo "HTTPS: https://$DOMAIN"
