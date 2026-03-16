#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data.db"
DEFAULT_SITEMAP = "https://www.loot-drop.io/sitemap.xml"
REPORT_DIR = ROOT / "reports"
MAX_URLS = int(os.getenv("MAX_URLS", "120"))
FALLBACK_URLS = [
    "https://www.loot-drop.io/",
    "https://www.loot-drop.io/why-they-fail",
    "https://www.loot-drop.io/deep-dives",
    "https://www.loot-drop.io/dashboard.html",
    "https://www.loot-drop.io/database-view",
    "https://www.loot-drop.io/rebuilds",
    "https://www.loot-drop.io/story.html",
    "https://www.loot-drop.io/roadmap.html",
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    conn.row_factory = sqlite3.Row
    return conn


def fetch_text(url: str, timeout: int = 12) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (LootDropCNWatcher)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def load_urls_from_sitemap(sitemap_url: str) -> list[str]:
    try:
        xml = fetch_text(sitemap_url)
        root = ET.fromstring(xml)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [n.text.strip() for n in root.findall("sm:url/sm:loc", ns) if n.text]
        if urls:
            priority = [
                "https://www.loot-drop.io/",
                "https://www.loot-drop.io/why-they-fail",
                "https://www.loot-drop.io/deep-dives",
                "https://www.loot-drop.io/dashboard.html",
                "https://www.loot-drop.io/database-view",
                "https://www.loot-drop.io/rebuilds",
                "https://www.loot-drop.io/story.html",
                "https://www.loot-drop.io/roadmap.html",
            ]
            ordered = []
            seen = set()
            for u in priority + urls:
                if u not in seen:
                    seen.add(u)
                    ordered.append(u)
            return ordered[:MAX_URLS]
    except (URLError, ET.ParseError, TimeoutError, ValueError):
        pass
    return FALLBACK_URLS[:MAX_URLS]


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS source_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_url TEXT NOT NULL,
          checksum TEXT NOT NULL,
          checked_at TEXT NOT NULL,
          changed INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS updates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          checked_at TEXT NOT NULL,
          changed_count INTEGER NOT NULL,
          summary TEXT NOT NULL
        );
        """
    )
    conn.commit()


def run_once() -> tuple[int, int, str, list[str]]:
    conn = get_conn()
    ensure_tables(conn)

    urls = load_urls_from_sitemap(DEFAULT_SITEMAP)
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed_count = 0
    changed_urls: list[str] = []

    for url in urls:
        try:
            html = fetch_text(url)
            ck = checksum(html)
        except Exception:
            continue

        prev = conn.execute(
            "SELECT checksum FROM source_snapshots WHERE source_url = ? ORDER BY id DESC LIMIT 1",
            (url,),
        ).fetchone()

        changed = 1 if (prev and prev["checksum"] != ck) else 0
        if changed:
            changed_count += 1
            changed_urls.append(url)

        conn.execute(
            """
            INSERT INTO source_snapshots (source_url, checksum, checked_at, changed)
            VALUES (?, ?, ?, ?)
            """,
            (url, ck, checked_at, changed),
        )

    summary = f"本次检查 {len(urls)} 个页面，检测到 {changed_count} 个页面发生变化。"
    conn.execute(
        "INSERT INTO updates (checked_at, changed_count, summary) VALUES (?, ?, ?)",
        (checked_at, changed_count, summary),
    )
    conn.commit()
    conn.close()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "last_update_report.md"
    lines = [
        f"# LootDrop 更新报告",
        "",
        f"- 检查时间: {checked_at}",
        f"- 检查页面数: {len(urls)}",
        f"- 变化页面数: {changed_count}",
        "",
        "## 发生变化的页面",
    ]
    if changed_urls:
        lines.extend([f"- {u}" for u in changed_urls])
    else:
        lines.append("- 无变化")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return len(urls), changed_count, checked_at, changed_urls


if __name__ == "__main__":
    total, changed, ts, urls = run_once()
    print(f"[{ts}] checked={total}, changed={changed}")
    if urls:
        print("changed_urls:")
        for item in urls:
            print(f"- {item}")
