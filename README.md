# LootDrop 中文同构站（本地）

> 说明：该项目按目标站点的信息架构与交互分区进行中文实现，用于研究和本地演示，不包含源站私有代码。

## 本地启动

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
python3 backend/app.py
```

打开：`http://127.0.0.1:8090`（直连应用）

## 路由

- `/`
- `/why-they-fail`
- `/deep-dives`
- `/dashboard`
- `/database-view`
- `/rebuilds`
- `/story`
- `/roadmap`

## API

- `/api/health`
- `/api/stats`
- `/api/startups?search=&sort=default|burned|recent`
- `/api/updates`
- `/api/changed-pages`
- `/api/ticker`
- `/api/mirrored-pages`
- `/api/mirror-diff?url=<source_url>`
- `/api/mission-runtime`
- `/api/mission-cycles?limit=20`
- `/api/mission-health`
- `/api/mission-alerts`
- `/api/watchdog-events?limit=20`
- `/api/maintenance-status`
- `/api/mission-retro`
- `/api/next-actions`
- `/api/acceleration-plan`
- `/api/turbo-last-run`

## 数据库

SQLite 文件：`/Users/somalia/Documents/New project 2/lootdrop_clone/data.db`

主要表：

- `startups`（案例数据）
- `source_snapshots`（源站页面快照哈希）
- `updates`（每次同步汇总）

## 持续跟踪目标站更新

手动执行一次：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
python3 scripts/watch_updates.py
```

抓取公开页面并入库：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
python3 scripts/ingest_public_pages.py
```

该脚本会维护两张表：
- `mirrored_pages`：每个 URL 最新版本
- `mirrored_page_versions`：URL 历史版本（用于差异对比）

建议用 cron（每周二、周五）：

```cron
0 10 * * 2,5 cd "/Users/somalia/Documents/New project 2/lootdrop_clone" && /usr/bin/python3 scripts/watch_updates.py
```

执行后，前端 `/api/updates` 会显示同步记录。

更新报告文件：`/Users/somalia/Documents/New project 2/lootdrop_clone/reports/last_update_report.md`

## Docker 部署

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
docker compose up -d --build
```

访问：`http://127.0.0.1:8080`（通过 Nginx 反向代理）

说明：`docker compose` 会同时启动：
- `nginx`（入口代理）
- `lootdrop-cn`（Web 服务，内部 8090）
- `updater`（后台自动同步，默认每 6 小时执行一次；包含更新检测 + 页面抓取入库）

安全默认项：
- Nginx 安全头（CSP/XFO/nosniff/referrer-policy）
- `/api/` 基础限流
- 常见扫描器 UA 拦截 + 常见攻击路径拦截
- 容器 `no-new-privileges` + `cap_drop: ALL`
- `read_only` 根文件系统 + `tmpfs` 运行目录

## 云主机一键部署

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/deploy_cloud.sh
```

## HTTPS（域名）部署

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
DOMAIN=your.domain.com ACME_EMAIL=ops@your.domain.com ./scripts/deploy_https.sh
```

HTTPS 覆盖文件：`/Users/somalia/Documents/New project 2/lootdrop_clone/docker-compose.https.yml`

## 数据备份

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/backup_data.sh
```

备份输出目录：`/Users/somalia/Documents/New project 2/lootdrop_clone/backups`

默认仅保留最近 14 份备份，可调整：

```bash
BACKUP_KEEP=30 ./scripts/backup_data.sh
```

## 自动备份循环（可选）

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
BACKUP_INTERVAL_SECONDS=43200 BACKUP_KEEP=20 ./scripts/backup_loop.sh
```

## 备份恢复

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/restore_backup.sh "/path/to/lootdrop-backup-YYYYmmdd-HHMMSS.tar.gz"
```

## 连续执行 6 小时任务

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
DURATION_SECONDS=21600 CYCLE_SECONDS=900 BACKUP_EVERY_N=4 BACKUP_KEEP=14 ./scripts/mission_6h.sh
```

后台启动（推荐）：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
MAX_URLS=80 DURATION_SECONDS=21600 CYCLE_SECONDS=900 ./scripts/start_mission.sh
```

查看任务状态：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/mission_status.sh
```

生成运行快照报告：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/runtime_report.sh
```

输出文件：`/Users/somalia/Documents/New project 2/lootdrop_clone/reports/runtime_report.md`

生成任务审计报告：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
python3 scripts/mission_audit.py
```

输出文件：
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_audit.json`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_audit.md`

自动告警输出（watchdog 每轮自动更新）：
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_alerts.json`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_alerts.md`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/watchdog_events.csv`

手动生成（可选）：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
python3 scripts/mission_alerts.py
```

维护输出（watchdog 按周期自动更新）：
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/maintenance_status.json`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/maintenance_status.md`

复盘与下一步输出（watchdog 按周期自动更新）：
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_retro.json`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_retro.md`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/next_actions.json`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/next_actions.md`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/acceleration_plan.json`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/acceleration_plan.md`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/reports/turbo_last_run.json`

手动生成（可选）：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
python3 scripts/mission_retro.py
python3 scripts/next_actions.py
python3 scripts/acceleration_engine.py
```

终级加速执行（可选）：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
MAX_URLS=60 ./scripts/turbo_execute.sh
```

停止任务：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/stop_mission.sh
```

输出：
- 运行日志：`/Users/somalia/Documents/New project 2/lootdrop_clone/logs/mission_6h.log`
- 状态文件：`/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_6h_status.md`
- 步骤轨迹：`/Users/somalia/Documents/New project 2/lootdrop_clone/reports/mission_cycles.csv`

手动步骤记账（将手工动作纳入复盘轨迹）：

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/record_manual_step.sh watch_updates_manual ok "manual verification run" manual
```

## systemd 模板（Linux 服务器）

模板文件：
- `/Users/somalia/Documents/New project 2/lootdrop_clone/deploy/systemd/lootdrop-mission.service`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/deploy/systemd/lootdrop-backup.service`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/deploy/systemd/lootdrop-backup.timer`
- `/Users/somalia/Documents/New project 2/lootdrop_clone/deploy/systemd/lootdrop-watchdog.service`

示例安装：

```bash
PROJECT_DIR="/path/to/lootdrop_clone"
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" deploy/systemd/lootdrop-backup.service | sudo tee /etc/systemd/system/lootdrop-backup.service >/dev/null
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" deploy/systemd/lootdrop-mission.service | sudo tee /etc/systemd/system/lootdrop-mission.service >/dev/null
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" deploy/systemd/lootdrop-watchdog.service | sudo tee /etc/systemd/system/lootdrop-watchdog.service >/dev/null
sudo cp deploy/systemd/lootdrop-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lootdrop-backup.timer
sudo systemctl enable --now lootdrop-watchdog.service
```

## cron 模板

模板文件：`/Users/somalia/Documents/New project 2/lootdrop_clone/deploy/cron/crontab.example`
watchdog 模板：`/Users/somalia/Documents/New project 2/lootdrop_clone/deploy/cron/mission-watchdog.example`

## 长时同步（可选）

```bash
cd "/Users/somalia/Documents/New project 2/lootdrop_clone"
./scripts/sync_loop.sh
```

默认每 6 小时同步一次，可通过环境变量调整：

```bash
INTERVAL_SECONDS=7200 ./scripts/sync_loop.sh
```
