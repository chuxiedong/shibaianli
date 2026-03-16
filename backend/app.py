#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"
DB_PATH = ROOT / "data.db"
REPORT_DIR = ROOT / "reports"
MISSION_STATUS_FILE = REPORT_DIR / "mission_6h_status.md"
RUNTIME_REPORT_FILE = REPORT_DIR / "runtime_report.md"
MISSION_CYCLES_FILE = REPORT_DIR / "mission_cycles.csv"
WATCHDOG_EVENTS_FILE = REPORT_DIR / "watchdog_events.csv"
MISSION_ALERTS_FILE = REPORT_DIR / "mission_alerts.json"
MAINTENANCE_STATUS_FILE = REPORT_DIR / "maintenance_status.json"
MISSION_RETRO_FILE = REPORT_DIR / "mission_retro.json"
NEXT_ACTIONS_FILE = REPORT_DIR / "next_actions.json"
ACCELERATION_PLAN_FILE = REPORT_DIR / "acceleration_plan.json"
TURBO_LAST_RUN_FILE = REPORT_DIR / "turbo_last_run.json"
MISSION_LOCK_DIR = ROOT / ".mission_6h.lock"
MISSION_HEARTBEAT_FILE = MISSION_LOCK_DIR / "heartbeat"
MISSION_PID_FILE = MISSION_LOCK_DIR / "pid"

ROUTES = {
    "/": {
        "slug": "home",
        "title": "失败档案馆 | 1200+ 创业案例反思库",
        "hero_title": "失败\n档案馆",
        "hero_sub": "收录 1200+ 失败创业样本与数百亿美元资金去向，用失败反推下一代产品与策略。",
        "section_title": "最新失败案例",
        "section_sub": "按时间、烧钱规模、失败原因筛选",
    },
    "/why-they-fail": {
        "slug": "why",
        "title": "失败模式 | 框架化拆解",
        "hero_title": "失败\n模式库",
        "hero_sub": "7 大反模式 + 22 个行业细分，识别项目里的隐形雷区。",
        "section_title": "7 大失败反模式",
        "section_sub": "需求错判、获客失衡、单位经济学失真、时机错误、组织治理、监管、技术债",
    },
    "/deep-dives": {
        "slug": "dives",
        "title": "行业深潜 | 失败数据剖面",
        "hero_title": "行业\n深潜",
        "hero_sub": "SaaS、电商、金融科技、AI、Web3 等赛道的死亡剖面与复建窗口。",
        "section_title": "22 个行业失败分布",
        "section_sub": "查看行业融资密度、死亡周期、复活可能性",
    },
    "/dashboard": {
        "slug": "dashboard",
        "title": "交互仪表盘 | 创业尸检数据",
        "hero_title": "交互\n仪表盘",
        "hero_sub": "实时统计失败项目、资金损耗和复建机会。",
        "section_title": "核心指标",
        "section_sub": "总项目数、已烧资金、可重建机会、新增样本",
    },
    "/database-view": {
        "slug": "database",
        "title": "数据库视图 | 完整案例",
        "hero_title": "数据库\n视图",
        "hero_sub": "完整检索失败创业公司、融资额、死亡日期、失败原因。",
        "section_title": "完整数据库",
        "section_sub": "支持关键词、行业、烧钱规模、失败时间范围筛选",
    },
    "/rebuilds": {
        "slug": "rebuilds",
        "title": "重建计划 | 从失败中提炼机会",
        "hero_title": "重建\n计划",
        "hero_sub": "把失败业务模型拆解后，用当前技术和分发渠道重构。",
        "section_title": "可重建方向",
        "section_sub": "产品切口、商业模式、增长路径、MVP 建议",
    },
    "/story": {
        "slug": "story",
        "title": "项目故事 | 为什么做这个库",
        "hero_title": "项目\n故事",
        "hero_sub": "记录 1200+ 创业失败样本背后的方法论和研究过程。",
        "section_title": "建库历程",
        "section_sub": "数据来源、清洗策略、归因框架、更新节奏",
    },
    "/roadmap": {
        "slug": "roadmap",
        "title": "路线图 | 演进计划",
        "hero_title": "版本\n路线图",
        "hero_sub": "下一步：API、批量导出、自动归类、AI 复盘助手。",
        "section_title": "路线图",
        "section_sub": "已完成、进行中、计划中",
    },
    "/updates-report": {
        "slug": "updates",
        "title": "更新报告 | 源站变化追踪",
        "hero_title": "更新\n报告",
        "hero_sub": "持续跟踪源站页面变化，记录差异，生成可审计报告。",
        "section_title": "同步日志与变化页面",
        "section_sub": "最近 20 次更新检查记录与明细",
    },
}

