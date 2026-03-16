#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ "$#" -lt 3 ]; then
  echo "usage: ./scripts/record_manual_step.sh <step> <result> <note> [cycle]"
  exit 1
fi

STEP="$1"
RESULT="$2"
NOTE="$3"
CYCLE="${4:-manual}"
CSV="$ROOT_DIR/reports/mission_cycles.csv"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p "$ROOT_DIR/reports"
if [ ! -f "$CSV" ]; then
  echo "timestamp,cycle,step,result,note" > "$CSV"
fi
SAFE_NOTE="$(echo "$NOTE" | tr ',' ';')"
echo "$TS,$CYCLE,$STEP,$RESULT,$SAFE_NOTE" >> "$CSV"

echo "$TS,$CYCLE,$STEP,$RESULT,$SAFE_NOTE"
