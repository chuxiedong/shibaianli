async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function renderStartups(items) {
  const list = document.getElementById('startup-list');
  if (!list) return;
  if (!items.length) {
    list.innerHTML = '<div class="startup-card">没有匹配结果</div>';
    return;
  }

  list.innerHTML = items.map((s) => `
    <article class="startup-card">
      <h4>${s.name}</h4>
      <div class="meta">行业：${s.industry} | 烧钱：$${s.burned_billion}B | 失败日期：${s.died_on}</div>
      <p>${s.failure_reason}</p>
      <div class="meta">重建分：${s.rebuild_score}/100</div>
    </article>
  `).join('');
}

function renderUpdates(items) {
  const list = document.getElementById('updates-list');
  if (!list) return;
  if (!items.length) {
    list.innerHTML = '<div class="update-card muted">尚无同步记录，等待下一次抓取窗口。</div>';
    return;
  }

  list.innerHTML = items.map((u) => `
    <article class="update-card">
      <div class="update-head">
        <span class="badge time">${u.checked_at}</span>
        <span class="badge delta">${u.changed_count} 个页面有变化</span>
      </div>
      <p class="update-summary">${u.summary}</p>
    </article>
  `).join('');
}

function renderChanges(items) {
  const list = document.getElementById('changes-list');
  if (!list) return;
  if (!items.length) {
    list.innerHTML = '<div class="update-card muted">最近没有检测到页面变化。</div>';
    return;
  }

  list.innerHTML = items.map((u) => `
    <article class="update-card">
      <div class="update-head">
        <span class="badge time">${u.checked_at}</span>
        <span class="badge changed">内容变动</span>
      </div>
      <div class="link-line"><a href="${u.source_url}" target="_blank" rel="noreferrer">${u.source_url}</a></div>
    </article>
  `).join('');
}

function renderMirrorPages(items) {
  const list = document.getElementById('mirror-pages-list');
  if (!list) return;
  if (!items.length) {
    list.innerHTML = '<div class="update-card">暂无镜像页面数据，可先运行抓取脚本。</div>';
    return;
  }
  list.innerHTML = items.map((p) => `
    <article class="update-card">
      <div class="update-head">
        <span class="badge time">${p.fetched_at}</span>
        <span class="badge mirror">镜像</span>
      </div>
      <div class="link-line"><a href="${p.source_url}" target="_blank" rel="noreferrer">${p.page_title}</a></div>
      <p class="meta">${p.h1_text || p.content_excerpt}</p>
      <button class="diff-btn" data-url="${p.source_url}">查看最近差异</button>
    </article>
  `).join('');
  bindMirrorDiffButtons();
}

async function loadStats() {
  const s = await fetchJson('/api/stats');
  document.getElementById('stat-total').textContent = s.total;
  document.getElementById('stat-burned').textContent = `$${s.burned}B`;
  document.getElementById('stat-rebuild').textContent = s.rebuild;
  document.getElementById('stat-updated').textContent = s.updated;
}

let currentSort = 'default';
let currentSearch = '';
let currentTag = '';

async function loadStartups() {
  const mergedSearch = [currentSearch, currentTag].filter(Boolean).join(' ');
  const qs = new URLSearchParams({ sort: currentSort, search: mergedSearch });
  const rows = await fetchJson(`/api/startups?${qs.toString()}`);
  renderStartups(rows);
}

async function loadUpdates() {
  const rows = await fetchJson('/api/updates');
  renderUpdates(rows);
  renderEventStream(rows);
}

async function loadChanges() {
  const rows = await fetchJson('/api/changed-pages');
  renderChanges(rows);
}

async function loadMirrorPages() {
  const rows = await fetchJson('/api/mirrored-pages');
  renderMirrorPages(rows);
}

function renderMissionRuntime(data) {
  const box = document.getElementById('mission-runtime-box');
  if (!box) return;
  const status = data.status_markdown || '暂无状态';
  const runtime = data.runtime_markdown || '暂无运行报告';
  box.innerHTML = `
    <div class="meta">状态文件：${data.has_status ? '可用' : '缺失'} · 运行报告：${data.has_runtime_report ? '可用' : '缺失'}</div>
    <details open class="mission-block">
      <summary>任务状态</summary>
      <pre class="mission-pre">${status}</pre>
    </details>
    <details open class="mission-block">
      <summary>运行报告</summary>
      <pre class="mission-pre">${runtime}</pre>
    </details>
  `;
}