NAV_ITEMS = [
    ("/", "首页"),
    ("/why-they-fail", "失败框架"),
    ("/deep-dives", "行业深潜"),
    ("/dashboard", "仪表盘"),
    ("/database-view", "案例库"),
    ("/rebuilds", "重建计划"),
    ("/story", "缘起"),
    ("/roadmap", "路线图"),
    ("/updates-report", "更新报告"),
]

FILTER_TAGS = [
    "SaaS",
    "金融科技",
    "电商",
    "AI",
    "Web3",
    "硬件",
    "消费",
    "医疗",
]

PAGE_MODULES = {
    "/": [
        ("失败清单", "按融资规模和时间查看死亡项目"),
        ("重建机会", "从失败模型中抽取可执行新机会"),
        ("资金尸检", "从资金消耗看商业模型崩点"),
    ],
    "/why-they-fail": [
        ("需求幻觉", "没有用户痛点却强推产品"),
        ("增长失衡", "投放增长无法覆盖获客成本"),
        ("组织断层", "团队和治理无法支撑扩张"),
    ],
    "/deep-dives": [
        ("SaaS 深潜", "订阅模式下的留存和扩张陷阱"),
        ("金融科技深潜", "合规、风控与增长冲突"),
        ("AI 深潜", "推理成本与用户价值失衡"),
    ],
    "/dashboard": [
        ("资金流速", "季度维度烧钱速度变化"),
        ("死亡波次", "行业别死亡高峰周期"),
        ("复活指数", "重建可行性评分模型"),
    ],
    "/database-view": [
        ("结构化检索", "多条件组合筛选失败样本"),
        ("字段透视", "行业、死亡时间、失败归因"),
        ("导出接口", "支持后续 CSV / API 导出"),
    ],
    "/rebuilds": [
        ("重建策略", "只保留价值链高复用环节"),
        ("MVP 切口", "低成本验证的新切入点"),
        ("商业重构", "定价、分发、服务交付再设计"),
    ],
    "/story": [
        ("数据来源", "公开新闻、融资数据库、社区归档"),
        ("分析框架", "失败归因 + 复建机会双轴"),
        ("版本演进", "从静态页面到可跟踪系统"),
    ],
    "/roadmap": [
        ("近期", "补全多页面像素级视觉对齐"),
        ("中期", "自动分类与失败原因聚类"),
        ("长期", "智能重建建议与策略模拟"),
    ],
    "/updates-report": [
        ("定时同步", "按计划拉取页面并记录摘要"),
        ("变更追踪", "按 URL 存储哈希差异"),
        ("报告归档", "生成可审计的同步报告"),
    ],
}

