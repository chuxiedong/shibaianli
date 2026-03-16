#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RUNTIME = REPORTS / "runtime_report.md"
CYCLES = REPORTS / "mission_cycles.csv"
EVENTS = REPORTS / "watchdog_events.csv"
OUT_JSON = REPORTS / "mission_alerts.json"
OUT_MD = REPORTS / "mission_alerts.md"


def read_cycles(limit: int = 80):
    if not CYCLES.exists():
        return []
    with CYCLES.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


def read_events(limit: int = 50):
    if not EVENTS.exists():
        return []
    with EVENTS.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


def parse_heartbeat_age(md: str) -> int | None:
    needle = "- mission_heartbeat_age_sec:"
    for line in md.splitlines():
        if line.startswith(needle):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def parse_cycle_seconds(md: str) -> int | None:
    needle = "- 周期长度:"
    for line in md.splitlines():
        if line.startswith(needle):
            raw = line.split(":", 1)[1].strip().replace(" 秒", "")
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cycles = read_cycles()
    events = read_events()
    runtime_md = RUNTIME.read_text(encoding="utf-8") if RUNTIME.exists() else ""

    alerts = []

    hb_age = parse_heartbeat_age(runtime_md)
    cycle_seconds = parse_cycle_seconds(runtime_md)
    if cycle_seconds is None or cycle_seconds <= 0:
        cycle_seconds = 900
    warn_threshold = max(600, cycle_seconds * 2)
    critical_threshold = max(1800, cycle_seconds * 3)
    if hb_age is None:
        alerts.append({"severity": "warning", "code": "NO_HEARTBEAT", "message": "未解析到心跳年龄"})
    elif hb_age > critical_threshold:
        alerts.append({"severity": "critical", "code": "HEARTBEAT_STALE", "message": f"心跳过旧: {hb_age}s (threshold={critical_threshold}s)"})
    elif hb_age > warn_threshold:
        alerts.append({"severity": "warning", "code": "HEARTBEAT_SLOW", "message": f"心跳偏慢: {hb_age}s (threshold={warn_threshold}s)"})

    fail_count = sum(1 for r in cycles if r.get("result") == "fail")
    total_steps = len(cycles)
    if total_steps > 0:
        fail_rate = fail_count / total_steps
        if fail_rate >= 0.2:
            alerts.append({"severity": "warning", "code": "HIGH_FAIL_RATE", "message": f"步骤失败率偏高: {fail_count}/{total_steps}"})

    restart_events = [e for e in events if e.get("event") == "mission_restart"]
    if len(restart_events) >= 3:
        alerts.append({"severity": "warning", "code": "FREQUENT_RESTART", "message": f"watchdog 重启次数偏多: {len(restart_events)}"})

    payload = {
        "generated_at": now,
        "alert_count": len(alerts),
        "alerts": alerts,
        "metrics": {
            "heartbeat_age_sec": hb_age,
            "cycle_seconds": cycle_seconds,
            "heartbeat_warn_threshold": warn_threshold,
            "heartbeat_critical_threshold": critical_threshold,
            "step_total": total_steps,
            "step_fail": fail_count,
            "watchdog_restarts": len(restart_events),
        },
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Mission Alerts",
        "",
        f"- generated_at: {now}",
        f"- alert_count: {len(alerts)}",
        f"- heartbeat_age_sec: {hb_age}",
        f"- step_fail: {fail_count}/{total_steps}",
        f"- watchdog_restarts: {len(restart_events)}",
        "",
        "## Alerts",
    ]
    if alerts:
        for a in alerts:
            lines.append(f"- [{a['severity']}] {a['code']}: {a['message']}")
    else:
        lines.append("- none")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
