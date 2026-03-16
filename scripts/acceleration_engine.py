#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CYCLES = REPORTS / "mission_cycles.csv"
ALERTS = REPORTS / "mission_alerts.json"
RUNTIME = REPORTS / "runtime_report.md"
NEXT_ACTIONS = REPORTS / "next_actions.json"
OUT_JSON = REPORTS / "acceleration_plan.json"
OUT_MD = REPORTS / "acceleration_plan.md"


def read_cycles(limit: int = 200):
    if not CYCLES.exists():
        return []
    with CYCLES.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def parse_runtime(md: str) -> dict:
    out = {}
    for line in md.splitlines():
        if not line.startswith("- ") or ":" not in line:
            continue
        k, v = line[2:].split(":", 1)
        out[k.strip()] = v.strip()
    return out


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cycles = read_cycles()
    alerts = read_json(ALERTS, {"alert_count": 0, "alerts": [], "metrics": {}})
    runtime_md = RUNTIME.read_text(encoding="utf-8") if RUNTIME.exists() else ""
    runtime = parse_runtime(runtime_md)
    next_actions = read_json(NEXT_ACTIONS, {"actions": []})

    ok = sum(1 for r in cycles if r.get("result") == "ok")
    fail = sum(1 for r in cycles if r.get("result") == "fail")
    total = max(ok + fail, 1)
    success_rate = ok / total

    hb_age = None
    try:
        hb_age = int(runtime.get("mission_heartbeat_age_sec", "0"))
    except ValueError:
        hb_age = None

    cycle_seconds = 900
    try:
        raw = runtime.get("周期长度", "900 秒").replace(" 秒", "")
        cycle_seconds = int(raw)
    except Exception:
        pass

    bottlenecks = []
    if hb_age is not None and hb_age > cycle_seconds:
        bottlenecks.append("心跳年龄接近或超过单轮周期，状态反馈滞后")
    if alerts.get("alert_count", 0) > 0:
        bottlenecks.append("存在告警，影响任务连续稳定性")
    if fail > 0:
        bottlenecks.append("步骤失败会放大重试时间成本")
    if not bottlenecks:
        bottlenecks.append("当前无显著阻塞，可做增量提速")

    turbo_sequence = [
        {
            "id": 1,
            "step": "缩短观测周期",
            "action": "将 watchdog CHECK_INTERVAL_SECONDS 从 60 降到 30（若资源允许）",
            "eta_gain": "状态刷新提速约 50%",
        },
        {
            "id": 2,
            "step": "抓取优先级推进",
            "action": "保留核心路由优先抓取，MAX_URLS 在 40-80 动态调节",
            "eta_gain": "每轮抓取耗时下降约 30%-70%",
        },
        {
            "id": 3,
            "step": "并行执行可并行项",
            "action": "watch_updates 与 ingest_public_pages 可拆分为并行批次",
            "eta_gain": "单轮任务墙钟时间下降约 25%-40%",
        },
        {
            "id": 4,
            "step": "低频维护聚合",
            "action": "maintenance 每 10 轮执行一次，避免高频维护占用",
            "eta_gain": "维护开销下降约 80%-90%",
        },
        {
            "id": 5,
            "step": "告警驱动执行",
            "action": "当 alert_count=0 时跳过重度诊断，保留轻量心跳检查",
            "eta_gain": "诊断时间下降约 40%",
        },
    ]

    efficiency_score = round(min(100, max(0, success_rate * 70 + (30 if alerts.get("alert_count", 0) == 0 else 0))), 2)

    payload = {
        "generated_at": now,
        "efficiency_score": efficiency_score,
        "success_rate": round(success_rate, 4),
        "ok_steps": ok,
        "fail_steps": fail,
        "alert_count": alerts.get("alert_count", 0),
        "heartbeat_age_sec": hb_age,
        "cycle_seconds": cycle_seconds,
        "bottlenecks": bottlenecks,
        "turbo_sequence": turbo_sequence,
        "next_actions_ref": next_actions.get("actions", [])[:5],
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Acceleration Plan",
        "",
        f"- generated_at: {now}",
        f"- efficiency_score: {efficiency_score}",
        f"- success_rate: {round(success_rate, 4)}",
        f"- step_ok: {ok}",
        f"- step_fail: {fail}",
        f"- alert_count: {alerts.get('alert_count', 0)}",
        f"- heartbeat_age_sec: {hb_age}",
        f"- cycle_seconds: {cycle_seconds}",
        "",
        "## Bottlenecks",
    ]
    lines.extend([f"- {b}" for b in bottlenecks])
    lines.extend(["", "## Turbo Sequence"])
    for t in turbo_sequence:
        lines.append(f"- ({t['id']}) {t['step']} :: {t['action']} | gain={t['eta_gain']}")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
