/**
 * UptimeX — Frontend Application Logic (Vanilla JavaScript)
 */

(function () {
  'use strict';

  // Application State
  const state = {
    currentView: 'overview',
    theme: localStorage.getItem('uptimex_theme') || 'dark',
    monitors: [],
    summary: null,
    incidents: [],
    selectedMonitorId: null,
    analyticsHours: 24,
    analyticsData: null,
    filterStatus: 'ALL',
    searchQuery: '',
    sortBy: 'created_at-desc',
    deleteTargetId: null,
    isRefreshing: false,
    countdown: 15,
    countdownInterval: null,
    backendOnline: true
  };

  // DOM Elements Cache
  const DOM = {
    html: document.documentElement,
    sidebar: document.getElementById('sidebar'),
    mobileMenuToggle: document.getElementById('mobile-menu-toggle'),
    pageTitle: document.getElementById('page-title'),
    pageSubtitle: document.getElementById('page-subtitle'),
    themeToggle: document.getElementById('theme-toggle'),
    refreshIndicator: document.getElementById('refresh-indicator'),
    countdownText: document.getElementById('countdown-text'),
    btnRefreshData: document.getElementById('btn-refresh-data'),
    btnOpenCreateModal: document.getElementById('btn-open-create-modal'),
    connectionDot: document.getElementById('connection-dot'),
    connectionText: document.getElementById('connection-text'),
    navMonitorsCount: document.getElementById('nav-monitors-count'),
    navIncidentsCount: document.getElementById('nav-incidents-count'),

    // View Panels
    viewPanels: {
      overview: document.getElementById('view-overview'),
      monitors: document.getElementById('view-monitors'),
      incidents: document.getElementById('view-incidents'),
      history: document.getElementById('view-history'),
      settings: document.getElementById('view-settings')
    },
    navItems: document.querySelectorAll('.nav-item'),

    // Overview Elements
    activeIncidentsBanner: document.getElementById('active-incidents-banner'),
    activeIncidentsDetail: document.getElementById('active-incidents-detail'),
    btnBannerViewIncidents: document.getElementById('btn-banner-view-incidents'),
    summaryTotal: document.getElementById('summary-total'),
    summaryStatusSplit: document.getElementById('summary-status-split'),
    summaryUp: document.getElementById('summary-up'),
    summaryUpPct: document.getElementById('summary-up-pct'),
    summaryDown: document.getElementById('summary-down'),
    summaryDownSub: document.getElementById('summary-down-sub'),
    summaryAvgLatency: document.getElementById('summary-avg-latency'),
    summaryUptime24h: document.getElementById('summary-uptime-24h'),
    overviewMonitorsTbody: document.getElementById('overview-monitors-tbody'),
    overviewRecentChecks: document.getElementById('overview-recent-checks'),
    overviewIncidentFeed: document.getElementById('overview-incident-feed'),
    btnQuickManage: document.getElementById('btn-quick-manage'),
    btnLinkAllIncidents: document.getElementById('btn-link-all-incidents'),

    // Monitors Elements
    filterSearch: document.getElementById('filter-search'),
    filterStatusPills: document.getElementById('filter-status-pills'),
    sortSelect: document.getElementById('sort-select'),
    monitorsContainer: document.getElementById('monitors-cards-container'),
    monitorsEmptyState: document.getElementById('monitors-empty-state'),
    btnEmptyAddMonitor: document.getElementById('btn-empty-add-monitor'),
    countAll: document.getElementById('count-all'),
    countUp: document.getElementById('count-up'),
    countDown: document.getElementById('count-down'),
    countPaused: document.getElementById('count-paused'),
    countPending: document.getElementById('count-pending'),

    // Incidents Elements
    activeIncidentsList: document.getElementById('active-incidents-list'),
    resolvedIncidentsList: document.getElementById('resolved-incidents-list'),
    activeIncidentsBadge: document.getElementById('active-incidents-badge'),
    resolvedIncidentsBadge: document.getElementById('resolved-incidents-badge'),

    // History Elements
    analyticsMonitorSelect: document.getElementById('analytics-monitor-select'),
    timeWindowPills: document.getElementById('time-window-pills'),
    btnExportCsv: document.getElementById('btn-export-csv'),
    analyticsUptime: document.getElementById('analytics-uptime'),
    analyticsChecksCount: document.getElementById('analytics-checks-count'),
    analyticsAvgLatency: document.getElementById('analytics-avg-latency'),
    analyticsMinMax: document.getElementById('analytics-min-max'),
    analyticsSuccessChecks: document.getElementById('analytics-success-checks'),
    analyticsFailedChecks: document.getElementById('analytics-failed-checks'),
    svgChart: document.getElementById('latency-svg-chart'),
    chartTooltip: document.getElementById('chart-tooltip'),
    historyTableTbody: document.getElementById('history-table-tbody'),
    historyPaginationInfo: document.getElementById('history-pagination-info'),

    // Settings Elements
    settingsForm: document.getElementById('settings-form'),
    settingDefaultInterval: document.getElementById('setting-default-interval'),
    settingDefaultTimeout: document.getElementById('setting-default-timeout'),
    settingRetentionDays: document.getElementById('setting-retention-days'),
    settingTheme: document.getElementById('setting-theme'),
    sysStatusApp: document.getElementById('sys-status-app'),
    sysStatusScheduler: document.getElementById('sys-status-scheduler'),
    sysTotalMonitors: document.getElementById('sys-total-monitors'),
    sysActiveIncidents: document.getElementById('sys-active-incidents'),
    sysServerTime: document.getElementById('sys-server-time'),

    // Modals
    modalMonitor: document.getElementById('modal-monitor'),
    modalTitle: document.getElementById('modal-title'),
    formMonitor: document.getElementById('form-monitor'),
    monitorFormId: document.getElementById('monitor-form-id'),
    monitorName: document.getElementById('monitor-name'),
    monitorUrl: document.getElementById('monitor-url'),
    monitorMethod: document.getElementById('monitor-method'),
    monitorInterval: document.getElementById('monitor-interval'),
    monitorTimeout: document.getElementById('monitor-timeout'),
    monitorExpectedStatus: document.getElementById('monitor-expected-status'),
    modalErrorBox: document.getElementById('modal-error-box'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalCancelBtn: document.getElementById('modal-cancel-btn'),

    modalDelete: document.getElementById('modal-delete'),
    deleteMonitorName: document.getElementById('delete-monitor-name'),
    deleteCloseBtn: document.getElementById('delete-close-btn'),
    deleteCancelBtn: document.getElementById('delete-cancel-btn'),
    deleteConfirmBtn: document.getElementById('delete-confirm-btn'),

    toastContainer: document.getElementById('toast-container')
  };

  /* ==========================================================================
     View Titles & Navigation
     ========================================================================== */

  const VIEW_METADATA = {
    overview: {
      title: 'System Overview',
      subtitle: 'Real-time infrastructure health and performance metrics'
    },
    monitors: {
      title: 'Website Monitors',
      subtitle: 'Manage endpoints, check frequencies, and HTTP expectations'
    },
    incidents: {
      title: 'Incidents & Outages',
      subtitle: 'Track active disruptions and review historical incident duration'
    },
    history: {
      title: 'Performance & History',
      subtitle: 'Response latency trend charts, uptime statistics, and CSV logs'
    },
    settings: {
      title: 'System Settings',
      subtitle: 'Configuration parameters, security audits, and scheduler status'
    }
  };

  function switchView(viewName) {
    if (!VIEW_METADATA[viewName]) return;
    state.currentView = viewName;

    // Update active nav button
    DOM.navItems.forEach(item => {
      item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Update visible panel
    Object.keys(DOM.viewPanels).forEach(key => {
      const panel = DOM.viewPanels[key];
      if (panel) panel.classList.toggle('active', key === viewName);
    });

    // Update topbar titles
    DOM.pageTitle.textContent = VIEW_METADATA[viewName].title;
    DOM.pageSubtitle.textContent = VIEW_METADATA[viewName].subtitle;

    // View specific initializations
    if (viewName === 'history') {
      populateMonitorDropdown();
      if (state.selectedMonitorId) {
        loadAnalytics(state.selectedMonitorId, state.analyticsHours);
      }
    } else if (viewName === 'settings') {
      loadSettings();
    }

    // Close mobile menu if open
    DOM.sidebar.classList.remove('open');
  }

  /* ==========================================================================
     Theme Management
     ========================================================================== */

  function applyTheme(theme) {
    state.theme = theme;
    DOM.html.setAttribute('data-theme', theme);
    localStorage.setItem('uptimex_theme', theme);
  }

  function toggleTheme() {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
  }

  /* ==========================================================================
     Toasts & Notifications
     ========================================================================== */

  function showToast(message, type = 'info', duration = 3500) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    } else if (type === 'error') {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>';
    } else {
      iconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(8px)';
      toast.style.transition = 'all 200ms ease';
      setTimeout(() => toast.remove(), 200);
    }, duration);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatRelativeTime(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);

    if (diffSec < 5) return 'Just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  function formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return '--';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins < 60) return `${mins}m ${secs}s`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ${mins % 60}m`;
  }

  /* ==========================================================================
     API Calls
     ========================================================================== */

  async function apiFetch(endpoint, options = {}) {
    try {
      const response = await fetch(endpoint, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });

      if (!response.ok) {
        let errDetail = `HTTP ${response.status}`;
        try {
          const errData = await response.json();
          if (errData && errData.detail) errDetail = errData.detail;
        } catch (_) {}
        throw new Error(errDetail);
      }

      setConnectionStatus(true);
      if (response.status === 204) return null;
      return await response.json();
    } catch (err) {
      if (err.message && err.message.includes('Failed to fetch')) {
        setConnectionStatus(false);
      }
      throw err;
    }
  }

  function setConnectionStatus(online) {
    state.backendOnline = online;
    if (online) {
      DOM.connectionDot.className = 'status-dot connected';
      DOM.connectionText.textContent = 'Backend Online';
    } else {
      DOM.connectionDot.className = 'status-dot disconnected';
      DOM.connectionText.textContent = 'Reconnecting...';
    }
  }

  /* ==========================================================================
     Data Loading & Rendering
     ========================================================================== */

  async function refreshAllData(silent = false) {
    if (state.isRefreshing) return;
    state.isRefreshing = true;

    try {
      const [summary, monitors, incidents] = await Promise.all([
        apiFetch('/api/summary'),
        apiFetch('/api/monitors'),
        apiFetch('/api/incidents')
      ]);

      state.summary = summary;
      state.monitors = monitors;
      state.incidents = incidents;

      renderSummary();
      renderMonitors();
      renderIncidents();
      renderOverviewTables();
      populateMonitorDropdown();

      // If viewing history and a monitor is selected, refresh its chart
      if (state.currentView === 'history' && state.selectedMonitorId) {
        loadAnalytics(state.selectedMonitorId, state.analyticsHours, true);
      }

      if (!silent) {
        showToast('Observability data refreshed.', 'info', 2000);
      }
    } catch (err) {
      console.error('Refresh error:', err);
      if (!silent) {
        showToast(err.message || 'Failed to refresh data.', 'error');
      }
    } finally {
      state.isRefreshing = false;
      resetCountdown();
    }
  }

  function renderSummary() {
    if (!state.summary) return;
    const s = state.summary;

    DOM.summaryTotal.textContent = s.total_monitors;
    DOM.navMonitorsCount.textContent = s.total_monitors;
    DOM.summaryStatusSplit.textContent = `${s.up_count} operational · ${s.paused_count} paused · ${s.pending_count} pending`;

    DOM.summaryUp.textContent = s.up_count;
    const operationalPct = s.total_monitors > 0
      ? Math.round((s.up_count / s.total_monitors) * 100)
      : 100;
    DOM.summaryUpPct.textContent = `${operationalPct}% operational`;

    DOM.summaryDown.textContent = s.down_count;
    DOM.summaryDownSub.textContent = s.down_count > 0 ? `${s.down_count} failing health checks` : 'No failing endpoints';

    DOM.summaryAvgLatency.innerHTML = s.overall_avg_response_time !== null
      ? `${s.overall_avg_response_time} <span class="unit">ms</span>`
      : `-- <span class="unit">ms</span>`;

    DOM.summaryUptime24h.textContent = s.overall_uptime_24h !== null
      ? `24h Uptime: ${s.overall_uptime_24h}%`
      : `24h Uptime: Insufficient data`;

    // Active incidents badge in nav
    if (s.active_incidents_count > 0) {
      DOM.navIncidentsCount.textContent = s.active_incidents_count;
      DOM.navIncidentsCount.style.display = 'inline-flex';
      DOM.activeIncidentsBanner.style.display = 'flex';
      DOM.activeIncidentsDetail.textContent = `${s.active_incidents_count} endpoint(s) currently down. Immediate attention recommended.`;
    } else {
      DOM.navIncidentsCount.style.display = 'none';
      DOM.activeIncidentsBanner.style.display = 'none';
    }

    // Filter counts
    DOM.countAll.textContent = state.monitors.length;
    DOM.countUp.textContent = state.monitors.filter(m => m.current_status === 'UP' && m.is_enabled).length;
    DOM.countDown.textContent = state.monitors.filter(m => m.current_status === 'DOWN' && m.is_enabled).length;
    DOM.countPaused.textContent = state.monitors.filter(m => !m.is_enabled).length;
    DOM.countPending.textContent = state.monitors.filter(m => m.current_status === 'PENDING' && m.is_enabled).length;
  }

  function renderMonitors() {
    const container = DOM.monitorsContainer;
    container.innerHTML = '';

    let filtered = [...state.monitors];

    // Filter by search query
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(m => m.name.toLowerCase().includes(q) || m.url.toLowerCase().includes(q));
    }

    // Filter by status tab
    if (state.filterStatus === 'UP') {
      filtered = filtered.filter(m => m.current_status === 'UP' && m.is_enabled);
    } else if (state.filterStatus === 'DOWN') {
      filtered = filtered.filter(m => m.current_status === 'DOWN' && m.is_enabled);
    } else if (state.filterStatus === 'PAUSED') {
      filtered = filtered.filter(m => !m.is_enabled);
    } else if (state.filterStatus === 'PENDING') {
      filtered = filtered.filter(m => m.current_status === 'PENDING' && m.is_enabled);
    }

    // Sort
    const [field, dir] = state.sortBy.split('-');
    filtered.sort((a, b) => {
      let valA = a[field];
      let valB = b[field];
      if (valA === null || valA === undefined) valA = '';
      if (valB === null || valB === undefined) valB = '';
      if (typeof valA === 'string') valA = valA.toLowerCase();
      if (typeof valB === 'string') valB = valB.toLowerCase();
      if (valA < valB) return dir === 'asc' ? -1 : 1;
      if (valA > valB) return dir === 'asc' ? 1 : -1;
      return 0;
    });

    if (filtered.length === 0) {
      DOM.monitorsEmptyState.style.display = 'flex';
      container.style.display = 'none';
      return;
    }

    DOM.monitorsEmptyState.style.display = 'none';
    container.style.display = 'grid';

    filtered.forEach(m => {
      const card = createMonitorCardElement(m);
      container.appendChild(card);
    });
  }

  function createMonitorCardElement(m) {
    const card = document.createElement('div');
    card.className = 'monitor-card';

    const statusClass = !m.is_enabled ? 'paused' : m.current_status.toLowerCase();
    const statusLabel = !m.is_enabled ? 'PAUSED' : m.current_status;

    let latencyDisplay = '--';
    let latencyClass = '';
    if (m.last_response_time_ms !== null && m.last_response_time_ms !== undefined) {
      latencyDisplay = `${m.last_response_time_ms} ms`;
      if (m.last_response_time_ms > 1000) latencyClass = 'failing';
      else if (m.last_response_time_ms > 400) latencyClass = 'slow';
    }

    card.innerHTML = `
      <div>
        <div class="monitor-card-header">
          <div class="monitor-card-title-group">
            <h3 class="monitor-card-name" title="${escapeHtml(m.name)}">${escapeHtml(m.name)}</h3>
            <a href="${escapeHtml(m.url)}" target="_blank" rel="noopener noreferrer" class="monitor-card-url" title="${escapeHtml(m.url)}">${escapeHtml(m.url)}</a>
          </div>
          <span class="status-pill ${statusClass}">
            <span class="dot"></span>
            ${statusLabel}
          </span>
        </div>

        <div class="monitor-stats-row">
          <div class="monitor-stat-item">
            <span class="monitor-stat-label">Latency</span>
            <span class="monitor-stat-val">${latencyDisplay}</span>
          </div>
          <div class="monitor-stat-item">
            <span class="monitor-stat-label">HTTP Code</span>
            <span class="monitor-stat-val">${m.last_status_code || '--'}</span>
          </div>
          <div class="monitor-stat-item">
            <span class="monitor-stat-label">Interval</span>
            <span class="monitor-stat-val">${m.interval_seconds}s</span>
          </div>
        </div>
      </div>

      <div class="monitor-card-footer">
        <div class="monitor-actions-left">
          <span>Checked: ${formatRelativeTime(m.last_check_at)}</span>
        </div>
        <div class="monitor-actions-right">
          <button class="btn btn-secondary btn-sm btn-check-now" data-id="${m.id}" title="Run manual check now">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
            </svg>
            <span>Check</span>
          </button>
          <button class="btn btn-secondary btn-sm btn-analytics-jump" data-id="${m.id}" title="View analytics & chart">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3v18h18"></path>
              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"></path>
            </svg>
          </button>
          <button class="btn btn-secondary btn-sm btn-toggle" data-id="${m.id}" title="${m.is_enabled ? 'Pause' : 'Resume'}">
            ${m.is_enabled
              ? '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>'
              : '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>'}
          </button>
          <button class="btn btn-secondary btn-sm btn-edit" data-id="${m.id}" title="Edit settings">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </button>
          <button class="btn btn-secondary btn-sm btn-delete text-rose" data-id="${m.id}" data-name="${escapeHtml(m.name)}" title="Delete monitor">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    `;

    return card;
  }

  function renderOverviewTables() {
    // 1. Monitors overview table
    const tbody = DOM.overviewMonitorsTbody;
    tbody.innerHTML = '';

    if (state.monitors.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 28px; color: var(--text-muted);">No monitors configured yet. Click "Add Monitor" to get started.</td></tr>`;
    } else {
      state.monitors.slice(0, 8).forEach(m => {
        const tr = document.createElement('tr');
        const statusClass = !m.is_enabled ? 'paused' : m.current_status.toLowerCase();
        const statusLabel = !m.is_enabled ? 'PAUSED' : m.current_status;

        let codeBadgeClass = 'success';
        if (!m.last_status_code || m.last_status_code >= 400) codeBadgeClass = 'error';
        else if (m.last_status_code >= 300) codeBadgeClass = 'redirect';

        tr.innerHTML = `
          <td>
            <div class="endpoint-cell">
              <span class="endpoint-name">${escapeHtml(m.name)}</span>
              <a href="${escapeHtml(m.url)}" target="_blank" rel="noopener noreferrer" class="endpoint-url">${escapeHtml(m.url)}</a>
            </div>
          </td>
          <td>
            <span class="status-pill ${statusClass}">
              <span class="dot"></span>
              ${statusLabel}
            </span>
          </td>
          <td>
            <div class="latency-display">
              <span>${m.last_response_time_ms !== null ? m.last_response_time_ms + ' ms' : '--'}</span>
            </div>
          </td>
          <td>
            <span class="http-code-badge ${codeBadgeClass}">${m.last_status_code || '--'}</span>
          </td>
          <td>
            <span class="subtext">${formatRelativeTime(m.last_check_at)}</span>
          </td>
          <td class="text-right">
            <button class="btn btn-secondary btn-sm btn-check-now" data-id="${m.id}" title="Run check now">
              Check
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    // 2. Fetch and render recent checks stream
    loadRecentChecks();

    // 3. Render incident feed snippet
    const feed = DOM.overviewIncidentFeed;
    feed.innerHTML = '';
    if (state.incidents.length === 0) {
      feed.innerHTML = `<div style="text-align:center; padding: 20px; color: var(--text-muted); font-size: 13px;">No incidents recorded. All systems operational!</div>`;
    } else {
      state.incidents.slice(0, 4).forEach(inc => {
        const item = document.createElement('div');
        item.className = 'incident-feed-item';
        item.style.padding = '10px 0';
        item.style.borderBottom = '1px solid var(--border-color)';
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        item.style.alignItems = 'center';

        const isAct = inc.status === 'ACTIVE';
        item.innerHTML = `
          <div>
            <strong style="color: ${isAct ? 'var(--rose)' : 'var(--emerald)'}; font-size: 13px;">
              ${isAct ? 'Active Outage' : 'Resolved Incident'}
            </strong>
            <p style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
              ${escapeHtml(inc.monitor_name || 'Monitor #' + inc.monitor_id)}: ${escapeHtml(inc.cause)}
            </p>
          </div>
          <span style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">
            ${isAct ? 'Ongoing' : formatDuration(inc.duration_seconds)}
          </span>
        `;
        feed.appendChild(item);
      });
    }
  }

  async function loadRecentChecks() {
    try {
      const recent = await apiFetch('/api/checks/recent?limit=8');
      const list = DOM.overviewRecentChecks;
      list.innerHTML = '';

      if (recent.length === 0) {
        list.innerHTML = `<div style="text-align:center; padding: 20px; color: var(--text-muted); font-size: 13px;">No check records yet.</div>`;
        return;
      }

      recent.forEach(c => {
        const div = document.createElement('div');
        div.style.display = 'flex';
        div.style.alignItems = 'center';
        div.style.justifyContent = 'space-between';
        div.style.padding = '8px 0';
        div.style.borderBottom = '1px solid var(--border-color)';
        div.style.fontSize = '12.5px';

        const isSucc = c.is_success;
        const color = isSucc ? 'var(--emerald)' : 'var(--rose)';
        const mon = state.monitors.find(m => m.id === c.monitor_id);
        const name = mon ? mon.name : `Monitor #${c.monitor_id}`;

        div.innerHTML = `
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="width:6px; height:6px; border-radius:50%; background-color:${color};"></span>
            <strong>${escapeHtml(name)}</strong>
          </div>
          <div style="display:flex; align-items:center; gap:12px; font-family: var(--font-mono); font-size: 12px;">
            <span>${c.status_code || 'ERR'}</span>
            <span style="color:${color}; font-weight:600;">${c.response_time_ms}ms</span>
            <span style="color:var(--text-muted);">${formatRelativeTime(c.checked_at)}</span>
          </div>
        `;
        list.appendChild(div);
      });
    } catch (_) {}
  }

  function renderIncidents() {
    const activeList = DOM.activeIncidentsList;
    const resolvedList = DOM.resolvedIncidentsList;
    activeList.innerHTML = '';
    resolvedList.innerHTML = '';

    const activeIncidents = state.incidents.filter(i => i.status === 'ACTIVE');
    const resolvedIncidents = state.incidents.filter(i => i.status === 'RESOLVED');

    DOM.activeIncidentsBadge.textContent = `${activeIncidents.length} Active`;
    DOM.resolvedIncidentsBadge.textContent = `${resolvedIncidents.length} Resolved`;

    // Active
    if (activeIncidents.length === 0) {
      activeList.innerHTML = `
        <div style="text-align:center; padding: 36px 20px; color: var(--text-muted);">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:8px; color:var(--emerald);">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <p style="font-weight:600; color:var(--text-primary);">Zero Active Outages</p>
          <p style="font-size:12.5px;">All endpoints are returning successful responses according to their configured health rules.</p>
        </div>
      `;
    } else {
      activeIncidents.forEach(inc => {
        const item = document.createElement('div');
        item.className = 'incident-item active-incident';
        item.innerHTML = `
          <div class="incident-info">
            <div class="incident-icon-pill rose">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <div class="incident-details">
              <h4>${escapeHtml(inc.monitor_name || 'Monitor #' + inc.monitor_id)}</h4>
              <p>${escapeHtml(inc.cause)}</p>
              <div class="incident-meta">
                <span>Started: ${new Date(inc.started_at).toLocaleString()}</span>
                <span>Outage Ongoing</span>
              </div>
            </div>
          </div>
          <button class="btn btn-secondary btn-sm btn-check-now" data-id="${inc.monitor_id}">
            Re-check Now
          </button>
        `;
        activeList.appendChild(item);
      });
    }

    // Resolved
    if (resolvedIncidents.length === 0) {
      resolvedList.innerHTML = `
        <div style="text-align:center; padding: 28px 20px; color: var(--text-muted); font-size: 13px;">
          No resolved incident history recorded.
        </div>
      `;
    } else {
      resolvedIncidents.forEach(inc => {
        const item = document.createElement('div');
        item.className = 'incident-item resolved-incident';
        item.innerHTML = `
          <div class="incident-info">
            <div class="incident-icon-pill emerald">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
            <div class="incident-details">
              <h4>${escapeHtml(inc.monitor_name || 'Monitor #' + inc.monitor_id)}</h4>
              <p>Root cause: ${escapeHtml(inc.cause)}</p>
              <div class="incident-meta">
                <span>Started: ${new Date(inc.started_at).toLocaleString()}</span>
                <span>Resolved: ${new Date(inc.resolved_at).toLocaleString()}</span>
                <span>Duration: <strong>${formatDuration(inc.duration_seconds)}</strong></span>
              </div>
            </div>
          </div>
          <span class="badge badge-emerald">Resolved</span>
        `;
        resolvedList.appendChild(item);
      });
    }
  }

  /* ==========================================================================
     Analytics & Native SVG Chart
     ========================================================================== */

  function populateMonitorDropdown() {
    const select = DOM.analyticsMonitorSelect;
    const currentVal = select.value;
    select.innerHTML = '<option value="">Select a monitor to view performance...</option>';

    state.monitors.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = `${m.name} (${m.url})`;
      select.appendChild(opt);
    });

    if (state.selectedMonitorId) {
      select.value = state.selectedMonitorId;
    } else if (state.monitors.length > 0 && !currentVal) {
      state.selectedMonitorId = state.monitors[0].id;
      select.value = state.selectedMonitorId;
    }
  }

  async function loadAnalytics(monitorId, hours = 24, silent = false) {
    if (!monitorId) return;
    state.selectedMonitorId = monitorId;
    state.analyticsHours = hours;

    try {
      const [analytics, history] = await Promise.all([
        apiFetch(`/api/monitors/${monitorId}/analytics?hours=${hours}`),
        apiFetch(`/api/monitors/${monitorId}/history?hours=${hours}&limit=30`)
      ]);

      state.analyticsData = analytics;
      renderAnalyticsStats(analytics);
      renderSvgChart(analytics.timeseries);
      renderHistoryTable(history);
    } catch (err) {
      console.error('Analytics load error:', err);
      if (!silent) showToast(err.message || 'Failed to load analytics.', 'error');
    }
  }

  function renderAnalyticsStats(data) {
    DOM.analyticsUptime.textContent = data.uptime_display;
    DOM.analyticsChecksCount.textContent = `${data.total_checks} checks in selected window`;

    DOM.analyticsAvgLatency.innerHTML = data.avg_response_time_ms !== null
      ? `${data.avg_response_time_ms} <span class="unit">ms</span>`
      : `-- <span class="unit">ms</span>`;

    DOM.analyticsMinMax.textContent = (data.min_response_time_ms !== null && data.max_response_time_ms !== null)
      ? `Min: ${data.min_response_time_ms}ms · Max: ${data.max_response_time_ms}ms`
      : `Min: -- · Max: --`;

    DOM.analyticsSuccessChecks.textContent = data.success_checks;
    DOM.analyticsFailedChecks.textContent = data.failed_checks;
  }

  function renderHistoryTable(records) {
    const tbody = DOM.historyTableTbody;
    tbody.innerHTML = '';

    if (!records || records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">No check records logged in this timeframe.</td></tr>`;
      DOM.historyPaginationInfo.textContent = 'Showing 0 checks';
      return;
    }

    DOM.historyPaginationInfo.textContent = `Showing latest ${records.length} check results`;

    records.forEach(r => {
      const tr = document.createElement('tr');
      const isSucc = r.is_success;
      const statusClass = isSucc ? 'up' : 'down';
      const statusLabel = isSucc ? 'SUCCESS' : 'FAILED';

      let codeBadgeClass = 'success';
      if (!r.status_code || r.status_code >= 400) codeBadgeClass = 'error';
      else if (r.status_code >= 300) codeBadgeClass = 'redirect';

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-size: 12.5px;">${new Date(r.checked_at).toISOString().replace('T', ' ').substring(0, 19)}</td>
        <td><span class="status-pill ${statusClass}"><span class="dot"></span>${statusLabel}</span></td>
        <td><span class="http-code-badge ${codeBadgeClass}">${r.status_code || '--'}</span></td>
        <td style="font-family: var(--font-mono); font-weight: 600;">${r.response_time_ms} ms</td>
        <td><span class="badge ${isSucc ? '' : 'badge-rose'}">${escapeHtml(r.error_category || 'OK')}</span></td>
        <td style="font-size: 12px; color: var(--text-secondary); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${escapeHtml(r.error_message || '--')}
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderSvgChart(points) {
    const svg = DOM.svgChart;
    svg.innerHTML = '';

    if (!points || points.length === 0) {
      svg.innerHTML = `
        <text x="450" y="130" text-anchor="middle" fill="#64748b" font-size="14" font-family="Plus Jakarta Sans, sans-serif">
          Insufficient data recorded in this time window to render performance chart.
        </text>
      `;
      return;
    }

    const width = 900;
    const height = 260;
    const padTop = 30;
    const padBottom = 40;
    const padLeft = 60;
    const padRight = 30;

    const chartWidth = width - padLeft - padRight;
    const chartHeight = height - padTop - padBottom;

    // Latency bounds
    const latencies = points.map(p => p.response_time_ms);
    let maxLat = Math.max(...latencies, 100);
    let minLat = 0;
    maxLat = Math.ceil(maxLat * 1.15); // Add headroom

    // Gradient definition
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
      <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.32"></stop>
        <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0"></stop>
      </linearGradient>
    `;
    svg.appendChild(defs);

    // Horizontal grid lines
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
      const val = Math.round(minLat + (maxLat - minLat) * (i / gridLines));
      const y = padTop + chartHeight - (i / gridLines) * chartHeight;

      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', padLeft);
      line.setAttribute('y1', y);
      line.setAttribute('x2', width - padRight);
      line.setAttribute('y2', y);
      line.setAttribute('stroke', 'var(--border-color)');
      line.setAttribute('stroke-dasharray', '4 4');
      line.setAttribute('stroke-width', '1');
      svg.appendChild(line);

      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', padLeft - 10);
      label.setAttribute('y', y + 4);
      label.setAttribute('text-anchor', 'end');
      label.setAttribute('fill', 'var(--text-muted)');
      label.setAttribute('font-size', '11');
      label.setAttribute('font-family', 'JetBrains Mono, monospace');
      label.textContent = `${val}ms`;
      svg.appendChild(label);
    }

    // Map data points to SVG coordinates
    const coords = points.map((p, idx) => {
      const x = points.length === 1
        ? padLeft + chartWidth / 2
        : padLeft + (idx / (points.length - 1)) * chartWidth;
      const y = padTop + chartHeight - ((p.response_time_ms - minLat) / (maxLat - minLat)) * chartHeight;
      return { x, y, point: p };
    });

    // Generate path strings
    const pathD = coords.reduce((acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`, '');
    const firstX = coords[0].x.toFixed(1);
    const lastX = coords[coords.length - 1].x.toFixed(1);
    const bottomY = (padTop + chartHeight).toFixed(1);
    const areaD = `${pathD} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;

    // Area fill
    const areaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    areaPath.setAttribute('d', areaD);
    areaPath.setAttribute('fill', 'url(#areaGradient)');
    svg.appendChild(areaPath);

    // Stroke line
    const linePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    linePath.setAttribute('d', pathD);
    linePath.setAttribute('fill', 'none');
    linePath.setAttribute('stroke', '#3b82f6');
    linePath.setAttribute('stroke-width', '2.5');
    linePath.setAttribute('stroke-linejoin', 'round');
    linePath.setAttribute('stroke-linecap', 'round');
    svg.appendChild(linePath);

    // Interactive circular markers with tooltips
    coords.forEach(c => {
      const isSuccess = c.point.is_success;
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', c.x);
      circle.setAttribute('cy', c.y);
      circle.setAttribute('r', points.length > 50 ? '3' : '4');
      circle.setAttribute('fill', isSuccess ? 'var(--emerald)' : 'var(--rose)');
      circle.setAttribute('stroke', 'var(--bg-card)');
      circle.setAttribute('stroke-width', '2');
      circle.style.cursor = 'pointer';

      // Tooltip interaction
      circle.addEventListener('mouseenter', (e) => {
        circle.setAttribute('r', '7');
        const tt = DOM.chartTooltip;
        const pt = c.point;
        const timeStr = new Date(pt.timestamp).toLocaleTimeString();
        tt.innerHTML = `
          <strong>${pt.response_time_ms} ms</strong> · HTTP ${pt.status_code || 'ERR'}
          <div style="color:var(--text-muted); font-size:10.5px; margin-top:2px;">${timeStr} (${isSuccess ? 'Operational' : 'Failed'})</div>
        `;
        tt.style.display = 'block';

        const rect = svg.getBoundingClientRect();
        const clientX = (c.x / width) * rect.width;
        const clientY = (c.y / height) * rect.height;
        tt.style.left = `${clientX + 10}px`;
        tt.style.top = `${clientY - 30}px`;
      });

      circle.addEventListener('mouseleave', () => {
        circle.setAttribute('r', points.length > 50 ? '3' : '4');
        DOM.chartTooltip.style.display = 'none';
      });

      svg.appendChild(circle);
    });

    // Timestamp X-axis markers
    if (coords.length > 0) {
      const startLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      startLabel.setAttribute('x', padLeft);
      startLabel.setAttribute('y', height - 10);
      startLabel.setAttribute('fill', 'var(--text-muted)');
      startLabel.setAttribute('font-size', '11');
      startLabel.setAttribute('font-family', 'JetBrains Mono, monospace');
      startLabel.textContent = new Date(points[0].timestamp).toLocaleTimeString();
      svg.appendChild(startLabel);

      const endLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      endLabel.setAttribute('x', width - padRight);
      endLabel.setAttribute('y', height - 10);
      endLabel.setAttribute('text-anchor', 'end');
      endLabel.setAttribute('fill', 'var(--text-muted)');
      endLabel.setAttribute('font-size', '11');
      endLabel.setAttribute('font-family', 'JetBrains Mono, monospace');
      endLabel.textContent = new Date(points[points.length - 1].timestamp).toLocaleTimeString();
      svg.appendChild(endLabel);
    }
  }

  /* ==========================================================================
     Settings Management
     ========================================================================== */

  async function loadSettings() {
    try {
      const cfg = await apiFetch('/api/settings');
      DOM.settingDefaultInterval.value = cfg.default_interval_seconds;
      DOM.settingDefaultTimeout.value = cfg.default_timeout_seconds;
      DOM.settingRetentionDays.value = cfg.data_retention_days;
      DOM.settingTheme.value = cfg.theme || state.theme;

      DOM.sysStatusApp.textContent = 'Operational';
      DOM.sysStatusScheduler.textContent = cfg.scheduler_running ? 'Active (APScheduler)' : 'Stopped';
      DOM.sysStatusScheduler.className = cfg.scheduler_running ? 'badge badge-emerald' : 'badge badge-rose';
      DOM.sysTotalMonitors.textContent = cfg.total_monitors_count;
      DOM.sysActiveIncidents.textContent = cfg.active_incidents_count;
      DOM.sysServerTime.textContent = new Date(cfg.server_time_utc).toUTCString();
    } catch (err) {
      console.error('Settings load error:', err);
    }
  }

  async function handleSaveSettings(e) {
    e.preventDefault();
    const payload = {
      default_interval_seconds: parseInt(DOM.settingDefaultInterval.value, 10),
      default_timeout_seconds: parseInt(DOM.settingDefaultTimeout.value, 10),
      data_retention_days: parseInt(DOM.settingRetentionDays.value, 10),
      theme: DOM.settingTheme.value
    };

    try {
      await apiFetch('/api/settings', {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      applyTheme(payload.theme);
      showToast('Settings saved successfully.', 'success');
      loadSettings();
    } catch (err) {
      showToast(err.message || 'Failed to save settings.', 'error');
    }
  }

  /* ==========================================================================
     Monitor Modal (Add / Edit) & Deletion
     ========================================================================== */

  function openCreateModal() {
    DOM.modalTitle.textContent = 'Add Website Monitor';
    DOM.monitorFormId.value = '';
    DOM.formMonitor.reset();
    DOM.monitorExpectedStatus.value = '200-299';
    DOM.monitorInterval.value = '60';
    DOM.monitorTimeout.value = '10';
    DOM.modalErrorBox.style.display = 'none';
    DOM.modalMonitor.style.display = 'flex';
    DOM.monitorName.focus();
  }

  function openEditModal(monitorId) {
    const mon = state.monitors.find(m => m.id === monitorId);
    if (!mon) return;

    DOM.modalTitle.textContent = 'Edit Monitor Settings';
    DOM.monitorFormId.value = mon.id;
    DOM.monitorName.value = mon.name;
    DOM.monitorUrl.value = mon.url;
    DOM.monitorMethod.value = mon.method;
    DOM.monitorInterval.value = mon.interval_seconds;
    DOM.monitorTimeout.value = mon.timeout_seconds;
    DOM.monitorExpectedStatus.value = mon.expected_status_codes;
    DOM.modalErrorBox.style.display = 'none';
    DOM.modalMonitor.style.display = 'flex';
    DOM.monitorName.focus();
  }

  function closeMonitorModal() {
    DOM.modalMonitor.style.display = 'none';
  }

  async function handleMonitorFormSubmit(e) {
    e.preventDefault();
    DOM.modalErrorBox.style.display = 'none';

    const id = DOM.monitorFormId.value;
    const payload = {
      name: DOM.monitorName.value.trim(),
      url: DOM.monitorUrl.value.trim(),
      method: DOM.monitorMethod.value,
      interval_seconds: parseInt(DOM.monitorInterval.value, 10),
      timeout_seconds: parseInt(DOM.monitorTimeout.value, 10),
      expected_status_codes: DOM.monitorExpectedStatus.value.trim()
    };

    try {
      if (id) {
        // Edit existing
        await apiFetch(`/api/monitors/${id}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        showToast(`Monitor "${payload.name}" updated.`, 'success');
      } else {
        // Create new
        await apiFetch('/api/monitors', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast(`Monitor "${payload.name}" created and check scheduled!`, 'success');
      }

      closeMonitorModal();
      refreshAllData(true);
    } catch (err) {
      DOM.modalErrorBox.textContent = err.message || 'Validation error.';
      DOM.modalErrorBox.style.display = 'block';
    }
  }

  function openDeleteModal(monitorId, monitorName) {
    state.deleteTargetId = monitorId;
    DOM.deleteMonitorName.textContent = monitorName || 'this monitor';
    DOM.modalDelete.style.display = 'flex';
  }

  function closeDeleteModal() {
    DOM.modalDelete.style.display = 'none';
    state.deleteTargetId = null;
  }

  async function confirmDeleteMonitor() {
    if (!state.deleteTargetId) return;
    const id = state.deleteTargetId;

    try {
      await apiFetch(`/api/monitors/${id}`, { method: 'DELETE' });
      showToast('Monitor deleted.', 'success');
      closeDeleteModal();
      refreshAllData(true);
    } catch (err) {
      showToast(err.message || 'Failed to delete monitor.', 'error');
    }
  }

  async function handleManualCheck(monitorId, buttonElement) {
    if (!buttonElement) return;
    const origHtml = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = `<span class="spin-icon" style="display:inline-block;">⟳</span> Checking...`;

    try {
      const result = await apiFetch(`/api/monitors/${monitorId}/check`, { method: 'POST' });
      if (result.is_success) {
        showToast(`Check succeeded: HTTP ${result.status_code || 200} in ${result.response_time_ms}ms`, 'success');
      } else {
        showToast(`Check failed: ${result.error_category || 'Error'} (${result.error_message || ''})`, 'error');
      }
      refreshAllData(true);
    } catch (err) {
      showToast(err.message || 'Check request failed.', 'error');
    } finally {
      buttonElement.disabled = false;
      buttonElement.innerHTML = origHtml;
    }
  }

  async function handleToggleMonitor(monitorId) {
    try {
      const updated = await apiFetch(`/api/monitors/${monitorId}/toggle`, { method: 'POST' });
      showToast(`Monitor ${updated.is_enabled ? 'resumed' : 'paused'}.`, 'info');
      refreshAllData(true);
    } catch (err) {
      showToast(err.message || 'Failed to toggle monitor state.', 'error');
    }
  }

  /* ==========================================================================
     Countdown & Auto-Refresh Timer
     ========================================================================== */

  function startCountdownTimer() {
    resetCountdown();
    if (state.countdownInterval) clearInterval(state.countdownInterval);

    state.countdownInterval = setInterval(() => {
      state.countdown -= 1;
      if (state.countdown <= 0) {
        state.countdown = 15;
        refreshAllData(true);
      }
      DOM.countdownText.textContent = `${state.countdown}s`;
    }, 1000);
  }

  function resetCountdown() {
    state.countdown = 15;
    DOM.countdownText.textContent = '15s';
  }

  /* ==========================================================================
     Event Listeners Setup
     ========================================================================== */

  function setupEventListeners() {
    // Navigation
    DOM.navItems.forEach(item => {
      item.addEventListener('click', () => switchView(item.dataset.view));
    });

    // Mobile Menu
    DOM.mobileMenuToggle.addEventListener('click', () => {
      DOM.sidebar.classList.toggle('open');
    });

    // Theme Toggle
    DOM.themeToggle.addEventListener('click', toggleTheme);

    // Refresh CTA
    DOM.btnRefreshData.addEventListener('click', () => refreshAllData(false));

    // Add Monitor CTA
    DOM.btnOpenCreateModal.addEventListener('click', openCreateModal);
    DOM.btnEmptyAddMonitor.addEventListener('click', openCreateModal);

    // Direct Jump Buttons
    DOM.btnBannerViewIncidents.addEventListener('click', () => switchView('incidents'));
    DOM.btnLinkAllIncidents.addEventListener('click', () => switchView('incidents'));
    DOM.btnQuickManage.addEventListener('click', () => switchView('monitors'));

    // Search & Filter
    DOM.filterSearch.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      renderMonitors();
    });

    DOM.filterStatusPills.addEventListener('click', (e) => {
      const pill = e.target.closest('.tab-pill');
      if (!pill) return;
      DOM.filterStatusPills.querySelectorAll('.tab-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.filterStatus = pill.dataset.filter;
      renderMonitors();
    });

    DOM.sortSelect.addEventListener('change', (e) => {
      state.sortBy = e.target.value;
      renderMonitors();
    });

    // Monitor Actions delegation (Overview and Monitors Grid)
    document.addEventListener('click', (e) => {
      const checkBtn = e.target.closest('.btn-check-now');
      if (checkBtn) {
        const id = parseInt(checkBtn.dataset.id, 10);
        handleManualCheck(id, checkBtn);
        return;
      }

      const toggleBtn = e.target.closest('.btn-toggle');
      if (toggleBtn) {
        const id = parseInt(toggleBtn.dataset.id, 10);
        handleToggleMonitor(id);
        return;
      }

      const editBtn = e.target.closest('.btn-edit');
      if (editBtn) {
        const id = parseInt(editBtn.dataset.id, 10);
        openEditModal(id);
        return;
      }

      const deleteBtn = e.target.closest('.btn-delete');
      if (deleteBtn) {
        const id = parseInt(deleteBtn.dataset.id, 10);
        const name = deleteBtn.dataset.name;
        openDeleteModal(id, name);
        return;
      }

      const analyticsJumpBtn = e.target.closest('.btn-analytics-jump');
      if (analyticsJumpBtn) {
        const id = parseInt(analyticsJumpBtn.dataset.id, 10);
        state.selectedMonitorId = id;
        switchView('history');
        return;
      }
    });

    // History & Analytics controls
    DOM.analyticsMonitorSelect.addEventListener('change', (e) => {
      const val = parseInt(e.target.value, 10);
      if (val) loadAnalytics(val, state.analyticsHours);
    });

    DOM.timeWindowPills.addEventListener('click', (e) => {
      const pill = e.target.closest('.tab-pill');
      if (!pill) return;
      DOM.timeWindowPills.querySelectorAll('.tab-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const hours = parseInt(pill.dataset.hours, 10);
      if (state.selectedMonitorId) loadAnalytics(state.selectedMonitorId, hours);
    });

    DOM.btnExportCsv.addEventListener('click', () => {
      if (!state.selectedMonitorId) {
        showToast('Please select a monitor first.', 'info');
        return;
      }
      window.location.href = `/api/monitors/${state.selectedMonitorId}/history/export?hours=${state.analyticsHours}`;
    });

    // Settings
    DOM.settingsForm.addEventListener('submit', handleSaveSettings);

    // Modal Events
    DOM.modalCloseBtn.addEventListener('click', closeMonitorModal);
    DOM.modalCancelBtn.addEventListener('click', closeMonitorModal);
    DOM.formMonitor.addEventListener('submit', handleMonitorFormSubmit);

    DOM.deleteCloseBtn.addEventListener('click', closeDeleteModal);
    DOM.deleteCancelBtn.addEventListener('click', closeDeleteModal);
    DOM.deleteConfirmBtn.addEventListener('click', confirmDeleteMonitor);

    // Close on backdrop click
    DOM.modalMonitor.addEventListener('click', (e) => {
      if (e.target === DOM.modalMonitor) closeMonitorModal();
    });
    DOM.modalDelete.addEventListener('click', (e) => {
      if (e.target === DOM.modalDelete) closeDeleteModal();
    });

    // Keyboard ESC to close modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeMonitorModal();
        closeDeleteModal();
      }
    });
  }

  /* ==========================================================================
     Application Initialization
     ========================================================================== */

  function init() {
    applyTheme(state.theme);
    setupEventListeners();
    refreshAllData(true);
    startCountdownTimer();
  }

  // Launch on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