ROUTE_BLUEPRINTS = {
    "/": [
        "全站概览：样本规模、烧钱体量、最近变化",
        "入口矩阵：框架、深潜、数据库、重建",
        "本周新增：新收录死亡项目和复建候选",
    ],
    "/why-they-fail": [
        "失败象限：需求、增长、交付、治理",
        "反模式雷达：按风险强度排序",
        "行动镜像：你当前项目的同类风险",
    ],
    "/deep-dives": [
        "行业分布：赛道死亡密度对比",
        "融资-死亡周期：从融资到失败时长",
        "可复建程度：每赛道机会评分",
    ],
    "/dashboard": [
        "趋势折线：季度烧钱速度",
        "结构图：失败原因构成比例",
        "动态看板：最近抓取和变化页面",
    ],
    "/database-view": [
        "字段筛选：行业/日期/资金/原因",
        "批量检索：关键词 + 排序组合",
        "数据出口：后续可扩展 CSV/JSON",
    ],
    "/rebuilds": [
        "重建模板：保留价值、替换成本",
        "AI 重构：用现有模型降低交付成本",
        "市场切片：新分发渠道可行性",
    ],
    "/story": [
        "为什么做：避免重复踩坑",
        "怎么做：公开数据抓取与归因",
        "往哪走：镜像 + 追踪 + 决策系统",
    ],
    "/roadmap": [
        "短期：像素级结构对齐",
        "中期：自动归因和差异检测",
        "长期：云端多节点同步",
    ],
    "/updates-report": [
        "监控计划：定时抓取 sitemap 和核心路由",
        "差异判定：URL 级 checksum 对比",
        "审计输出：每次同步报告归档",
    ],
}

ROUTE_SPECIFIC_SECTIONS = {
    "/why-they-fail": """
    <section class="panel route-only route-failures">
      <h3>失败反模式矩阵</h3>
      <div class="failure-matrix">
        <article class="failure-cell"><h4>需求错位</h4><p>解决了“有趣”但不愿付费的问题，市场反馈与产品锚点脱节。</p></article>
        <article class="failure-cell"><h4>获客过载</h4><p>CAC 长期高于 LTV，营销推进反而加速亏损。</p></article>
        <article class="failure-cell"><h4>交付断裂</h4><p>承诺与体验存在结构性偏差，退款与流失放大成本。</p></article>
        <article class="failure-cell"><h4>治理失序</h4><p>优先级摇摆、权责模糊，组织熵增吞噬资金与时间。</p></article>
      </div>
    </section>
    <section class="panel route-only route-failures">
      <h3>风险自测</h3>
      <div class="risk-checklist">
        <label><input type="checkbox" /> 留存连续 3 期下滑，尚无修复动作</label>
        <label><input type="checkbox" /> 依赖单一渠道，渠道成本占比 >60%</label>
        <label><input type="checkbox" /> 毛利率低于 30%，仍在加大投放</label>
        <label><input type="checkbox" /> 核心功能 30 天无迭代，Roadmap 无验证计划</label>
      </div>
    </section>
    """,
    "/deep-dives": """
    <section class="panel route-only route-dives">
      <h3>行业深潜图谱</h3>
      <div class="dive-lanes">
        <article class="dive-lane"><h4>SaaS</h4><p>常见死因：试用拉新大于续费驱动，销售成本挤压毛利。</p></article>
        <article class="dive-lane"><h4>金融科技</h4><p>常见死因：合规成本抬升，风控模型失真导致坏账螺旋。</p></article>
        <article class="dive-lane"><h4>电商</h4><p>常见死因：履约与退货成本侵蚀贡献毛利，渠道依赖度过高。</p></article>
        <article class="dive-lane"><h4>AI</h4><p>常见死因：推理成本与价格倒挂，场景刚需度不足。</p></article>
      </div>
    </section>
    <section class="panel route-only route-dives">
      <h3>赛道热区</h3>
      <div class="heat-strip">
        <span data-level="8">AI 工具</span>
        <span data-level="6">开发者工具</span>
        <span data-level="7">B2B SaaS</span>
        <span data-level="4">消费硬件</span>
        <span data-level="5">Web3</span>
      </div>
    </section>
    """,
    "/dashboard": """
    <section class="panel route-only route-dashboard">
      <h3>看板视图</h3>
      <div class="dashboard-grid">
        <article class="dash-card"><h4>季度烧钱趋势</h4><canvas id="burn-chart" height="120"></canvas></article>
        <article class="dash-card"><h4>失败原因分布</h4><canvas id="reason-chart" height="120"></canvas></article>
        <article class="dash-card"><h4>重建机会评分</h4><canvas id="rebuild-chart" height="120"></canvas></article>
      </div>
    </section>
    <section class="panel route-only route-dashboard">
      <h3>实时事件流</h3>
      <div class="event-stream" id="event-stream">
        <div class="event-item">系统初始化完成，等待最新更新记录...</div>
      </div>
    </section>
    """,
    "/rebuilds": """
    <section class="panel route-only route-rebuilds">
      <h3>重建策略速写</h3>
      <div class="dive-lanes">
        <article class="dive-lane"><h4>价值链复用</h4><p>保留数据、用户、分销资产，替换亏损环节。</p></article>
        <article class="dive-lane"><h4>MVP 切口</h4><p>缩小交付面，聚焦“价值最高、成本最低”的 1-2 个场景。</p></article>
        <article class="dive-lane"><h4>新分发</h4><p>用社区/生态分发替代高 CAC 渠道，提高自然留存。</p></article>
        <article class="dive-lane"><h4>AI 降本</h4><p>用自动化降低售前、交付与客服的人力成本。</p></article>
      </div>
    </section>
    """,
}


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    conn.row_factory = sqlite3.Row
    return conn


