#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ALERTS_FILE = REPORTS / "mission_alerts.json"
RUNTIME_FILE = REPORTS / "runtime_report.md"
OUT_JSON = REPORTS / "next_actions.json"
OUT_MD = REPORTS / "next_actions.md"


def load_alerts() -> dict:
    if not ALERTS_FILE.exists():
        return {"alert_count": 0, "alerts": [], "metrics": {}}
    try:
        return json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"alert_count": 0, "alerts": [], "metrics": {}}


def load_runtime() -> str:
    if not RUNTIME_FILE.exists():
        return ""
    return RUNTIME_FILE.read_text(encoding="utf-8")


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alerts = load_alerts()
    runtime = load_runtime()

    actions = []

    if alerts.get("alert_count", 0) > 0:
        actions.append({
            "priority": "P0",
            "title": "处理 mission 告警",
            "detail": "根据 mission_alerts 中的 critical/warning 条目逐项修复并验证。",
            "trigger": "alert_count>0",
        })

    if "heartbeat_age_sec" in runtime and "heartbeat_age_sec: 0" not in runtime:
        actions.append({
            "priority": "P1",
            "title": "确认 heartbeat 在阈值内",
            "detail": "检查 watchdog 是否持续刷新 runtime_report，heartbeat_age_sec 不应持续增长超过阈值。",
            "trigger": "runtime_report",
        })

    actions.extend([
        {
            "priority": "P1",
            "title": "执行下一轮源站抓取核验",
            "detail": "运行 watch_updates + ingest_public_pages，确认 mission_cycles 追加成功。",
            "trigger": "continuous",
        },
        {
            "priority": "P2",
            "title": "检查备份与恢复演练",
            "detail": "创建新备份并用 restore_backup 在隔离路径演练恢复。",
            "trigger": "daily",
        },
        {
            "priority": "P2",
            "title": "发布前核查云部署参数",
            "detail": "确认 DOMAIN/ACME_EMAIL、端口与防火墙策略，再执行 deploy_https.sh。",
            "trigger": "pre-release",
        },
    ])

    payload = {
        "generated_at": now,
        "count": len(actions),
        "actions": actions,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# Next Actions", "", f"- generated_at: {now}", f"- count: {len(actions)}", "", "## Actions"]
    for a in actions:
        lines.append(f"- [{a['priority']}] {a['title']} :: {a['detail']} (trigger={a['trigger']})")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
