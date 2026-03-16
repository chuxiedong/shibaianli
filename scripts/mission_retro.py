#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT_JSON = REPORTS / "mission_retro.json"
OUT_MD = REPORTS / "mission_retro.md"
CYCLES = REPORTS / "mission_cycles.csv"
ALERTS = REPORTS / "mission_alerts.json"
RUNTIME = REPORTS / "runtime_report.md"


def read_cycles(limit: int = 200):
    if not CYCLES.exists():
        return []
    with CYCLES.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


def read_alerts() -> dict:
    if not ALERTS.exists():
        return {"alert_count": 0, "alerts": [], "metrics": {}}
    try:
        return json.loads(ALERTS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"alert_count": 0, "alerts": [], "metrics": {}, "error": "bad json"}


def parse_runtime_lines() -> list[str]:
    if not RUNTIME.exists():
        return []
    return [ln for ln in RUNTIME.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cycles = read_cycles()
    alerts = read_alerts()
    runtime_lines = parse_runtime_lines()

    requested_actions = [
        "复刻目标站点结构与中文化呈现",
        "构建前后端与本地数据库",
        "建立持续更新跟踪机制",
        "支持容器化与云部署",
        "建立长时间连续执行与自愈能力",
        "增加安全收敛、备份、审计与告警",
    ]

    executed_actions = [
        "完成多路由同构页面、API 与 SQLite 数据层",
        "完成 watch/ingest/差异对比/镜像历史版本",
        "完成 docker + nginx + https(caddy) 部署方案",
        "完成 mission_6h + watchdog + runtime/health/alerts 面板",
        "完成备份/恢复/维护裁剪与系统模板（cron/systemd）",
    ]

    success_steps = sum(1 for r in cycles if r.get("result") == "ok")
    fail_steps = sum(1 for r in cycles if r.get("result") == "fail")

    payload = {
        "generated_at": now,
        "requested_actions": requested_actions,
        "executed_actions": executed_actions,
        "metrics": {
            "cycle_rows": len(cycles),
            "step_ok": success_steps,
            "step_fail": fail_steps,
            "alert_count": alerts.get("alert_count", 0),
        },
        "runtime_snapshot": runtime_lines[:20],
        "current_risks": [
            "当前环境可能对超长后台进程有会话回收限制，已通过 watchdog 自愈规避。",
            "来源站点网络波动时，抓取会降级到 fallback 列表。",
        ],
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Mission Retro",
        "",
        f"- generated_at: {now}",
        f"- step_ok: {success_steps}",
        f"- step_fail: {fail_steps}",
        f"- alert_count: {alerts.get('alert_count', 0)}",
        "",
        "## 被要求执行的动作",
    ]
    lines.extend([f"- {x}" for x in requested_actions])
    lines.extend(["", "## 已执行动作"])
    lines.extend([f"- {x}" for x in executed_actions])
    lines.extend(["", "## 当前风险"])
    lines.extend([f"- {x}" for x in payload["current_risks"]])
    lines.extend(["", "## Runtime Snapshot"])
    lines.extend(runtime_lines[:20] or ["- none"])

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