function renderMissionHealth(data) {
  const box = document.getElementById('mission-runtime-box');
  if (!box) return;
  const statusColor = {
    healthy: '#00d26a',
    stale: '#ff6a85',
    stopped: '#ff6a85',
    unknown: '#ffbd38',
  }[data.status] || '#98a3b8';
  const head = `
    <div class="mission-health">
      <span class="health-dot" style="background:${statusColor}"></span>
      <strong>mission: ${data.status}</strong>
      <span class="meta">heartbeat_age=${data.heartbeat_age_sec ?? '-'}s · fails=${data.recent_fail_count}/${data.recent_total_steps}</span>
    </div>
  `;
  box.insertAdjacentHTML('afterbegin', head);
}

function renderMissionCycles(rows) {
  const list = document.getElementById('mission-cycles-list');
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div class="update-card">暂无任务轨迹记录。</div>';
    return;
  }
  list.innerHTML = rows.slice().reverse().map((r) => `
    <article class="update-card">
      <div><strong>${r.timestamp}</strong> · cycle ${r.cycle}</div>
      <div class="meta">${r.step} → ${r.result}</div>
      <p>${r.note}</p>
    </article>
  `).join('');
}

function renderMissionAlerts(data) {
  const list = document.getElementById('mission-alerts-list');
  if (!list) return;
  const alerts = data?.alerts || [];
  if (!alerts.length) {
    list.innerHTML = '<div class="update-card muted">当前无告警。</div>';
    return;
  }
  list.innerHTML = alerts.map((a) => `
    <article class="update-card">
      <div><strong>[${a.severity}] ${a.code}</strong></div>
      <p>${a.message}</p>
    </article>
  `).join('');
}

function renderWatchdogEvents(rows) {
  const list = document.getElementById('watchdog-events-list');
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div class="update-card muted">暂无 watchdog 事件。</div>';
    return;
  }
  list.innerHTML = rows.slice().reverse().map((r) => `
    <article class="update-card">
      <div><strong>${r.timestamp}</strong> · ${r.event}</div>
      <p>${r.details}</p>
    </article>
  `).join('');
}

function renderMaintenanceStatus(data) {
  const box = document.getElementById('maintenance-box');
  if (!box) return;
  const sizes = data?.sizes || {};
  box.innerHTML = `
    <div class="meta">生成时间：${data?.generated_at || '-'}</div>
    <div class="meta">日志=${sizes.logs_bytes ?? '-'} bytes · 报告=${sizes.reports_bytes ?? '-'} bytes · 备份=${sizes.backups_bytes ?? '-'} bytes</div>
    <details class="mission-block">
      <summary>备份清单</summary>
      <pre class="mission-pre">${JSON.stringify(data?.backups || {}, null, 2)}</pre>
    </details>
  `;
}

function renderRetro(data) {
  const box = document.getElementById('retro-box');
  if (!box) return;
  const requested = data?.requested_actions || [];
  const executed = data?.executed_actions || [];
  const metrics = data?.metrics || {};
  box.innerHTML = `
    <div class="meta">generated_at: ${data?.generated_at || '-'}</div>
    <div class="meta">step_ok=${metrics.step_ok ?? '-'} · step_fail=${metrics.step_fail ?? '-'} · alert_count=${metrics.alert_count ?? '-'}</div>
    <pre class="mission-pre">requested:\\n${requested.map((x) => `- ${x}`).join('\\n') || '- none'}</pre>
    <pre class="mission-pre">executed:\\n${executed.map((x) => `- ${x}`).join('\\n') || '- none'}</pre>
  `;
}

function renderNextActions(data) {
  const list = document.getElementById('next-actions-list');
  if (!list) return;
  const actions = data?.actions || [];
  if (!actions.length) {
    list.innerHTML = '<div class="update-card">暂无下一步动作建议。</div>';
    return;
  }
  list.innerHTML = actions.map((a) => `
    <article class="update-card">
      <div><strong>[${a.priority}] ${a.title}</strong></div>
      <p>${a.detail}</p>
      <div class="meta">trigger: ${a.trigger}</div>
    </article>
  `).join('');
}

