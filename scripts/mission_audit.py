#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CYCLES = ROOT / "reports" / "mission_cycles.csv"
OUT_JSON = ROOT / "reports" / "mission_audit.json"
OUT_MD = ROOT / "reports" / "mission_audit.md"


def main() -> None:
    rows = []
    if CYCLES.exists():
        with CYCLES.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    total = len(rows)
    by_step = Counter(r.get("step", "") for r in rows)
    by_result = Counter(r.get("result", "") for r in rows)
    fail_rows = [r for r in rows if r.get("result") == "fail"]
    last = rows[-1] if rows else None

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_rows": total,
        "result_stats": dict(by_result),
        "step_stats": dict(by_step),
        "fail_rows": fail_rows[-20:],
        "last_row": last,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Mission Audit",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- total_rows: {total}",
        f"- ok: {by_result.get('ok', 0)}",
        f"- fail: {by_result.get('fail', 0)}",
        "",
        "## Step Stats",
    ]
    for step, cnt in sorted(by_step.items()):
        lines.append(f"- {step}: {cnt}")

    lines.extend(["", "## Last Row"])
    if last:
        lines.append(f"- {last}")
    else:
        lines.append("- none")

    lines.extend(["", "## Recent Fails"])
    if fail_rows:
        for r in fail_rows[-20:]:
            lines.append(f"- {r}")
    else:
        lines.append("- none")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