def read_mission_cycles(limit: int = 30) -> list[dict[str, str]]:
    if not MISSION_CYCLES_FILE.exists():
        return []
    lines = MISSION_CYCLES_FILE.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) <= 1:
        return []
    header = lines[0].split(",")
    rows: list[dict[str, str]] = []
    for line in lines[-limit:]:
        parts = line.split(",", maxsplit=len(header) - 1)
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


def read_csv_rows(path: Path, limit: int = 30) -> list[dict[str, str]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) <= 1:
        return []
    header = lines[0].split(",")
    rows: list[dict[str, str]] = []
    for line in lines[-limit:]:
        parts = line.split(",", maxsplit=len(header) - 1)
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


def init_db() -> None:
    conn = db_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS startups (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          industry TEXT NOT NULL,
          burned_billion REAL NOT NULL,
          died_on TEXT NOT NULL,
          failure_reason TEXT NOT NULL,
          rebuild_score INTEGER NOT NULL
        );

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

    count = conn.execute("SELECT COUNT(*) AS c FROM startups").fetchone()["c"]
    if count == 0:
        conn.executemany(
            """
            INSERT INTO startups (name, industry, burned_billion, died_on, failure_reason, rebuild_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("Quibi", "流媒体", 1.75, "2020-12-01", "产品定位和渠道策略失误", 81),
                ("Beepi", "二手车", 0.15, "2017-02-01", "单位经济学不成立", 70),
                ("Jawbone", "可穿戴", 0.93, "2017-06-01", "硬件毛利与运营失衡", 67),
                ("Zirtual", "人力服务", 0.005, "2015-08-10", "现金流管理失败", 75),
                ("Powa", "电商", 2.70, "2016-02-01", "过度融资与低转化", 55),
                ("FTX", "加密金融", 8.00, "2022-11-11", "治理失控与合规问题", 20),
                ("WeWork", "共享办公", 22.00, "2023-11-06", "扩张过快与组织治理问题", 62),
            ],
        )
        conn.commit()
    conn.close()


def render_route_blueprint(path: str) -> str:
    items = ROUTE_BLUEPRINTS.get(path, ROUTE_BLUEPRINTS["/"])
    cards = "".join(
        [
            (
                '<article class="route-card">'
                f"<h4>模块 {idx + 1}</h4>"
                f"<p>{text}</p>"
                "</article>"
            )
            for idx, text in enumerate(items)
        ]
    )
    return f"""
    <section class="panel">
      <h3>页面蓝图（{ROUTES[path]['slug']}）</h3>
      <div class="route-grid">
        {cards}
      </div>
    </section>
    """


def render_page(path: str) -> str:
    cfg = ROUTES[path]
    modules = PAGE_MODULES.get(path, PAGE_MODULES["/"])
    nav = "\n".join(
        [
            f'<a href="{href}" class="nav-pill {"active" if href == path else ""}">{label}</a>'
            for href, label in NAV_ITEMS
        ]
    )
    modules_html = "".join(
        [
            (
                '<article class="module-card">'
                f"<h4>{title}</h4>"
                f"<p>{desc}</p>"
                "</article>"
            )
            for title, desc in modules
        ]
    )
    route_specific_html = ROUTE_SPECIFIC_SECTIONS.get(path, "")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{cfg['title']}</title>
  <meta name="description" content="创业失败案例中文镜像站，包含失败原因、资金损耗与重建路径。" />
  <link rel="stylesheet" href="/assets/style.css" />
</head>
<body class="has-sidebar">
  <header class="main-mobile-header">
    <button class="hamburger-btn" id="hamburger-btn">☰</button>
    <span class="mobile-title">创业坟场</span>
    <a href="/" class="skull-icon">💀</a>
  </header>
  <div class="drawer-overlay" id="drawer-overlay"></div>

  <canvas id="hero-canvas"></canvas>
  <header class="hero">
    <div class="hero-content">
      <div class="hero-badge">💀 失败档案 · 1200+ 样本</div>
      <h1 class="hero-title">{cfg['hero_title'].replace(chr(10), '<br>')}</h1>
      <p class="hero-subtitle">{cfg['hero_sub']}</p>
      <div class="hero-live-data">
        <span class="live-dot"></span>
        <span class="live-label">实时数据</span>
        <span class="live-schedule">每周二 / 周五同步抓取 + 版本归档</span>
      </div>

      <div class="hero-grid">
        <a href="/why-they-fail" class="hero-item">失败框架</a>
        <a href="/deep-dives" class="hero-item">行业深潜</a>
        <a href="/dashboard" class="hero-item">交互仪表盘</a>
        <a href="/database-view" class="hero-item">数据库视图</a>
        <a href="/rebuilds" class="hero-item">重建计划</a>
        <a href="/roadmap" class="hero-item">路线图</a>
        <a href="/updates-report" class="hero-item">更新报告</a>
      </div>
    </div>
  </header>
  <div class="ticker-strip">
    <div class="ticker-track" id="ticker-track"></div>
  </div>

  <div class="main-layout below-hero">
    <aside class="main-sidebar" id="main-sidebar">
      <div class="sidebar-section nav-section">
        <div class="section-header"><span>导航</span></div>
        <div class="nav-pills">{nav}</div>
      </div>
      <div class="sidebar-section search-section">
        <input id="sidebar-search-input" class="sidebar-search-input" placeholder="搜索案例、行业、失败原因" />
      </div>
      <div class="sidebar-section sort-section">
        <div class="sidebar-sort-btns">
          <button class="sidebar-sort-btn active" data-sort="default">最新</button>
          <button class="sidebar-sort-btn" data-sort="burned">烧钱最多</button>
          <button class="sidebar-sort-btn" data-sort="recent">最近死亡</button>
        </div>
      </div>
      <div class="sidebar-section filter-section">
        <div class="section-header"><span>筛选标签</span></div>
        <div class="filter-tree">
          {"".join(f'<button class="filter-tag" data-tag="{tag}">{tag}</button>' for tag in FILTER_TAGS)}
        </div>
      </div>
    </aside>

    <main class="content">
      <section class="panel">
        <h2>{cfg['section_title']}</h2>
        <p>{cfg['section_sub']}</p>
      </section>
      <section class="panel" id="stats-panel">
        <h3>关键统计</h3>
        <div class="stats-grid">
          <div class="stat-card"><span>项目总数</span><strong id="stat-total">-</strong></div>
          <div class="stat-card"><span>累计烧钱(十亿美元)</span><strong id="stat-burned">-</strong></div>
          <div class="stat-card"><span>平均重建分</span><strong id="stat-rebuild">-</strong></div>
          <div class="stat-card"><span>最近更新</span><strong id="stat-updated">-</strong></div>
        </div>
      </section>
      <section class="panel">
        <h3>失败样本</h3>
        <div id="startup-list" class="startup-list"></div>
      </section>
      <section class="panel">
        <h3>页面模块</h3>
        <div class="module-grid">
          {modules_html}
        </div>
      </section>
      {render_route_blueprint(path)}
      {route_specific_html}
      <section class="panel">
        <h3>源站更新跟踪</h3>
        <div id="updates-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>变化页面明细</h3>
        <div id="changes-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>公开页面镜像索引</h3>
        <div id="mirror-pages-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>镜像差异对比</h3>
        <div id="mirror-diff-box" class="diff-box">请选择一个页面查看最近两版差异。</div>
      </section>
      <section class="panel">
        <h3>任务运行状态</h3>
        <div id="mission-runtime-box" class="diff-box">等待加载任务状态...</div>
      </section>
      <section class="panel">
        <h3>最近执行轨迹</h3>
        <div id="mission-cycles-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>任务告警</h3>
        <div id="mission-alerts-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>Watchdog 事件</h3>
        <div id="watchdog-events-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>维护状态</h3>
        <div id="maintenance-box" class="diff-box">等待维护状态...</div>
      </section>
      <section class="panel">
        <h3>任务复盘</h3>
        <div id="retro-box" class="diff-box">等待复盘数据...</div>
      </section>
      <section class="panel">
        <h3>下一步动作</h3>
        <div id="next-actions-list" class="updates-list"></div>
      </section>
      <section class="panel">
        <h3>终级加速推演</h3>
        <div id="acceleration-box" class="diff-box">等待加速推演...</div>
      </section>
      <section class="panel">
        <h3>Turbo 最近执行</h3>
        <div id="turbo-box" class="diff-box">等待 turbo 结果...</div>
      </section>
    </main>
  </div>

  <script src="/assets/app.js"></script>
</body>
</html>
"""


class AppHandler(BaseHTTPRequestHandler):
    server_version = "LootDropCN/0.1"

    def _json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, body: str, status: int = 200, ctype: str = "text/html; charset=utf-8") -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._json({"ok": True, "time": datetime.now().isoformat()})
            return

        if path == "/api/stats":
            conn = db_conn()
            row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       ROUND(COALESCE(SUM(burned_billion), 0), 2) AS burned,
                       ROUND(COALESCE(AVG(rebuild_score), 0), 1) AS rebuild
                FROM startups
                """
            ).fetchone()
            upd = conn.execute("SELECT checked_at FROM updates ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()
            self._json(
                {
                    "total": row["total"],
                    "burned": row["burned"],
                    "rebuild": row["rebuild"],
                    "updated": upd["checked_at"] if upd else "尚未同步",
                }
            )
            return

        if path == "/api/startups":
            qs = parse_qs(parsed.query)
            q = (qs.get("search", [""])[0] or "").strip()
            sort = (qs.get("sort", ["default"])[0] or "default").strip()

            order_clause = {
                "burned": "burned_billion DESC",
                "recent": "died_on DESC",
            }.get(sort, "id DESC")

            conn = db_conn()
            if q:
                rows = conn.execute(
                    f"""
                    SELECT * FROM startups
                    WHERE name LIKE ? OR industry LIKE ? OR failure_reason LIKE ?
                    ORDER BY {order_clause}
                    LIMIT 100
                    """,
                    (f"%{q}%", f"%{q}%", f"%{q}%"),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT * FROM startups ORDER BY {order_clause} LIMIT 100"
                ).fetchall()
            conn.close()
            self._json([dict(r) for r in rows])
            return

        if path == "/api/updates":
            conn = db_conn()
            rows = conn.execute(
                "SELECT checked_at, changed_count, summary FROM updates ORDER BY id DESC LIMIT 20"
            ).fetchall()
            conn.close()
            self._json([dict(r) for r in rows])
            return

        if path == "/api/ticker":
            conn = db_conn()
            rows = conn.execute(
                """
                SELECT name, burned_billion, industry
                FROM startups
                ORDER BY id DESC
                LIMIT 20
                """
            ).fetchall()
            conn.close()
            payload = [
                f"{r['name']} · {r['industry']} · ${r['burned_billion']}B burned"
                for r in rows
            ]
            self._json(payload)
            return

        if path == "/api/changed-pages":
            conn = db_conn()
            rows = conn.execute(
                """
                SELECT checked_at, source_url
                FROM source_snapshots
                WHERE changed = 1
                ORDER BY id DESC
                LIMIT 60
                """
            ).fetchall()
            conn.close()
            self._json([dict(r) for r in rows])
            return

        if path == "/api/mirrored-pages":
            conn = db_conn()
            rows = conn.execute(
                """
                SELECT source_url, page_title, h1_text, content_excerpt, fetched_at
                FROM mirrored_pages
                ORDER BY id DESC
                LIMIT 30
                """
            ).fetchall()
            conn.close()
            self._json([dict(r) for r in rows])
            return

        if path == "/api/mirror-diff":
            qs = parse_qs(parsed.query)
            source_url = (qs.get("url", [""])[0] or "").strip()
            if not source_url:
                self._json({"error": "missing url"}, status=400)
                return
            conn = db_conn()
            rows = conn.execute(
                """
                SELECT source_url, page_title, content_excerpt, checksum, fetched_at
                FROM mirrored_page_versions
                WHERE source_url = ?
                ORDER BY id DESC
                LIMIT 2
                """,
                (source_url,),
            ).fetchall()
            conn.close()
            if not rows:
                self._json({"found": False, "message": "no version data"})
                return
            current = dict(rows[0])
            previous = dict(rows[1]) if len(rows) > 1 else None
            changed = bool(previous and previous["checksum"] != current["checksum"])
            self._json(
                {
                    "found": True,
                    "changed": changed,
                    "current": current,
                    "previous": previous,
                }
            )
            return

        if path == "/api/mission-runtime":
            payload = {
                "has_status": MISSION_STATUS_FILE.exists(),
                "has_runtime_report": RUNTIME_REPORT_FILE.exists(),
                "status_markdown": MISSION_STATUS_FILE.read_text(encoding="utf-8") if MISSION_STATUS_FILE.exists() else "",
                "runtime_markdown": RUNTIME_REPORT_FILE.read_text(encoding="utf-8") if RUNTIME_REPORT_FILE.exists() else "",
            }
            self._json(payload)
            return

        if path == "/api/mission-cycles":
            qs = parse_qs(parsed.query)
            try:
                limit = int((qs.get("limit", ["30"])[0] or "30").strip())
            except ValueError:
                limit = 30
            limit = max(1, min(limit, 200))
            rows = read_mission_cycles(limit)
            self._json(rows)
            return

        if path == "/api/watchdog-events":
            qs = parse_qs(parsed.query)
            try:
                limit = int((qs.get("limit", ["30"])[0] or "30").strip())
            except ValueError:
                limit = 30
            limit = max(1, min(limit, 200))
            rows = read_csv_rows(WATCHDOG_EVENTS_FILE, limit)
            self._json(rows)
            return

        if path == "/api/mission-health":
            now = int(datetime.now().timestamp())
            has_lock = MISSION_LOCK_DIR.exists()
            heartbeat = None
            heartbeat_age = None
            stale_threshold = 1800
            if MISSION_HEARTBEAT_FILE.exists():
                try:
                    heartbeat = int(MISSION_HEARTBEAT_FILE.read_text(encoding="utf-8").strip())
                    heartbeat_age = now - heartbeat
                except ValueError:
                    heartbeat = None
                    heartbeat_age = None

            cycles = read_mission_cycles(100)
            fail_count = sum(1 for r in cycles if r.get("result") == "fail")
            last_step = cycles[-1] if cycles else None
            status = "stopped"
            if has_lock and heartbeat_age is not None:
                status = "healthy" if heartbeat_age <= stale_threshold else "stale"
            elif has_lock:
                status = "unknown"

            payload = {
                "status": status,
                "has_lock": has_lock,
                "heartbeat_epoch": heartbeat,
                "heartbeat_age_sec": heartbeat_age,
                "stale_threshold_sec": stale_threshold,
                "recent_fail_count": fail_count,
                "recent_total_steps": len(cycles),
                "last_step": last_step,
                "pid": MISSION_PID_FILE.read_text(encoding="utf-8").strip() if MISSION_PID_FILE.exists() else None,
            }
            self._json(payload)
            return

        if path == "/api/mission-alerts":
            if not MISSION_ALERTS_FILE.exists():
                self._json({"generated_at": None, "alert_count": 0, "alerts": [], "metrics": {}})
                return
            try:
                payload = json.loads(MISSION_ALERTS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"generated_at": None, "alert_count": 0, "alerts": [], "metrics": {}, "error": "bad json"}
            self._json(payload)
            return

        if path == "/api/maintenance-status":
            if not MAINTENANCE_STATUS_FILE.exists():
                self._json({"generated_at": None, "logs": [], "csv": [], "backups": {}, "sizes": {}})
                return
            try:
                payload = json.loads(MAINTENANCE_STATUS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"generated_at": None, "error": "bad json"}
            self._json(payload)
            return

        if path == "/api/mission-retro":
            if not MISSION_RETRO_FILE.exists():
                self._json({"generated_at": None, "requested_actions": [], "executed_actions": [], "metrics": {}, "current_risks": []})
                return
            try:
                payload = json.loads(MISSION_RETRO_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"generated_at": None, "error": "bad json"}
            self._json(payload)
            return

        if path == "/api/next-actions":
            if not NEXT_ACTIONS_FILE.exists():
                self._json({"generated_at": None, "count": 0, "actions": []})
                return
            try:
                payload = json.loads(NEXT_ACTIONS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"generated_at": None, "count": 0, "actions": [], "error": "bad json"}
            self._json(payload)
            return

        if path == "/api/acceleration-plan":
            if not ACCELERATION_PLAN_FILE.exists():
                self._json({"generated_at": None, "efficiency_score": None, "bottlenecks": [], "turbo_sequence": []})
                return
            try:
                payload = json.loads(ACCELERATION_PLAN_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"generated_at": None, "error": "bad json"}
            self._json(payload)
            return

        if path == "/api/turbo-last-run":
            if not TURBO_LAST_RUN_FILE.exists():
                self._json({"run_at": None, "elapsed_seconds": None, "steps": {}})
                return
            try:
                payload = json.loads(TURBO_LAST_RUN_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"run_at": None, "error": "bad json"}
            self._json(payload)
            return

        if path.startswith("/assets/"):
            file_path = ASSETS_DIR / path.removeprefix("/assets/")
            if not file_path.exists() or not file_path.is_file():
                self._text("Not Found", status=404, ctype="text/plain; charset=utf-8")
                return
            ctype = "text/plain; charset=utf-8"
            if file_path.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif file_path.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            self._text(file_path.read_text(encoding="utf-8"), ctype=ctype)
            return

        if path.startswith("/reports/"):
            file_path = REPORT_DIR / path.removeprefix("/reports/")
            if not file_path.exists() or not file_path.is_file():
                self._text("Not Found", status=404, ctype="text/plain; charset=utf-8")
                return
            self._text(file_path.read_text(encoding="utf-8"), ctype="text/markdown; charset=utf-8")
            return

        alias_routes = {
            "/dashboard.html": "/dashboard",
            "/story.html": "/story",
            "/roadmap.html": "/roadmap",
            "/ideas.html": "/",
            "/lists.html": "/",
            "/insights.html": "/",
        }
        if path in alias_routes:
            path = alias_routes[path]

        normalized = path.rstrip("/") or "/"
        if normalized in ROUTES:
            self._text(render_page(normalized), status=HTTPStatus.OK)
            return

        self._text("页面不存在", status=404)


def main() -> None:
    init_db()
    port = int(os.getenv("PORT", "8090"))
    server = HTTPServer(("127.0.0.1", port), AppHandler)
    print(f"LootDrop CN running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