function renderAccelerationPlan(data) {
  const box = document.getElementById('acceleration-box');
  if (!box) return;
  const bottlenecks = data?.bottlenecks || [];
  const sequence = data?.turbo_sequence || [];
  box.innerHTML = `
    <div class="meta">generated_at: ${data?.generated_at || '-'} | efficiency_score: ${data?.efficiency_score ?? '-'}</div>
    <pre class="mission-pre">bottlenecks:\\n${bottlenecks.map((x) => `- ${x}`).join('\\n') || '- none'}</pre>
    <pre class="mission-pre">turbo_sequence:\\n${sequence.map((s) => `(${s.id}) ${s.step} :: ${s.action} | gain=${s.eta_gain}`).join('\\n') || '- none'}</pre>
  `;
}

function renderTurboLastRun(data) {
  const box = document.getElementById('turbo-box');
  if (!box) return;
  box.innerHTML = `
    <div class="meta">run_at: ${data?.run_at || '-'} | total: ${data?.elapsed_seconds ?? '-'}s | max_urls: ${data?.max_urls ?? '-'}</div>
    <pre class="mission-pre">${JSON.stringify(data?.steps || {}, null, 2)}</pre>
  `;
}

async function loadMissionRuntime() {
  const data = await fetchJson('/api/mission-runtime');
  renderMissionRuntime(data);
}

async function loadMissionCycles() {
  const rows = await fetchJson('/api/mission-cycles?limit=20');
  renderMissionCycles(rows);
}

async function loadMissionHealth() {
  const data = await fetchJson('/api/mission-health');
  renderMissionHealth(data);
}

async function loadMissionAlerts() {
  const data = await fetchJson('/api/mission-alerts');
  renderMissionAlerts(data);
}

async function loadWatchdogEvents() {
  const rows = await fetchJson('/api/watchdog-events?limit=20');
  renderWatchdogEvents(rows);
}

async function loadMaintenanceStatus() {
  const data = await fetchJson('/api/maintenance-status');
  renderMaintenanceStatus(data);
}

async function loadRetro() {
  const data = await fetchJson('/api/mission-retro');
  renderRetro(data);
}

async function loadNextActions() {
  const data = await fetchJson('/api/next-actions');
  renderNextActions(data);
}

async function loadAccelerationPlan() {
  const data = await fetchJson('/api/acceleration-plan');
  renderAccelerationPlan(data);
}

async function loadTurboLastRun() {
  const data = await fetchJson('/api/turbo-last-run');
  renderTurboLastRun(data);
}

function renderMirrorDiff(data) {
  const box = document.getElementById('mirror-diff-box');
  if (!box) return;
  if (!data.found) {
    box.innerHTML = '暂无可用历史版本数据。';
    return;
  }
  const current = data.current || {};
  const previous = data.previous || {};
  const statusText = data.changed ? '检测到变化' : '最近两版无变化';
  box.innerHTML = `
    <div class="diff-status">${statusText}</div>
    <div class="diff-grid">
      <article class="diff-card">
        <h4>当前版本</h4>
        <div class="meta">${current.fetched_at || '-'}</div>
        <p>${current.content_excerpt || '暂无内容'}</p>
      </article>
      <article class="diff-card">
        <h4>上一版本</h4>
        <div class="meta">${previous.fetched_at || '-'}</div>
        <p>${previous.content_excerpt || '暂无历史版本'}</p>
      </article>
    </div>
  `;
}

async function loadMirrorDiff(url) {
  const qs = new URLSearchParams({ url });
  const data = await fetchJson(`/api/mirror-diff?${qs.toString()}`);
  renderMirrorDiff(data);
}

function bindMirrorDiffButtons() {
  document.querySelectorAll('.diff-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const url = btn.dataset.url;
      if (!url) return;
      loadMirrorDiff(url).catch(console.error);
    });
  });
}

