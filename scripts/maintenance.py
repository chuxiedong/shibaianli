#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"
BACKUPS = ROOT / "backups"

MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 5000
KEEP_BACKUPS = 30

STATUS_JSON = REPORTS / "maintenance_status.json"
STATUS_MD = REPORTS / "maintenance_status.md"

LOG_FILES = [
    LOGS / "mission_6h.log",
    LOGS / "mission_6h.nohup.log",
    LOGS / "mission_watchdog.log",
    LOGS / "mission_watchdog.nohup.log",
]

CSV_FILES = [
    REPORTS / "mission_cycles.csv",
    REPORTS / "watchdog_events.csv",
]


def trim_log(path: Path, max_bytes: int) -> dict:
    if not path.exists():
        return {"file": str(path), "action": "skip_missing"}
    size = path.stat().st_size
    if size <= max_bytes:
        return {"file": str(path), "action": "keep", "size": size}
    text = path.read_text(encoding="utf-8", errors="ignore")
    keep_chars = max_bytes
    tail = text[-keep_chars:]
    marker = "\n--- trimmed by maintenance.py ---\n"
    path.write_text(marker + tail, encoding="utf-8")
    return {"file": str(path), "action": "trim", "from": size, "to": path.stat().st_size}


def trim_csv_rows(path: Path, max_rows: int) -> dict:
    if not path.exists():
        return {"file": str(path), "action": "skip_missing"}
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) <= 1:
        return {"file": str(path), "action": "keep_empty"}
    header = lines[0]
    rows = lines[1:]
    if len(rows) <= max_rows:
        return {"file": str(path), "action": "keep", "rows": len(rows)}
    kept = rows[-max_rows:]
    path.write_text("\n".join([header, *kept]) + "\n", encoding="utf-8")
    return {"file": str(path), "action": "trim_rows", "from": len(rows), "to": len(kept)}


def prune_backups(keep: int) -> dict:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    files = sorted(BACKUPS.glob("lootdrop-backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = []
    for old in files[keep:]:
      removed.append(str(old))
      old.unlink(missing_ok=True)
    return {"action": "prune_backups", "kept": min(len(files), keep), "removed": len(removed)}


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)

    log_results = [trim_log(p, MAX_LOG_BYTES) for p in LOG_FILES]
    csv_results = [trim_csv_rows(p, MAX_CSV_ROWS) for p in CSV_FILES]
    backup_result = prune_backups(KEEP_BACKUPS)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "limits": {
            "max_log_bytes": MAX_LOG_BYTES,
            "max_csv_rows": MAX_CSV_ROWS,
            "keep_backups": KEEP_BACKUPS,
        },
        "logs": log_results,
        "csv": csv_results,
        "backups": backup_result,
        "sizes": {
            "logs_bytes": dir_size(LOGS),
            "reports_bytes": dir_size(REPORTS),
            "backups_bytes": dir_size(BACKUPS),
        },
    }

    STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Maintenance Status",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- logs_bytes: {payload['sizes']['logs_bytes']}",
        f"- reports_bytes: {payload['sizes']['reports_bytes']}",
        f"- backups_bytes: {payload['sizes']['backups_bytes']}",
        "",
        "## Log Actions",
    ]
    for item in log_results:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## CSV Actions")
    for item in csv_results:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Backup Actions")
    lines.append(f"- {backup_result}")

    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(STATUS_JSON))
    print(str(STATUS_MD))


if __name__ == "__main__":
    main()
