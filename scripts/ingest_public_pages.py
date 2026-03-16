#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data.db"
SITEMAP = "https://www.loot-drop.io/sitemap.xml"
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


def fetch(url: str, timeout: int = 12) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (LootDropCNIngest)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def load_urls() -> list[str]:
    try:
        xml = fetch(SITEMAP)
        root = ET.fromstring(xml)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [n.text.strip() for n in root.findall("sm:url/sm:loc", ns) if n.text]
        if urls:
            return urls[:60]
    except Exception:
        pass
    return FALLBACK_URLS


def first_match(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return default
    return re.sub(r"\s+", " ", m.group(1)).strip()


def normalize_plain(html: str) -> str:
    no_script = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    no_style = re.sub(r"<style[\s\S]*?</style>", " ", no_script, flags=re.IGNORECASE)
    no_tags = re.sub(r"<[^>]+>", " ", no_style)
    return re.sub(r"\s+", " ", no_tags).strip()


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mirrored_pages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_url TEXT NOT NULL UNIQUE,
          page_title TEXT NOT NULL,
          page_description TEXT NOT NULL,
          h1_text TEXT NOT NULL,
          content_excerpt TEXT NOT NULL,
          checksum TEXT NOT NULL,
          fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mirrored_page_versions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_url TEXT NOT NULL,
          page_title TEXT NOT NULL,
          content_excerpt TEXT NOT NULL,
          checksum TEXT NOT NULL,
          fetched_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def ingest() -> tuple[int, int]:
    urls = load_urls()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    ensure_table(conn)

    ok = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for url in urls:
        try:
            html = fetch(url)
        except URLError:
            continue
        title = first_match(r"<title>(.*?)</title>", html, "(无标题)")
        desc = first_match(r"<meta[^>]*name=[\"']description[\"'][^>]*content=[\"'](.*?)[\"']", html, "")
        h1 = first_match(r"<h1[^>]*>(.*?)</h1>", html, "")
        plain = normalize_plain(html)
        excerpt = plain[:280]
        checksum = hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest()

        conn.execute(
            """
            INSERT INTO mirrored_pages
            (source_url, page_title, page_description, h1_text, content_excerpt, checksum, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_url) DO UPDATE SET
              page_title=excluded.page_title,
              page_description=excluded.page_description,
              h1_text=excluded.h1_text,
              content_excerpt=excluded.content_excerpt,
              checksum=excluded.checksum,
              fetched_at=excluded.fetched_at
            """,
            (url, title, desc, h1, excerpt, checksum, now),
        )

        prev = conn.execute(
            """
            SELECT checksum
            FROM mirrored_page_versions
            WHERE source_url = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (url,),
        ).fetchone()
        if not prev or prev[0] != checksum:
            conn.execute(
                """
                INSERT INTO mirrored_page_versions
                (source_url, page_title, content_excerpt, checksum, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url, title, excerpt, checksum, now),
            )
        ok += 1

    conn.commit()
    conn.close()
    return len(urls), ok


if __name__ == "__main__":
    total, ok = ingest()
    print(f"ingest finished: discovered={total}, stored={ok}")