function drawMiniChart(canvasId, values, color) {
  const canvas = document.getElementById(canvasId);
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const ctx = canvas.getContext('2d');
  if (!ctx || !values.length) return;
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  const step = w / Math.max(values.length - 1, 1);
  const max = Math.max(...values, 1);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = i * step;
    const y = h - (v / max) * (h - 8) - 4;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawDashboardCharts() {
  drawMiniChart('burn-chart', [3, 5, 8, 6, 10, 7, 12], '#ff6a85');
  drawMiniChart('reason-chart', [6, 9, 4, 8, 5, 7], '#45d7ff');
  drawMiniChart('rebuild-chart', [4, 6, 5, 7, 8, 9, 8], '#ffbd38');
}

function renderEventStream(updateRows) {
  const box = document.getElementById('event-stream');
  if (!box) return;
  if (!updateRows.length) return;
  box.innerHTML = updateRows.slice(0, 5).map((u) => (
    `<div class="event-item">${u.checked_at} · ${u.summary}</div>`
  )).join('');
}

function renderTicker(items) {
  const track = document.getElementById('ticker-track');
  if (!track) return;
  if (!items.length) {
    track.textContent = '暂无滚动数据';
    return;
  }
  const line = [...items, ...items].map((t) => `<span class="ticker-item">${t}</span>`).join('');
  track.innerHTML = line;
}

async function loadTicker() {
  const rows = await fetchJson('/api/ticker');
  renderTicker(rows);
}

function bindControls() {
  document.querySelectorAll('.sidebar-sort-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sidebar-sort-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentSort = btn.dataset.sort;
      loadStartups().catch(console.error);
    });
  });

  const search = document.getElementById('sidebar-search-input');
  search?.addEventListener('input', (e) => {
    currentSearch = e.target.value.trim();
    loadStartups().catch(console.error);
  });

  document.querySelectorAll('.filter-tag').forEach((tag) => {
    tag.addEventListener('click', () => {
      const isActive = tag.classList.contains('active');
      document.querySelectorAll('.filter-tag').forEach((t) => t.classList.remove('active'));
      if (isActive) {
        currentTag = '';
      } else {
        tag.classList.add('active');
        currentTag = tag.dataset.tag || '';
      }
      loadStartups().catch(console.error);
    });
  });

  const btn = document.getElementById('hamburger-btn');
  const sidebar = document.getElementById('main-sidebar');
  const overlay = document.getElementById('drawer-overlay');
  if (btn && sidebar && overlay) {
    btn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('show');
    });
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
    });
  }
}

(function initCanvas() {
  const c = document.getElementById('hero-canvas');
  if (!(c instanceof HTMLCanvasElement)) return;
  const ctx = c.getContext('2d');
  if (!ctx) return;

  function resize() {
    c.width = window.innerWidth;
    c.height = Math.min(window.innerHeight * 0.58, 520);
  }
  resize();
  window.addEventListener('resize', resize);

  let t = 0;
  function loop() {
    t += 0.01;
    const w = c.width;
    const h = c.height;
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < 26; i += 1) {
      const x = (i / 26) * w + Math.sin(t + i) * 14;
      const y = h * 0.4 + Math.cos(t * 1.4 + i) * 48;
      ctx.fillStyle = i % 2 ? 'rgba(255,77,109,0.12)' : 'rgba(69,215,255,0.10)';
      ctx.beginPath();
      ctx.arc(x, y, 10 + (i % 4), 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(loop);
  }
  loop();
})();

async function init() {
  bindControls();
  await Promise.all([
    loadStats(),
    loadStartups(),
    loadUpdates(),
    loadChanges(),
    loadTicker(),
    loadMirrorPages(),
    loadMissionRuntime(),
    loadMissionCycles(),
    loadMissionHealth(),
    loadMissionAlerts(),
    loadWatchdogEvents(),
    loadMaintenanceStatus(),
    loadRetro(),
    loadNextActions(),
    loadAccelerationPlan(),
    loadTurboLastRun(),
  ]);
  drawDashboardCharts();

  // Periodic refresh for long-running mission observability.
  setInterval(() => {
    Promise.all([
      loadMissionRuntime(),
      loadMissionCycles(),
      loadMissionHealth(),
      loadMissionAlerts(),
      loadWatchdogEvents(),
      loadMaintenanceStatus(),
      loadRetro(),
      loadNextActions(),
      loadAccelerationPlan(),
      loadTurboLastRun(),
    ]).catch(console.error);
  }, 60000);
}

init().catch((err) => {
  console.error(err);
});
