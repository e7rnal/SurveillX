/**
 * SurveillX Main Application v2.0
 * Professional dashboard with charts, real-time updates, and enhanced UX
 */

class SurveillXApp {
    constructor() {
        this.currentPage = 'dashboard';
        this.socket = null;
        this.refreshInterval = null;
        this.charts = {};
    }

    // ============ INITIALIZATION ============

    async init() {
        // Check authentication
        if (!API.isAuthenticated()) {
            window.location.href = '/templates/login.html';
            return;
        }

        // Setup navigation
        this.setupNavigation();

        // Setup header actions
        this.setupHeaderActions();

        // Load initial page
        await this.loadPage('dashboard');

        // Start auto-refresh
        this.startAutoRefresh();

        // Connect WebSocket
        this.connectSocket();

        // Request notification permission
        this.requestNotificationPermission();

        // Setup mobile hamburger toggle
        this.setupMobileMenu();
    }

    setupNavigation() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                this.loadPage(page);
                // Close sidebar on mobile after nav click
                this.closeMobileMenu();
            });
        });

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                API.logout();
                Toast.info('Logged out successfully');
            });
        }
    }

    setupMobileMenu() {
        const hamburger = document.getElementById('hamburger-btn');
        const overlay = document.getElementById('sidebar-overlay');
        if (hamburger) {
            hamburger.addEventListener('click', () => this.toggleMobileMenu());
        }
        if (overlay) {
            overlay.addEventListener('click', () => this.closeMobileMenu());
        }
    }

    toggleMobileMenu() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        sidebar?.classList.toggle('open');
        overlay?.classList.toggle('show');
    }

    closeMobileMenu() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        sidebar?.classList.remove('open');
        overlay?.classList.remove('show');
    }

    setupHeaderActions() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadPage(this.currentPage);
                Toast.success('Page refreshed');
            });
        }

        // Fullscreen button
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen();
                } else {
                    document.exitFullscreen();
                }
            });
        }
    }

    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    // ============ PAGE LOADING ============

    async loadPage(page) {
        this.currentPage = page;

        // Update active nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });

        // Update page title
        const titles = {
            dashboard: 'Dashboard Overview',
            live: 'Live Monitor',
            attendance: 'Attendance Records',
            alerts: 'Security Alerts',
            students: 'Student Management',
            settings: 'System Settings',
            detection: 'Activity Detection Lab'
        };

        const titleEl = document.getElementById('page-title');
        if (titleEl) titleEl.textContent = titles[page] || 'SurveillX';

        // Show loading state
        const content = document.getElementById('main-content');
        if (!content) return;

        content.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 400px;">
                <div class="loading-spinner"></div>
            </div>
        `;

        try {
            switch (page) {
                case 'dashboard':
                    await this.loadDashboard(content);
                    break;
                case 'live':
                    await this.loadLiveMonitor(content);
                    break;
                case 'attendance':
                    await this.loadAttendance(content);
                    break;
                case 'alerts':
                    await this.loadAlerts(content);
                    break;
                case 'students':
                    await this.loadStudents(content);
                    break;
                case 'settings':
                    await this.loadSettings(content);
                    break;
                case 'detection':
                    await this.loadDetectionTest(content);
                    break;
            }

            // Add fade-in animation
            content.classList.add('fade-in');

        } catch (error) {
            content.innerHTML = `
                <div class="error-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Failed to load: ${error.message}</p>
                    <button class="btn secondary" onclick="app.loadPage('${page}')">Retry</button>
                </div>
            `;
            Toast.error('Failed to load page');
        }
    }

    // ============ DASHBOARD ============

    async loadDashboard(container) {
        const data = await API.healthCheck();
        const stats = data.stats || {};

        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon primary">
                        <i class="fa-solid fa-user-check"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value counter-animate" data-target="${stats.today_attendance || 0}">0</div>
                        <div class="stat-label">Today's Attendance</div>
                        <div class="stat-change positive">
                            <i class="fa-solid fa-arrow-up"></i> 12% from yesterday
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon success">
                        <i class="fa-solid fa-video"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value counter-animate" data-target="${stats.active_cameras || 0}">0</div>
                        <div class="stat-label">Active Cameras</div>
                        <div class="stat-change ${stats.active_cameras > 0 ? 'positive' : ''}">
                            ${stats.active_cameras > 0 ? '<i class="fa-solid fa-circle"></i> Streaming' : 'No active streams'}
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon danger">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value counter-animate" data-target="${stats.recent_alerts || 0}">0</div>
                        <div class="stat-label">Recent Alerts</div>
                        <div class="stat-change negative">
                            <i class="fa-solid fa-arrow-up"></i> Last 24 hours
                        </div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon warning">
                        <i class="fa-solid fa-users"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value counter-animate" data-target="${stats.total_students || 0}">0</div>
                        <div class="stat-label">Total Students</div>
                        <div class="stat-change positive">
                            <i class="fa-solid fa-user-plus"></i> Fully enrolled
                        </div>
                    </div>
                </div>

                <div class="stat-card">
                    <div class="stat-icon" style="background:rgba(16,185,129,0.15);color:#10b981;">
                        <i class="fa-solid fa-camera"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value counter-animate" data-target="${stats.enrolled_faces || 0}">0</div>
                        <div class="stat-label">Enrolled Faces</div>
                        <div class="stat-change positive">
                            <i class="fa-solid fa-shield-check"></i> Face recognition ready
                        </div>
                    </div>
                </div>
            </div>

            <!-- ═══ SYSTEM HEALTH ═══ -->
            <div class="dashboard-row">
                <div class="card" style="flex:1;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                        <h3 style="margin:0;"><i class="fa-solid fa-server" style="color:var(--primary);margin-right:0.4rem;"></i>System Health</h3>
                        <div style="display:flex;align-items:center;gap:0.6rem;">
                            <span id="sys-uptime" style="font-size:0.72rem;color:var(--text-secondary);"><i class="fa-solid fa-clock" style="margin-right:0.25rem;"></i>—</span>
                            <span id="sys-health-status" style="font-size:0.68rem;padding:0.15rem 0.5rem;border-radius:10px;background:rgba(16,185,129,0.15);color:#10b981;font-weight:500;"><i class="fa-solid fa-circle" style="font-size:0.35rem;vertical-align:middle;margin-right:0.2rem;"></i>Live</span>
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
                        <!-- LEFT: Gauges + Storage + Network -->
                        <div style="display:flex;flex-direction:column;gap:0.75rem;">
                            <!-- Gauges Row -->
                            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.6rem;">
                                <div class="sys-gauge-card" id="sys-cpu-gauge" style="text-align:center;padding:0.6rem 0.4rem;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;">
                                    <div class="sys-gauge-svg" style="width:76px;height:76px;margin:0 auto 0.3rem;"></div>
                                    <div style="font-size:0.78rem;font-weight:600;">CPU</div>
                                    <div id="sys-cpu-detail" style="font-size:0.65rem;color:var(--text-secondary);margin-top:0.15rem;">—</div>
                                </div>
                                <div class="sys-gauge-card" id="sys-ram-gauge" style="text-align:center;padding:0.6rem 0.4rem;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;">
                                    <div class="sys-gauge-svg" style="width:76px;height:76px;margin:0 auto 0.3rem;"></div>
                                    <div style="font-size:0.78rem;font-weight:600;">Memory</div>
                                    <div id="sys-ram-detail" style="font-size:0.65rem;color:var(--text-secondary);margin-top:0.15rem;">—</div>
                                </div>
                                <div class="sys-gauge-card" id="sys-gpu-gauge" style="text-align:center;padding:0.6rem 0.4rem;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;">
                                    <div class="sys-gauge-svg" style="width:76px;height:76px;margin:0 auto 0.3rem;"></div>
                                    <div style="font-size:0.78rem;font-weight:600;">GPU</div>
                                    <div id="sys-gpu-detail" style="font-size:0.65rem;color:var(--text-secondary);margin-top:0.15rem;">—</div>
                                </div>
                            </div>

                            <!-- Storage Volumes -->
                            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.7rem 0.8rem;">
                                <div style="font-size:0.75rem;font-weight:600;margin-bottom:0.5rem;"><i class="fa-solid fa-hard-drive" style="color:#f59e0b;margin-right:0.3rem;"></i>Storage Volumes</div>
                                <div id="sys-disks-list" style="display:flex;flex-direction:column;gap:0.4rem;">
                                    <div style="font-size:0.7rem;color:var(--text-secondary);"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>
                                </div>
                            </div>

                            <!-- Network -->
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;">
                                <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.5rem 0.7rem;text-align:center;">
                                    <div style="font-size:0.65rem;color:var(--text-secondary);margin-bottom:0.2rem;"><i class="fa-solid fa-arrow-up" style="color:#10b981;margin-right:0.2rem;"></i>Sent</div>
                                    <div id="sys-net-sent" style="font-size:0.9rem;font-weight:700;">—</div>
                                </div>
                                <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.5rem 0.7rem;text-align:center;">
                                    <div style="font-size:0.65rem;color:var(--text-secondary);margin-bottom:0.2rem;"><i class="fa-solid fa-arrow-down" style="color:#3b82f6;margin-right:0.2rem;"></i>Received</div>
                                    <div id="sys-net-recv" style="font-size:0.9rem;font-weight:700;">—</div>
                                </div>
                            </div>
                        </div>

                        <!-- RIGHT: GPU Details + AI Engines + Server -->
                        <div style="display:flex;flex-direction:column;gap:0.75rem;">
                            <!-- GPU Details -->
                            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.7rem 0.8rem;">
                                <div style="font-size:0.75rem;font-weight:600;margin-bottom:0.4rem;"><i class="fa-solid fa-microchip" style="color:#8b5cf6;margin-right:0.3rem;"></i>GPU Details</div>
                                <div id="sys-gpu-name" style="font-size:0.8rem;font-weight:600;color:var(--primary);margin-bottom:0.4rem;">—</div>
                                <div style="margin-bottom:0.4rem;">
                                    <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:var(--text-secondary);margin-bottom:0.15rem;"><span>VRAM Usage</span><span id="sys-gpu-vram-text">—</span></div>
                                    <div style="height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;"><div id="sys-gpu-vram-bar" style="height:100%;background:linear-gradient(90deg,#8b5cf6,#6366f1);border-radius:3px;transition:width 0.6s;width:0%;"></div></div>
                                </div>
                                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                                    <div style="padding:0.35rem;background:rgba(255,255,255,0.03);border-radius:6px;text-align:center;">
                                        <div style="font-size:0.6rem;color:var(--text-secondary);margin-bottom:0.1rem;">Temperature</div>
                                        <div id="sys-gpu-temp" style="font-size:1rem;font-weight:700;">—</div>
                                    </div>
                                    <div style="padding:0.35rem;background:rgba(255,255,255,0.03);border-radius:6px;text-align:center;">
                                        <div style="font-size:0.6rem;color:var(--text-secondary);margin-bottom:0.1rem;">Power Draw</div>
                                        <div id="sys-gpu-power" style="font-size:1rem;font-weight:700;">—</div>
                                    </div>
                                </div>
                            </div>

                            <!-- AI Engines -->
                            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.7rem 0.8rem;flex:1;">
                                <div style="font-size:0.75rem;font-weight:600;margin-bottom:0.4rem;"><i class="fa-solid fa-robot" style="color:#10b981;margin-right:0.3rem;"></i>AI Engines</div>
                                <div id="sys-ai-engines" style="display:flex;flex-direction:column;gap:0.3rem;">
                                    <div style="font-size:0.7rem;color:var(--text-secondary);"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>
                                </div>
                            </div>

                            <!-- Server Info -->
                            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:0.6rem 0.8rem;">
                                <div style="font-size:0.72rem;font-weight:600;margin-bottom:0.3rem;"><i class="fa-solid fa-info-circle" style="color:var(--primary);margin-right:0.3rem;"></i>Server Info</div>
                                <div style="display:flex;flex-direction:column;gap:0.2rem;font-size:0.68rem;">
                                    <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-secondary);">Hostname</span><span id="sys-hostname" style="font-weight:500;">—</span></div>
                                    <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-secondary);">Python</span><span id="sys-python" style="font-weight:500;">—</span></div>
                                    <div style="display:flex;justify-content:space-between;"><span style="color:var(--text-secondary);">OS</span><span id="sys-os" style="font-weight:500;">—</span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="dashboard-row">
                <div class="card">
                    <h3><i class="fa-solid fa-chart-line"></i> Attendance Trend (Last 7 Days)</h3>
                    <div class="chart-container" style="height: 220px;">
                        <canvas id="attendance-chart"></canvas>
                    </div>
                </div>
                <div class="card">
                    <h3><i class="fa-solid fa-chart-pie"></i> Alert Distribution</h3>
                    <div class="chart-container" style="height: 220px;">
                        <canvas id="alerts-chart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-row">
                <div class="card">
                    <h3><i class="fa-solid fa-bell"></i> Recent Alerts</h3>
                    <div id="recent-alerts-list" class="list-container">
                        <div class="skeleton" style="height: 60px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 60px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 60px;"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fa-solid fa-clock"></i> Today's Attendance</h3>
                    <div id="recent-attendance-list" class="list-container">
                        <div class="skeleton" style="height: 60px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 60px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 60px;"></div>
                    </div>
                </div>
            </div>

            <!-- Live Feed + Quick Actions -->
            <div class="dashboard-row">
                <div class="card" style="flex:1;">
                    <h3><i class="fa-solid fa-satellite-dish" style="color:var(--primary);"></i> Live Event Feed</h3>
                    <div id="live-event-feed" style="max-height:160px;overflow-y:auto;">
                        <div class="empty-state small"><i class="fa-solid fa-signal"></i><p>Waiting for events...</p></div>
                    </div>
                </div>
                <div class="card" style="min-width:280px;">
                    <h3 style="margin:0 0 0.5rem;"><i class="fa-solid fa-vial" style="color:var(--warning);"></i> Quick Actions</h3>
                    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
                        <button class="btn primary" id="test-alert-btn" style="flex:1;min-width:100px;"><i class="fa-solid fa-bolt"></i> Test Alert</button>
                        <button class="btn secondary" onclick="app.loadPage('students')" style="flex:1;min-width:100px;"><i class="fa-solid fa-user-plus"></i> Students</button>
                        <button class="btn secondary" onclick="app.loadPage('attendance')" style="flex:1;min-width:100px;"><i class="fa-solid fa-clipboard-check"></i> Attendance</button>
                    </div>
                </div>
            </div>
        `;

        // Animate counters
        this.animateCounters();

        // Load charts
        await this.loadAttendanceChart();
        await this.loadAlertsChart();

        // Load lists
        await this.loadRecentAlerts();
        await this.loadRecentAttendance();

        // Update alert badge
        document.getElementById('alert-count').textContent = stats.recent_alerts || 0;

        // Test alert button handler
        document.getElementById('test-alert-btn')?.addEventListener('click', async () => {
            try {
                const res = await API.request('/api/alerts/test', { method: 'POST' });
                Toast.success(`Test alert created: ${res.event_type} (${res.severity})`);
            } catch (e) {
                Toast.error('Failed to create test alert: ' + e.message);
            }
        });

        // Load system health + start auto-refresh
        this._loadSystemHealth();
        this._sysHealthInterval = setInterval(() => {
            if (this.currentPage === 'dashboard') {
                this._loadSystemHealth();
            } else {
                clearInterval(this._sysHealthInterval);
            }
        }, 10000);
    }

    _renderCircleGauge(container, percent, color) {
        const clamp = Math.min(100, Math.max(0, percent || 0));
        const r = 36, cx = 45, cy = 45, sw = 7;
        const circ = 2 * Math.PI * r;
        const offset = circ - (clamp / 100) * circ;
        // Dynamic color based on usage
        let fillColor = color;
        if (!color) {
            if (clamp < 60) fillColor = '#10b981';
            else if (clamp < 85) fillColor = '#f59e0b';
            else fillColor = '#ef4444';
        }
        container.innerHTML = `
            <svg viewBox="0 0 90 90" style="width:100%;height:100%;transform:rotate(-90deg);">
                <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="${sw}"/>
                <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${fillColor}" stroke-width="${sw}"
                    stroke-dasharray="${circ}" stroke-dashoffset="${offset}"
                    stroke-linecap="round" style="transition:stroke-dashoffset 0.8s ease,stroke 0.4s;"/>
            </svg>
            <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:700;color:${fillColor};transform:none;">
                ${Math.round(clamp)}%
            </div>
        `;
        container.style.position = 'relative';
    }

    async _loadSystemHealth() {
        try {
            const d = await API.request('/api/system/health');

            // Server info
            const el = (id) => document.getElementById(id);
            if (d.server) {
                const uptimeEl = el('sys-uptime');
                if (uptimeEl) uptimeEl.innerHTML = `<i class="fa-solid fa-clock" style="margin-right:0.25rem;"></i>${d.server.uptime?.text || '—'}`;
                el('sys-hostname').textContent = d.server.hostname || '—';
                el('sys-python').textContent = d.server.python || '—';
                el('sys-os').textContent = d.server.os || '—';
            }

            // CPU gauge
            const cpuGauge = document.querySelector('#sys-cpu-gauge .sys-gauge-svg');
            if (cpuGauge) this._renderCircleGauge(cpuGauge, d.cpu?.percent);
            el('sys-cpu-detail').textContent = `${d.cpu?.cores || '—'} cores · ${(d.cpu?.load_avg || [0])[0]}`;

            // RAM gauge
            const ramGauge = document.querySelector('#sys-ram-gauge .sys-gauge-svg');
            if (ramGauge) this._renderCircleGauge(ramGauge, d.memory?.percent);
            el('sys-ram-detail').textContent = `${d.memory?.used_gb || '—'} / ${d.memory?.total_gb || '—'} GB`;

            // Disks — render per-volume bars
            const disksEl = el('sys-disks-list');
            if (disksEl && d.disks) {
                disksEl.innerHTML = d.disks.map(dk => {
                    const pct = dk.percent || 0;
                    const barColor = pct < 60 ? '#10b981' : pct < 85 ? '#f59e0b' : '#ef4444';
                    return `
                        <div style="margin-bottom:0.25rem;">
                            <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:var(--text-secondary);margin-bottom:0.15rem;">
                                <span>${dk.label} <span style="opacity:0.5;font-size:0.62rem;">(${dk.mount})</span></span>
                                <span style="font-weight:600;color:${barColor};">${dk.used_gb} / ${dk.total_gb} GB · ${pct}%</span>
                            </div>
                            <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">
                                <div style="height:100%;background:${barColor};border-radius:3px;transition:width 0.6s;width:${pct}%;"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // GPU gauge
            const gpuGauge = document.querySelector('#sys-gpu-gauge .sys-gauge-svg');
            if (d.gpu?.available) {
                if (gpuGauge) this._renderCircleGauge(gpuGauge, d.gpu.utilization_percent, '#8b5cf6');
                el('sys-gpu-detail').textContent = d.gpu.name || 'GPU';
            } else {
                if (gpuGauge) this._renderCircleGauge(gpuGauge, 0, '#6b7280');
                el('sys-gpu-detail').textContent = 'No GPU';
            }

            // GPU Details
            if (d.gpu?.available) {
                el('sys-gpu-name').textContent = `NVIDIA ${d.gpu.name}`;
                el('sys-gpu-vram-text').textContent = `${d.gpu.vram_used_mb} / ${d.gpu.vram_total_mb} MB`;
                el('sys-gpu-vram-bar').style.width = `${d.gpu.vram_percent}%`;
                // Temperature color
                const temp = d.gpu.temperature_c;
                const tempColor = temp < 50 ? '#10b981' : temp < 75 ? '#f59e0b' : '#ef4444';
                el('sys-gpu-temp').innerHTML = `<span style="color:${tempColor}">${temp}°C</span>`;
                el('sys-gpu-power').textContent = `${d.gpu.power_draw_w} W`;
            }

            // Network
            if (d.network) {
                const formatNet = (mb) => mb > 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`;
                el('sys-net-sent').textContent = formatNet(d.network.bytes_sent_mb);
                el('sys-net-recv').textContent = formatNet(d.network.bytes_recv_mb);
            }

            // AI Engines
            const engEl = el('sys-ai-engines');
            if (engEl && d.ai_engines) {
                engEl.innerHTML = d.ai_engines.map(e => {
                    const color = e.status === 'active' ? '#10b981' : e.status === 'standby' ? '#f59e0b' : '#ef4444';
                    const icon = e.status === 'active' ? 'fa-circle-check' : e.status === 'standby' ? 'fa-clock' : 'fa-circle-xmark';
                    const label = e.status === 'active' ? 'Active' : e.status === 'standby' ? 'Standby' : 'Offline';
                    return `
                        <div style="display:flex;align-items:center;justify-content:space-between;padding:0.4rem 0.5rem;background:rgba(255,255,255,0.02);border-radius:6px;">
                            <div style="display:flex;align-items:center;gap:0.4rem;">
                                <i class="fa-solid ${e.icon}" style="font-size:0.75rem;color:${color};width:18px;text-align:center;"></i>
                                <div>
                                    <div style="font-size:0.78rem;font-weight:500;">${e.name}</div>
                                    <div style="font-size:0.62rem;color:var(--text-secondary);">${e.model}</div>
                                </div>
                            </div>
                            <span style="font-size:0.65rem;padding:0.1rem 0.4rem;border-radius:8px;background:${color}15;color:${color};font-weight:600;">
                                <i class="fa-solid ${icon}" style="font-size:0.5rem;margin-right:0.2rem;"></i>${label}
                            </span>
                        </div>
                    `;
                }).join('');
            }

        } catch (e) {
            console.warn('System health fetch failed:', e);
        }
    }

    animateCounters() {
        document.querySelectorAll('.counter-animate').forEach(counter => {
            const target = parseInt(counter.dataset.target) || 0;
            const duration = 800;
            const step = target / (duration / 16);
            let current = 0;

            const timer = setInterval(() => {
                current += step;
                if (current >= target) {
                    counter.textContent = target;
                    clearInterval(timer);
                } else {
                    counter.textContent = Math.floor(current);
                }
            }, 16);
        });
    }

    async loadAttendanceChart() {
        const ctx = document.getElementById('attendance-chart');
        if (!ctx) return;

        try {
            const res = await API.request('/api/attendance/trend?days=7');
            const trend = res.trend || [];
            const labels = trend.map(t => {
                const d = new Date(t.date + 'T00:00:00');
                return d.toLocaleDateString('en-IN', { weekday: 'short', timeZone: 'Asia/Kolkata' });
            });
            const data = trend.map(t => t.count);

            this.charts.attendance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [{
                        label: 'Students Present',
                        data,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#6366f1',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.5)' } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.5)', stepSize: 1 }, beginAtZero: true }
                    }
                }
            });
        } catch (e) {
            console.warn('Attendance chart error:', e);
        }
    }

    async loadAlertsChart() {
        const ctx = document.getElementById('alerts-chart');
        if (!ctx) return;

        const colorMap = {
            running: '#f59e0b',
            fighting: '#ef4444',
            loitering: '#3b82f6',
            unauthorized_entry: '#8b5cf6',
            suspicious_activity: '#ec4899',
        };
        const fallbackColors = ['#6b7280', '#14b8a6', '#f97316', '#84cc16', '#a855f7'];

        try {
            const res = await API.request('/api/alerts/distribution?days=30');
            const dist = res.distribution || [];

            if (dist.length === 0) {
                ctx.parentElement.innerHTML = '<div class="empty-state small"><i class="fa-solid fa-chart-pie"></i><p>No alerts in the last 30 days</p></div>';
                return;
            }

            const labels = dist.map(d => this.formatEventType(d.event_type));
            const data = dist.map(d => d.count);
            const colors = dist.map((d, i) => colorMap[d.event_type] || fallbackColors[i % fallbackColors.length]);

            this.charts.alerts = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels,
                    datasets: [{ data, backgroundColor: colors, borderWidth: 0 }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: { color: 'rgba(255,255,255,0.7)', padding: 15, usePointStyle: true }
                        }
                    }
                }
            });
        } catch (e) {
            console.warn('Alerts chart error:', e);
        }
    }

    async loadRecentAlerts() {
        try {
            const data = await API.getAlerts({ limit: 5 });
            const container = document.getElementById('recent-alerts-list');
            if (!container) return;

            if (!data.alerts || data.alerts.length === 0) {
                container.innerHTML = '<div class="empty-state small"><i class="fa-solid fa-check-circle"></i><p>No recent alerts</p></div>';
                return;
            }

            container.innerHTML = data.alerts.map(alert => `
                <div class="list-item" style="cursor:pointer;transition:background 0.15s;" onclick="app.viewAlertDetail(${alert.id})" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">
                    <div class="item-icon ${alert.severity}">
                        <i class="fa-solid fa-${this.getAlertIcon(alert.event_type)}"></i>
                    </div>
                    <div class="item-content">
                        <div class="item-title">${this.formatEventType(alert.event_type)}</div>
                        <div class="item-subtitle">${this.timeAgo(alert.timestamp)}</div>
                    </div>
                    <span class="badge ${alert.severity}">${alert.severity}</span>
                </div>
            `).join('');
        } catch (error) {
            document.getElementById('recent-alerts-list').innerHTML =
                '<div class="error-state">Failed to load alerts</div>';
        }
    }

    async loadRecentAttendance() {
        try {
            const data = await API.getTodayAttendance();
            const container = document.getElementById('recent-attendance-list');
            if (!container) return;

            if (!data.records || data.records.length === 0) {
                container.innerHTML = '<div class="empty-state small"><i class="fa-solid fa-calendar-xmark"></i><p>No attendance today</p></div>';
                return;
            }

            container.innerHTML = data.records.slice(0, 5).map(record => `
                <div class="list-item">
                    <div class="avatar">${record.student_name?.[0] || '?'}</div>
                    <div class="item-content">
                        <div class="item-title">${record.student_name || 'Unknown'}</div>
                        <div class="item-subtitle">${new Date(record.timestamp).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true })}</div>
                    </div>
                    <span class="badge success">Present</span>
                </div>
            `).join('');
        } catch (error) {
            document.getElementById('recent-attendance-list').innerHTML =
                '<div class="error-state">Failed to load attendance</div>';
        }
    }

    // ============ LIVE MONITOR ============

    async loadLiveMonitor(container) {
        try {
            // Load the multi-camera grid partial
            const response = await fetch('/api/partials/live');
            if (!response.ok) throw new Error('Failed to load live monitor');

            const html = await response.text();

            // Create a temporary div to parse the HTML
            const temp = document.createElement('div');
            temp.innerHTML = html;

            // Extract script content
            const scripts = temp.querySelectorAll('script');
            const scriptContents = [];
            scripts.forEach(script => {
                scriptContents.push(script.textContent);
                script.remove(); // Remove script tags from HTML
            });

            // Insert HTML first
            container.innerHTML = temp.innerHTML;

            // Execute scripts after HTML is inserted
            scriptContents.forEach(scriptContent => {
                const script = document.createElement('script');
                script.textContent = scriptContent;
                document.body.appendChild(script);
            });

            console.log('Multi-camera grid loaded successfully');

        } catch (error) {
            console.error('Error loading live monitor:', error);
            container.innerHTML = `
                <div class="error-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Failed to load live monitor</p>
                    <button class="btn secondary" onclick="app.loadPage('live')">Retry</button>
                </div>
            `;
        }
    }

    toggleFullscreen() {
        const feedContainer = document.querySelector('.feed-container');
        if (!document.fullscreenElement) {
            feedContainer.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    captureSnapshot() {
        const canvas = document.getElementById('main-canvas');
        if (!canvas) return;

        const link = document.createElement('a');
        link.download = `snapshot_${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();

        Toast.success('Snapshot saved!');
    }

    // ============ STUDENTS ============

    async loadStudents(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="tabs">
                    <button class="tab-btn active" data-tab="enrolled">Enrolled Students</button>
                    <button class="tab-btn" data-tab="pending">Pending Enrollments</button>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;">
                    <div style="display:flex;align-items:center;gap:0;">
                        <input type="text" id="student-search" placeholder="Search name or roll no..." style="padding:0.5rem 1rem;border-radius:var(--border-radius-sm) 0 0 var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);border-right:none;background:var(--bg-card);color:white;outline:none;width:200px;">
                        <button class="btn primary" id="student-search-btn" style="border-radius:0 var(--border-radius-sm) var(--border-radius-sm) 0;padding:0.5rem 0.75rem;">
                            <i class="fa-solid fa-search"></i>
                        </button>
                    </div>
                    <button class="btn primary" id="add-student-btn">
                        <i class="fa-solid fa-user-plus"></i> Add Student
                    </button>
                    <button class="btn secondary" id="import-csv-btn">
                        <i class="fa-solid fa-file-csv"></i> Import CSV
                    </button>
                    <button class="btn secondary" id="generate-link-btn">
                        <i class="fa-solid fa-link"></i> Enrollment Link
                    </button>
                </div>
            </div>
            
            <div class="card">
                <div id="students-tab-content">
                    <div class="skeleton" style="height: 50px; margin-bottom: 0.5rem;"></div>
                    <div class="skeleton" style="height: 50px; margin-bottom: 0.5rem;"></div>
                    <div class="skeleton" style="height: 50px;"></div>
                </div>
            </div>
            
            <!-- Add Student Modal -->
            <div id="add-student-modal" class="modal">
                <div class="modal-content" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>Add New Student</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label>Full Name *</label>
                            <input type="text" id="new-student-name" placeholder="John Doe" required>
                        </div>
                        <div class="form-group">
                            <label>Roll Number *</label>
                            <input type="text" id="new-student-roll" placeholder="CS2024001" required>
                        </div>
                        <div class="form-group">
                            <label>Class</label>
                            <select id="new-student-class" style="padding:0.5rem;border-radius:var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;">
                                <option value="">Select Class</option>
                                <option value="BCA-I">BCA-I</option>
                                <option value="BCA-II">BCA-II</option>
                                <option value="BCA-III">BCA-III</option>
                                <option value="MCA-I">MCA-I</option>
                                <option value="MCA-II">MCA-II</option>
                                <option value="BSc-IT-I">BSc-IT-I</option>
                                <option value="BSc-IT-II">BSc-IT-II</option>
                                <option value="BSc-IT-III">BSc-IT-III</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Contact Number</label>
                            <input type="text" id="new-student-contact" placeholder="+91 98765 43210">
                        </div>
                        
                        <!-- 5 Photo Upload -->
                        <div class="form-group">
                            <label>Face Photos (5 required) *</label>
                            <p class="hint" style="margin-bottom: 0.8rem;">Upload 5 photos of the student from different angles for accurate face recognition.</p>
                            <div id="photo-upload-grid" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem;">
                                ${['Front Face', 'Left Side', 'Right Side', 'Look Up', 'Look Down'].map((pose, i) => `
                                    <div class="photo-slot" data-index="${i}" style="
                                        border: 2px dashed var(--border);
                                        border-radius: 8px;
                                        aspect-ratio: 1;
                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        justify-content: center;
                                        cursor: pointer;
                                        position: relative;
                                        overflow: hidden;
                                        background: var(--bg-tertiary);
                                        transition: border-color 0.2s;
                                    ">
                                        <i class="fa-solid fa-camera" style="font-size: 1.2rem; color: var(--text-secondary); margin-bottom: 4px;"></i>
                                        <span style="font-size: 0.65rem; color: var(--text-secondary); text-align: center;">${pose}</span>
                                        <input type="file" accept="image/*" capture="user" style="display:none;" data-photo-index="${i}">
                                    </div>
                                `).join('')}
                            </div>
                            <p id="photo-count-label" class="hint" style="margin-top: 0.5rem;">0/5 photos added</p>
                        </div>
                        
                        <button class="btn primary full-width" id="save-student-btn">
                            <i class="fa-solid fa-check"></i> Add Student
                        </button>
                    </div>
                </div>
            </div>

            <!-- Enrollment Link Modal -->
            <div id="enrollment-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Generate Enrollment Link</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label>Student Email</label>
                            <input type="email" id="enroll-email" placeholder="student@example.com">
                            <p class="hint">Student will receive enrollment link via email</p>
                        </div>
                        <div class="form-group">
                            <label>Roll Number (Optional)</label>
                            <input type="text" id="enroll-roll-no" placeholder="CS2024001">
                        </div>
                        <button class="btn primary full-width" id="generate-btn">
                            <i class="fa-solid fa-paper-plane"></i> Generate & Send Link
                        </button>
                        
                        <div id="link-result" class="link-result" style="display: none;">
                            <div class="qr-code">
                                <img id="qr-image" src="" alt="QR Code">
                            </div>
                            <div class="link-display">
                                <input type="text" id="enrollment-link" readonly>
                                <button class="btn" id="copy-link-btn">
                                    <i class="fa-solid fa-copy"></i>
                                </button>
                            </div>
                            <p class="hint">Link expires in 24 hours</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Setup tabs
        container.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.loadStudentTab(btn.dataset.tab);
            });
        });

        // Setup Add Student modal
        const addModal = document.getElementById('add-student-modal');
        this._studentPhotos = [null, null, null, null, null]; // 5 photo slots
        const poses = ['Front Face', 'Left Side', 'Right Side', 'Look Up', 'Look Down'];

        document.getElementById('add-student-btn').addEventListener('click', () => {
            addModal.classList.add('show');
        });
        addModal.querySelector('.close-modal').addEventListener('click', () => {
            addModal.classList.remove('show');
        });

        // Photo slot click → open file picker
        document.querySelectorAll('.photo-slot').forEach(slot => {
            const idx = parseInt(slot.dataset.index);
            const fileInput = slot.querySelector('input[type="file"]');

            slot.addEventListener('click', () => fileInput.click());

            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const reader = new FileReader();
                reader.onload = (ev) => {
                    this._studentPhotos[idx] = ev.target.result; // base64 data URL
                    // Show preview
                    slot.innerHTML = `
                        <img src="${ev.target.result}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;">
                        <button class="photo-remove-btn" data-rm-index="${idx}" style="
                            position:absolute; top:2px; right:2px;
                            background:rgba(0,0,0,0.6); color:#fff;
                            border:none; border-radius:50%; width:20px; height:20px;
                            cursor:pointer; font-size:12px; line-height:20px; text-align:center;
                        ">&times;</button>
                        <input type="file" accept="image/*" capture="user" style="display:none;" data-photo-index="${idx}">
                    `;
                    // Re-bind click
                    const newInput = slot.querySelector('input[type="file"]');
                    slot.onclick = () => newInput.click();
                    newInput.addEventListener('change', arguments.callee);

                    // Remove button
                    slot.querySelector('.photo-remove-btn').addEventListener('click', (ev2) => {
                        ev2.stopPropagation();
                        this._studentPhotos[idx] = null;
                        slot.innerHTML = `
                            <i class="fa-solid fa-camera" style="font-size:1.2rem;color:var(--text-secondary);margin-bottom:4px;"></i>
                            <span style="font-size:0.65rem;color:var(--text-secondary);text-align:center;">${poses[idx]}</span>
                            <input type="file" accept="image/*" capture="user" style="display:none;" data-photo-index="${idx}">
                        `;
                        const resetInput = slot.querySelector('input[type="file"]');
                        slot.onclick = () => resetInput.click();
                        resetInput.addEventListener('change', arguments.callee);
                        this._updatePhotoCount();
                    });

                    this._updatePhotoCount();
                };
                reader.readAsDataURL(file);
            });
        });

        // Save student handler (with photos)
        document.getElementById('save-student-btn').addEventListener('click', async () => {
            const name = document.getElementById('new-student-name').value.trim();
            const rollNo = document.getElementById('new-student-roll').value.trim();
            const className = document.getElementById('new-student-class').value.trim();
            const contactNo = document.getElementById('new-student-contact').value.trim();

            if (!name || !rollNo) {
                Toast.error('Name and Roll Number are required');
                return;
            }

            const photos = this._studentPhotos.filter(p => p !== null);
            if (photos.length < 5) {
                Toast.error(`Please upload all 5 photos (${photos.length}/5 added)`);
                return;
            }

            const btn = document.getElementById('save-student-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';

            try {
                const photoData = photos.map((p, i) => ({ data: p, pose: poses[i] }));
                await API.addStudent({
                    name, roll_no: rollNo, class: className, contact_no: contactNo,
                    photos: photoData
                });
                Toast.success('Student added with face encoding!');
                addModal.classList.remove('show');
                // Clear form
                document.getElementById('new-student-name').value = '';
                document.getElementById('new-student-roll').value = '';
                document.getElementById('new-student-class').value = '';
                document.getElementById('new-student-contact').value = '';
                this._studentPhotos = [null, null, null, null, null];
                // Refresh students list
                await this.loadStudentTab('enrolled');
            } catch (error) {
                Toast.error('Failed to add student: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Add Student';
            }
        });

        // Setup enrollment modal
        const modal = document.getElementById('enrollment-modal');
        document.getElementById('generate-link-btn').addEventListener('click', () => {
            modal.classList.add('show');
        });
        modal.querySelector('.close-modal').addEventListener('click', () => {
            modal.classList.remove('show');
        });

        // Generate link handler
        document.getElementById('generate-btn').addEventListener('click', async () => {
            const email = document.getElementById('enroll-email').value;
            const rollNo = document.getElementById('enroll-roll-no').value;

            if (!email) {
                Toast.error('Please enter student email');
                return;
            }

            try {
                const data = await API.generateEnrollmentLink(email, rollNo);
                const link = `${window.location.origin}/enroll?token=${data.token}`;

                document.getElementById('enrollment-link').value = link;
                document.getElementById('qr-image').src =
                    `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(link)}`;
                document.getElementById('link-result').style.display = 'block';

                Toast.success('Enrollment link generated and emailed!');
            } catch (error) {
                Toast.error('Failed to generate link: ' + error.message);
            }
        });

        // Copy link handler
        document.getElementById('copy-link-btn').addEventListener('click', () => {
            const input = document.getElementById('enrollment-link');
            input.select();
            document.execCommand('copy');
            Toast.success('Link copied to clipboard!');
        });

        // Search handler (debounced auto-search on type)
        document.getElementById('student-search').addEventListener('input', () => {
            clearTimeout(this._studentSearchTimeout);
            this._studentSearchTimeout = setTimeout(() => this.loadStudentTab('enrolled'), 300);
        });

        // Search button click handler
        document.getElementById('student-search-btn').addEventListener('click', () => {
            this.loadStudentTab('enrolled');
        });

        // Enter key in search field
        document.getElementById('student-search').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(this._studentSearchTimeout);
                this.loadStudentTab('enrolled');
            }
        });

        // CSV import handler
        document.getElementById('import-csv-btn').addEventListener('click', () => {
            this.showCSVImportModal();
        });

        // Load initial tab
        await this.loadStudentTab('enrolled');
    }

    _updatePhotoCount() {
        const count = this._studentPhotos ? this._studentPhotos.filter(p => p !== null).length : 0;
        const label = document.getElementById('photo-count-label');
        if (label) {
            label.textContent = `${count}/5 photos added`;
            label.style.color = count === 5 ? 'var(--success)' : 'var(--text-secondary)';
        }
    }

    async loadStudentTab(tab) {
        const content = document.getElementById('students-tab-content');

        if (tab === 'enrolled') {
            try {
                const search = document.getElementById('student-search')?.value?.trim() || '';
                const data = await API.getStudents({ search });

                if (!data.students || data.students.length === 0) {
                    content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-users-slash"></i><p>No enrolled students</p></div>';
                    return;
                }

                const enrolled = data.students.filter(s => s.has_face_encoding).length;
                const total = data.students.length;

                content.innerHTML = `
                    <div style="display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;">
                        <div style="background:var(--bg-tertiary);padding:0.6rem 1rem;border-radius:var(--border-radius-sm);font-size:0.85rem;">
                            <i class="fa-solid fa-users" style="color:var(--primary);margin-right:0.4rem;"></i>
                            <strong>${total}</strong> Total
                        </div>
                        <div style="background:var(--bg-tertiary);padding:0.6rem 1rem;border-radius:var(--border-radius-sm);font-size:0.85rem;">
                            <i class="fa-solid fa-camera" style="color:var(--success);margin-right:0.4rem;"></i>
                            <strong>${enrolled}</strong> Enrolled
                        </div>
                        <div style="background:var(--bg-tertiary);padding:0.6rem 1rem;border-radius:var(--border-radius-sm);font-size:0.85rem;">
                            <i class="fa-solid fa-exclamation-triangle" style="color:var(--warning);margin-right:0.4rem;"></i>
                            <strong>${total - enrolled}</strong> Not Enrolled
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Roll No</th>
                                <th>Class</th>
                                <th>Face</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.students.map(s => `
                                <tr>
                                    <td>
                                        <div class="user-cell">
                                            <div class="avatar">${s.name[0]}</div>
                                            <span>${s.name}</span>
                                        </div>
                                    </td>
                                    <td>${s.roll_no}</td>
                                    <td>${s.class || '-'}</td>
                                    <td>
                                        ${s.has_face_encoding
                        ? `<span class="badge success" style="font-size:0.7rem;"><i class="fa-solid fa-check-circle"></i> ${s.face_count || 0} photos</span>`
                        : '<span class="badge" style="background:rgba(239,68,68,0.15);color:#ef4444;font-size:0.7rem;"><i class="fa-solid fa-camera-slash"></i> Not Enrolled</span>'}
                                    </td>
                                    <td>
                                        <button class="btn-icon" onclick="app.viewStudent(${s.id})" title="View & Enroll Face"><i class="fa-solid fa-eye"></i></button>
                                        <button class="btn-icon" onclick="app.editStudent(${s.id})" title="Edit"><i class="fa-solid fa-pen"></i></button>
                                        <button class="btn-icon danger" onclick="app.deleteStudent(${s.id})" title="Delete">
                                            <i class="fa-solid fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } catch (error) {
                content.innerHTML = `<div class="error-state">Failed to load: ${error.message}</div>`;
            }
        } else {
            // Pending enrollments
            try {
                const data = await API.getPendingEnrollments();

                if (!data.enrollments || data.enrollments.length === 0) {
                    content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-check-circle"></i><p>No pending enrollments</p></div>';
                    return;
                }

                // Store enrollment data for review modal
                this._pendingEnrollments = {};
                data.enrollments.forEach(e => { this._pendingEnrollments[e.id] = e; });

                content.innerHTML = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Roll No</th>
                                <th>Submitted</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.enrollments.map(e => `
                                <tr>
                                    <td>
                                        <div class="user-cell">
                                            <div class="avatar">${e.name[0]}</div>
                                            <span>${e.name}</span>
                                        </div>
                                    </td>
                                    <td>${e.email || '-'}</td>
                                    <td>${e.roll_no || '-'}</td>
                                    <td>${this.timeAgo(e.submitted_at)}</td>
                                    <td>
                                        <button class="btn small" onclick="app.reviewEnrollment(${e.id})" style="background:rgba(99,102,241,0.15);color:#818cf8;border:1px solid rgba(99,102,241,0.3);margin-right:4px;">
                                            <i class="fa-solid fa-eye"></i> Review
                                        </button>
                                        <button class="btn small success" onclick="app.approveEnrollment(${e.id})">
                                            <i class="fa-solid fa-check"></i>
                                        </button>
                                        <button class="btn small danger" onclick="app.rejectEnrollment(${e.id})">
                                            <i class="fa-solid fa-times"></i>
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                    `;
            } catch (error) {
                content.innerHTML = `<div class="error-state">Failed to load: ${error.message}</div>`;
            }
        }
    }

    reviewEnrollment(id) {
        const e = this._pendingEnrollments?.[id];
        if (!e) { Toast.error('Enrollment data not found'); return; }

        // Parse sample_images
        let photos = [];
        if (e.sample_images) {
            try {
                photos = typeof e.sample_images === 'string' ? JSON.parse(e.sample_images) : e.sample_images;
            } catch (err) { photos = []; }
        }
        const poseLabels = ['Front Face', 'Left Turn', 'Right Turn', 'Look Up', 'Neutral'];

        // Remove old modal
        document.getElementById('enrollment-review-modal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'enrollment-review-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);';
        modal.innerHTML = `
                    <div style="background:#1e293b;border-radius:1rem;padding:1.5rem;max-width:560px;width:95%;max-height:90vh;overflow-y:auto;border:1px solid rgba(255,255,255,0.1);box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                    <h3 style="color:white;font-size:1.1rem;margin:0;"><i class="fa-solid fa-user-clock" style="color:#818cf8;margin-right:0.5rem;"></i>Enrollment Review</h3>
                    <button onclick="document.getElementById('enrollment-review-modal').remove()" style="background:none;border:none;color:#94a3b8;font-size:1.2rem;cursor:pointer;">&times;</button>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1.25rem;">
                    <div style="background:#0f172a;padding:0.75rem;border-radius:0.5rem;">
                        <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Name</div>
                        <div style="color:white;font-weight:600;margin-top:0.25rem;">${e.name}</div>
                    </div>
                    <div style="background:#0f172a;padding:0.75rem;border-radius:0.5rem;">
                        <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Roll No</div>
                        <div style="color:white;font-weight:600;margin-top:0.25rem;">${e.roll_no || '-'}</div>
                    </div>
                    <div style="background:#0f172a;padding:0.75rem;border-radius:0.5rem;">
                        <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Class</div>
                        <div style="color:white;font-weight:600;margin-top:0.25rem;">${e.class || '-'}</div>
                    </div>
                    <div style="background:#0f172a;padding:0.75rem;border-radius:0.5rem;">
                        <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Contact</div>
                        <div style="color:white;font-weight:600;margin-top:0.25rem;">${e.contact_no || '-'}</div>
                    </div>
                    <div style="background:#0f172a;padding:0.75rem;border-radius:0.5rem;">
                        <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Email</div>
                        <div style="color:white;font-weight:600;margin-top:0.25rem;">${e.email || '-'}</div>
                    </div>
                    <div style="background:#0f172a;padding:0.75rem;border-radius:0.5rem;">
                        <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Submitted</div>
                        <div style="color:white;font-weight:600;margin-top:0.25rem;">${this.timeAgo(e.submitted_at)}</div>
                    </div>
                </div>

                <div style="margin-bottom:1rem;">
                    <div style="color:#94a3b8;font-size:0.8rem;font-weight:600;margin-bottom:0.5rem;"><i class="fa-solid fa-camera" style="margin-right:0.4rem;"></i>Face Photos (${photos.length}/5)</div>
                    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.4rem;">
                        ${photos.length > 0 ? photos.map((p, i) => {
            const src = typeof p === 'object' ? (p.data || '') : p;
            return `
                                <div style="aspect-ratio:1;background:#0f172a;border-radius:0.4rem;overflow:hidden;border:2px solid rgba(34,197,94,0.4);position:relative;">
                                    <img src="${src}" style="width:100%;height:100%;object-fit:cover;" alt="${poseLabels[i] || 'Photo'}">
                                    <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,0.8));padding:0.15rem;text-align:center;">
                                        <span style="font-size:0.5rem;color:#94a3b8;">${poseLabels[i] || ''}</span>
                                    </div>
                                </div>`;
        }).join('') : '<div style="grid-column:1/-1;text-align:center;color:#64748b;padding:1rem;">No photos available</div>'}
                    </div>
                </div>

                ${e.face_encoding ? '<div style="display:flex;align-items:center;gap:0.4rem;color:#22c55e;font-size:0.8rem;margin-bottom:1rem;"><i class="fa-solid fa-shield-check"></i> Face encoding pre-computed</div>' : '<div style="display:flex;align-items:center;gap:0.4rem;color:#f59e0b;font-size:0.8rem;margin-bottom:1rem;"><i class="fa-solid fa-exclamation-triangle"></i> Face encoding will be computed on approval</div>'}

                <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                    <button onclick="document.getElementById('enrollment-review-modal').remove();app.rejectEnrollment(${e.id})" style="padding:0.6rem 1.25rem;border-radius:0.5rem;background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);cursor:pointer;font-weight:600;font-family:inherit;">
                        <i class="fa-solid fa-times"></i> Reject
                    </button>
                    <button onclick="document.getElementById('enrollment-review-modal').remove();app.approveEnrollment(${e.id})" style="padding:0.6rem 1.25rem;border-radius:0.5rem;background:#22c55e;color:white;border:none;cursor:pointer;font-weight:600;font-family:inherit;">
                        <i class="fa-solid fa-check"></i> Approve
                    </button>
                </div>
            </div>
                    `;

        // Close on backdrop click
        modal.addEventListener('click', (ev) => { if (ev.target === modal) modal.remove(); });
        document.body.appendChild(modal);
    }

    async approveEnrollment(id) {
        if (!confirm('Approve this enrollment?')) return;
        try {
            await API.approveEnrollment(id);
            Toast.success('Enrollment approved!');
            this.loadStudentTab('pending');
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    async rejectEnrollment(id) {
        const reason = prompt('Reason for rejection:');
        if (!reason) return;
        try {
            await API.rejectEnrollment(id, reason);
            Toast.info('Enrollment rejected');
            this.loadStudentTab('pending');
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    async deleteStudent(id) {
        if (!confirm('Delete this student? This cannot be undone.')) return;
        try {
            await API.deleteStudent(id);
            Toast.success('Student deleted');
            this.loadStudentTab('enrolled');
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    showCSVImportModal() {
        document.getElementById('csv-import-modal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'csv-import-modal';
        modal.className = 'modal show';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:500px;">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-file-csv" style="margin-right:0.5rem;color:var(--primary);"></i>Import Students from CSV</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:1rem;">
                        Upload a CSV file with columns: <code>name, roll_no, class, contact_no</code><br>
                        First row should be headers.
                    </p>
                    <div style="border:2px dashed var(--border);border-radius:8px;padding:2rem;text-align:center;cursor:pointer;background:var(--bg-tertiary);transition:border-color 0.2s;" id="csv-drop-zone">
                        <i class="fa-solid fa-cloud-arrow-up" style="font-size:2rem;color:var(--primary);margin-bottom:0.5rem;display:block;"></i>
                        <p style="margin:0;color:var(--text-secondary);">Click or drag CSV file here</p>
                        <input type="file" accept=".csv" id="csv-file-input" style="display:none;">
                    </div>
                    <div id="csv-result" style="display:none;margin-top:1rem;"></div>
                    <button class="btn primary full-width" id="csv-upload-btn" style="margin-top:1rem;" disabled>
                        <i class="fa-solid fa-upload"></i> Import
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

        const dropZone = modal.querySelector('#csv-drop-zone');
        const fileInput = modal.querySelector('#csv-file-input');
        let selectedFile = null;

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = 'var(--primary)'; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = 'var(--border)'; });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--border)';
            const file = e.dataTransfer.files[0];
            if (file && file.name.endsWith('.csv')) {
                selectedFile = file;
                dropZone.innerHTML = `<i class="fa-solid fa-file-csv" style="font-size:2rem;color:var(--success);"></i><p style="margin:0.5rem 0 0;color:var(--text-primary);">${file.name}</p>`;
                modal.querySelector('#csv-upload-btn').disabled = false;
            }
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                selectedFile = e.target.files[0];
                dropZone.innerHTML = `<i class="fa-solid fa-file-csv" style="font-size:2rem;color:var(--success);"></i><p style="margin:0.5rem 0 0;color:var(--text-primary);">${selectedFile.name}</p>`;
                modal.querySelector('#csv-upload-btn').disabled = false;
            }
        });

        modal.querySelector('#csv-upload-btn').addEventListener('click', async () => {
            if (!selectedFile) return;
            const btn = modal.querySelector('#csv-upload-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Importing...';

            const formData = new FormData();
            formData.append('file', selectedFile);

            try {
                const resp = await fetch('/api/students/import-csv', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('jwt_token')}` },
                    body: formData
                });
                const result = await resp.json();
                const resultDiv = modal.querySelector('#csv-result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <div style="padding:0.75rem;border-radius:6px;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);margin-bottom:0.5rem;">
                        <strong style="color:var(--success);">${result.imported || 0}</strong> students imported
                    </div>
                    ${result.errors?.length ? `
                        <div style="padding:0.75rem;border-radius:6px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);">
                            <strong style="color:#ef4444;">${result.errors.length}</strong> errors:
                            <ul style="margin:0.25rem 0 0;padding-left:1.2rem;font-size:0.8rem;color:var(--text-secondary);">
                                ${result.errors.slice(0, 5).map(e => `<li>${e}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                `;
                Toast.success(`${result.imported || 0} students imported`);
                this.loadStudentTab('enrolled');
            } catch (err) {
                Toast.error('Import failed: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-upload"></i> Import';
            }
        });
    }

    // ============ ATTENDANCE ============

    async loadAttendance(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="tabs">
                    <button class="tab-btn active" data-att-tab="present">Present</button>
                    <button class="tab-btn" data-att-tab="absent">Absent</button>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;">
                    <input type="text" id="attendance-search" placeholder="Search student name..." style="padding:0.5rem 1rem;border-radius:var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;outline:none;">
                    <input type="date" id="attendance-date" value="${new Date().toISOString().split('T')[0]}">
                    <button class="btn primary" id="filter-attendance"><i class="fa-solid fa-filter"></i> Filter</button>
                    <button class="btn secondary" id="mark-attendance-btn"><i class="fa-solid fa-user-check"></i> Mark Attendance</button>
                    <button class="btn secondary" id="export-attendance-csv"><i class="fa-solid fa-download"></i> Export CSV</button>
                </div>
            </div>
            <div class="card">
                <div id="attendance-content">
                    <div class="skeleton" style="height:50px;margin-bottom:0.5rem;"></div>
                    <div class="skeleton" style="height:50px;margin-bottom:0.5rem;"></div>
                    <div class="skeleton" style="height:50px;"></div>
                </div>
            </div>
        `;

        this._activeAttTab = 'present';

        container.querySelectorAll('[data-att-tab]').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('[data-att-tab]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this._activeAttTab = btn.dataset.attTab;
                this._activeAttTab === 'absent' ? this.loadAbsentStudents() : this.loadAttendanceData();
            });
        });

        document.getElementById('filter-attendance').addEventListener('click', () => {
            this._activeAttTab === 'absent' ? this.loadAbsentStudents() : this.loadAttendanceData();
        });

        document.getElementById('attendance-search').addEventListener('input', () => {
            clearTimeout(this._attendanceSearchTimeout);
            this._attendanceSearchTimeout = setTimeout(() => {
                this._activeAttTab === 'absent' ? this.loadAbsentStudents() : this.loadAttendanceData();
            }, 300);
        });

        document.getElementById('export-attendance-csv').addEventListener('click', () => this.exportAttendanceCSV());
        document.getElementById('mark-attendance-btn').addEventListener('click', () => this.showManualAttendanceModal());

        this._attendanceInterval = setInterval(() => {
            if (this._activeAttTab === 'present') this.loadAttendanceData();
        }, 30000);

        await this.loadAttendanceData();
    }

    async loadAttendanceData() {
        const container = document.getElementById('attendance-content');
        if (!container) return;
        const date = document.getElementById('attendance-date')?.value || new Date().toISOString().split('T')[0];
        const search = document.getElementById('attendance-search')?.value?.trim() || '';

        try {
            const params = { date };
            if (search) params.search = search;
            const data = await API.getAttendance(params);

            if (!data.records || data.records.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-calendar-xmark"></i><p>No attendance records' + (search ? ' matching "' + search + '"' : ' for this date') + '</p><p style="font-size:0.85rem;color:var(--text-muted);">Attendance is auto-marked when students are recognized via face detection.</p></div>';
                return;
            }

            container.innerHTML = `
                <div style="margin-bottom:1rem;padding:1rem;background:var(--success-bg);border-radius:var(--border-radius-sm);display:flex;align-items:center;gap:0.5rem;">
                    <i class="fa-solid fa-users" style="color:var(--success);"></i>
                    <span><strong>${data.records.length}</strong> students present on ${new Date(date).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata' })}</span>
                </div>
                <table class="data-table">
                    <thead><tr><th>#</th><th>Student</th><th>Roll No</th><th>Class</th><th>Check-in Time</th><th>Status</th></tr></thead>
                    <tbody>
                        ${data.records.map((r, i) => `
                        <tr>
                            <td style="color:var(--text-muted);">${i + 1}</td>
                            <td><div class="user-cell"><div class="avatar">${(r.student_name || '?')[0]}</div><span>${r.student_name || 'Unknown'}</span></div></td>
                            <td>${r.roll_no || '-'}</td>
                            <td>${r.class || '-'}</td>
                            <td>${new Date(r.timestamp).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true })}</td>
                            <td>${r.status === 'late' ? '<span class="badge" style="background:rgba(245,158,11,0.15);color:#f59e0b;"><i class="fa-solid fa-clock"></i> Late</span>' : '<span class="badge success">Present</span>'}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            container.innerHTML = `<div class="error-state">Failed: ${error.message}</div>`;
        }
    }

    async loadAbsentStudents() {
        const container = document.getElementById('attendance-content');
        if (!container) return;
        const date = document.getElementById('attendance-date')?.value || new Date().toISOString().split('T')[0];
        const search = (document.getElementById('attendance-search')?.value?.trim() || '').toLowerCase();

        try {
            const data = await API.request(`/api/attendance/absent?date=${date}`);
            let students = data.students || [];
            if (search) students = students.filter(s => (s.name || '').toLowerCase().includes(search) || (s.roll_no || '').toString().includes(search));

            if (students.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-face-smile"></i><p>All students are present!' + (search ? ' (for "' + search + '")' : '') + '</p></div>';
                return;
            }

            container.innerHTML = `
                <div style="margin-bottom:1rem;padding:1rem;background:rgba(239,68,68,0.1);border-radius:var(--border-radius-sm);display:flex;align-items:center;gap:0.5rem;">
                    <i class="fa-solid fa-user-slash" style="color:#ef4444;"></i>
                    <span><strong>${students.length}</strong> students absent on ${new Date(date).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata' })}</span>
                </div>
                <table class="data-table">
                    <thead><tr><th>#</th><th>Student</th><th>Roll No</th><th>Class</th><th>Action</th></tr></thead>
                    <tbody>
                        ${students.map((s, i) => `
                        <tr>
                            <td style="color:var(--text-muted);">${i + 1}</td>
                            <td><div class="user-cell"><div class="avatar" style="background:rgba(239,68,68,0.2);color:#ef4444;">${(s.name || '?')[0]}</div><span>${s.name || 'Unknown'}</span></div></td>
                            <td>${s.roll_no || '-'}</td>
                            <td>${s.class || '-'}</td>
                            <td><button class="btn primary" style="font-size:0.75rem;padding:0.3rem 0.6rem;" onclick="app.markManualAttendance(${s.id})"><i class="fa-solid fa-check"></i> Mark Present</button></td>
                        </tr>`).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            container.innerHTML = `<div class="error-state">Failed: ${error.message}</div>`;
        }
    }

    showManualAttendanceModal() {
        document.getElementById('manual-attendance-modal')?.remove();
        const modal = document.createElement('div');
        modal.className = 'modal show';
        modal.id = 'manual-attendance-modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:450px;">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-user-check" style="color:var(--primary);margin-right:0.5rem;"></i>Mark Attendance</h3>
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Search Student</label>
                        <input type="text" id="manual-att-search" placeholder="Type student name or roll no..." style="width:100%;">
                    </div>
                    <div id="manual-att-results" style="max-height:250px;overflow-y:auto;">
                        <div class="empty-state small"><p>Type to search for a student</p></div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        const si = document.getElementById('manual-att-search');
        si.focus();
        si.addEventListener('input', async () => {
            const q = si.value.trim();
            const rd = document.getElementById('manual-att-results');
            if (q.length < 2) { rd.innerHTML = '<div class="empty-state small"><p>Type at least 2 characters</p></div>'; return; }
            try {
                const data = await API.getStudents({ search: q });
                const ss = data.students || [];
                if (!ss.length) { rd.innerHTML = '<div class="empty-state small"><p>No students found</p></div>'; return; }
                rd.innerHTML = ss.map(s => `
                    <div style="display:flex;align-items:center;justify-content:space-between;padding:0.6rem;border-bottom:1px solid rgba(255,255,255,0.05);">
                        <div class="user-cell"><div class="avatar">${(s.name || '?')[0]}</div><div><div>${s.name}</div><div style="font-size:0.75rem;color:var(--text-muted);">Roll: ${s.roll_no || '-'} | ${s.class || '-'}</div></div></div>
                        <button class="btn primary" style="font-size:0.75rem;padding:0.3rem 0.6rem;" onclick="app.markManualAttendance(${s.id})"><i class="fa-solid fa-check"></i> Mark</button>
                    </div>`).join('');
            } catch (e) { rd.innerHTML = `<div class="error-state">Error: ${e.message}</div>`; }
        });
    }

    async markManualAttendance(studentId) {
        try {
            await API.request('/api/attendance/mark', { method: 'POST', body: JSON.stringify({ student_id: studentId }) });
            Toast.success('Attendance marked successfully!');
            document.getElementById('manual-attendance-modal')?.remove();
            this._activeAttTab === 'absent' ? this.loadAbsentStudents() : this.loadAttendanceData();
        } catch (e) {
            Toast.error(e.message || 'Failed to mark attendance');
        }
    }

    exportAttendanceCSV() {
        const date = document.getElementById('attendance-date')?.value || new Date().toISOString().split('T')[0];
        const table = document.querySelector('#attendance-content table');
        if (!table) {
            Toast.warning('No attendance records to export');
            return;
        }

        // Use server-side CSV export
        const token = localStorage.getItem('jwt_token');
        fetch(`/ api / attendance /export?date = ${date} `, {
            headers: { 'Authorization': `Bearer ${token} ` }
        })
            .then(res => res.blob())
            .then(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `attendance_${date}.csv`;
                a.click();
                URL.revokeObjectURL(url);
                Toast.success('Attendance exported to CSV');
            })
            .catch(err => {
                Toast.error('Export failed: ' + err.message);
            });
    }

    async viewStudent(id) {
        try {
            const data = await API.request(`/api/students/${id}`);
            const student = data.student;

            // Fetch face photos and attendance history in parallel
            let faces = [], history = [];
            try {
                const [facesData, histData] = await Promise.all([
                    API.request(`/api/students/${id}/faces`),
                    API.request(`/api/students/${id}/attendance-history`),
                ]);
                faces = facesData.faces || [];
                history = histData.history || [];
            } catch (e) { console.warn('Partial data fetch failed:', e); }

            // Remove old modal
            document.getElementById('student-detail-modal')?.remove();

            const modal = document.createElement('div');
            modal.id = 'student-detail-modal';
            modal.className = 'modal show';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:680px;max-height:90vh;overflow-y:auto;">
                    <div class="modal-header">
                        <h3><i class="fa-solid fa-user" style="margin-right:0.5rem;"></i>Student Details</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <!-- Profile Header -->
                        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1.25rem;">
                            <div class="avatar" style="width:60px;height:60px;font-size:1.5rem;">${student.name[0]}</div>
                            <div>
                                <h4 style="margin:0;">${student.name}</h4>
                                <p style="margin:0;color:var(--text-secondary);">
                                    Roll: <span class="monospace">${student.roll_no}</span>
                                    ${student.class ? ` · ${student.class}` : ''}
                                </p>
                                <span class="badge ${student.has_face_encoding ? 'success' : ''}" style="margin-top:0.3rem;display:inline-block;font-size:0.7rem;${student.has_face_encoding ? '' : 'background:rgba(239,68,68,0.15);color:#ef4444;'}">
                                    ${student.has_face_encoding ? '<i class="fa-solid fa-shield-check"></i> Face Enrolled' : '<i class="fa-solid fa-camera-slash"></i> Not Enrolled'}
                                </span>
                            </div>
                        </div>

                        <!-- Face Photos Section -->
                        <div style="margin-bottom:1.25rem;">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                                <h4 style="margin:0;font-size:0.9rem;"><i class="fa-solid fa-camera" style="margin-right:0.4rem;color:var(--primary);"></i>Face Photos (${faces.length})</h4>
                                <div style="display:flex;gap:0.4rem;">
                                    <button class="btn small" id="upload-face-btn" style="font-size:0.75rem;">
                                        <i class="fa-solid fa-upload"></i> Upload
                                    </button>
                                    <button class="btn small" id="recompute-btn" style="font-size:0.75rem;">
                                        <i class="fa-solid fa-sync"></i> Recompute
                                    </button>
                                </div>
                            </div>
                            <div id="face-photos-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:0.5rem;">
                                ${faces.length > 0 ? faces.map(f => `
                                    <div style="position:relative;aspect-ratio:1;background:var(--bg-tertiary);border-radius:6px;overflow:hidden;border:2px solid rgba(34,197,94,0.3);">
                                        <img src="${f.photo_path}" style="width:100%;height:100%;object-fit:cover;">
                                        <button class="face-del-btn" data-face-id="${f.id}" style="position:absolute;top:2px;right:2px;background:rgba(239,68,68,0.8);color:#fff;border:none;border-radius:50%;width:20px;height:20px;cursor:pointer;font-size:10px;line-height:20px;text-align:center;">&times;</button>
                                    </div>
                                `).join('') : '<div style="grid-column:1/-1;text-align:center;padding:1rem;color:var(--text-secondary);font-size:0.85rem;"><i class="fa-solid fa-image" style="font-size:1.5rem;margin-bottom:0.5rem;display:block;opacity:0.4;"></i>No photos enrolled yet</div>'}
                            </div>
                            <input type="file" id="face-file-input" accept="image/*" style="display:none;" multiple>
                        </div>

                        <!-- Attendance History -->
                        <div>
                            <h4 style="margin:0 0 0.5rem;font-size:0.9rem;"><i class="fa-solid fa-calendar-check" style="margin-right:0.4rem;color:var(--success);"></i>Recent Attendance (${history.length})</h4>
                            ${history.length > 0 ? `
                                <div style="max-height:150px;overflow-y:auto;">
                                    ${history.slice(0, 10).map(h => `
                                        <div style="display:flex;justify-content:space-between;padding:0.3rem 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.8rem;">
                                            <span>${new Date(h.timestamp).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata' })} ${new Date(h.timestamp).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true })}</span>
                                            <span class="badge success" style="font-size:0.65rem;">${h.source || 'auto'}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : '<p style="color:var(--text-secondary);font-size:0.8rem;">No attendance records yet</p>'}
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Close handlers
            modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

            // Upload face photo
            const fileInput = modal.querySelector('#face-file-input');
            modal.querySelector('#upload-face-btn').addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', async (e) => {
                const files = Array.from(e.target.files);
                if (!files.length) return;
                for (const file of files) {
                    const reader = new FileReader();
                    reader.onload = async (ev) => {
                        try {
                            await API.request(`/api/students/${id}/faces`, {
                                method: 'POST',
                                body: JSON.stringify({ photo: ev.target.result })
                            });
                            Toast.success('Photo uploaded');
                        } catch (err) {
                            Toast.error('Upload failed: ' + err.message);
                        }
                    };
                    reader.readAsDataURL(file);
                }
                // Refresh after small delay for all uploads to complete
                setTimeout(() => this.viewStudent(id), 1500);
            });

            // Delete face photos
            modal.querySelectorAll('.face-del-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const faceId = btn.dataset.faceId;
                    if (!confirm('Delete this face photo?')) return;
                    try {
                        await API.request(`/api/students/${id}/faces/${faceId}`, { method: 'DELETE' });
                        Toast.success('Photo deleted');
                        this.viewStudent(id); // Refresh
                    } catch (err) {
                        Toast.error('Delete failed: ' + err.message);
                    }
                });
            });

            // Recompute encoding
            modal.querySelector('#recompute-btn').addEventListener('click', async () => {
                const btn = modal.querySelector('#recompute-btn');
                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Computing...';
                try {
                    await API.request(`/api/students/${id}/recompute-encoding`, { method: 'POST' });
                    Toast.success('Face encoding recomputed!');
                    this.viewStudent(id);
                } catch (err) {
                    Toast.error('Recompute failed: ' + err.message);
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa-solid fa-sync"></i> Recompute';
                }
            });

        } catch (error) {
            Toast.error('Failed to load student details: ' + error.message);
        }
    }

    async editStudent(id) {
        try {
            const data = await API.request(`/ api / students / ${id} `);
            const student = data.student;

            // Show edit modal
            const modal = document.createElement('div');
            modal.className = 'modal show';
            modal.id = 'edit-student-modal';
            modal.innerHTML = `
    <div class="modal-content">
                    <div class="modal-header">
                        <h3>Edit Student</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label>Name</label>
                            <input type="text" id="edit-name" value="${student.name}">
                        </div>
                        <div class="form-group">
                            <label>Roll Number</label>
                            <input type="text" id="edit-roll" value="${student.roll_no}">
                        </div>
                        <div class="form-group">
                            <label>Class</label>
                            <input type="text" id="edit-class" value="${student.class || ''}">
                        </div>
                        <div class="form-group">
                            <label>Contact</label>
                            <input type="text" id="edit-contact" value="${student.contact_no || ''}">
                        </div>
                        <button class="btn primary full-width" id="save-student-btn">
                            <i class="fa-solid fa-save"></i> Save Changes
                        </button>
                    </div>
                </div>
    `;
            document.body.appendChild(modal);

            modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

            modal.querySelector('#save-student-btn').addEventListener('click', async () => {
                const updated = {
                    name: document.getElementById('edit-name').value,
                    roll_no: document.getElementById('edit-roll').value,
                    class: document.getElementById('edit-class').value,
                    contact_no: document.getElementById('edit-contact').value
                };
                try {
                    await API.request(`/ api / students / ${id} `, {
                        method: 'PUT',
                        body: JSON.stringify(updated)
                    });
                    Toast.success('Student updated');
                    modal.remove();
                    this.loadStudentTab('enrolled');
                } catch (error) {
                    Toast.error('Failed to update: ' + error.message);
                }
            });
        } catch (error) {
            Toast.error('Failed to load student');
        }
    }

    // ============ ALERTS ============

    async loadAlerts(container) {
        this._alertsPage = 1;
        container.innerHTML = `
            <div class="page-header">
                <div class="filter-group" style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center;">
                    <select id="alert-type-filter" style="padding:0.45rem;border-radius:var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;">
                        <option value="">All Types</option>
                        <option value="falling">Falling</option>
                        <option value="running">Running</option>
                        <option value="fighting">Fighting</option>
                        <option value="loitering">Loitering</option>
                    </select>
                    <select id="alert-severity-filter" style="padding:0.45rem;border-radius:var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;">
                        <option value="">All Severity</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <select id="alert-status-filter" style="padding:0.45rem;border-radius:var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;">
                        <option value="">All Status</option>
                        <option value="unresolved" selected>Unresolved</option>
                        <option value="resolved">Resolved</option>
                        <option value="false_alarm">False Alarm</option>
                    </select>
                    <input type="date" id="alert-date-filter" style="padding:0.45rem;border-radius:var(--border-radius-sm);border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;">
                    <button class="btn primary" id="filter-alerts">
                        <i class="fa-solid fa-filter"></i> Filter
                    </button>
                </div>
                <div class="btn-group" style="display:flex;gap:0.4rem;">
                    <button class="btn secondary" id="refresh-alerts">
                        <i class="fa-solid fa-refresh"></i> Refresh
                    </button>
                    <button class="btn danger" id="clear-all-alerts">
                        <i class="fa-solid fa-trash"></i> Clear All
                    </button>
                </div>
            </div>

            <div class="card">
                <div id="alerts-content">
                    <div class="skeleton" style="height: 80px; margin-bottom: 0.75rem;"></div>
                    <div class="skeleton" style="height: 80px; margin-bottom: 0.75rem;"></div>
                    <div class="skeleton" style="height: 80px;"></div>
                </div>
                <div id="alerts-pagination" style="display:flex;justify-content:center;align-items:center;gap:0.75rem;margin-top:1rem;"></div>
            </div>
        `;

        document.getElementById('filter-alerts').addEventListener('click', () => {
            this._alertsPage = 1;
            this.loadAlertsData();
        });

        document.getElementById('refresh-alerts').addEventListener('click', () => {
            this.loadAlertsData();
            Toast.info('Alerts refreshed');
        });

        document.getElementById('clear-all-alerts').addEventListener('click', () => {
            this.clearAllAlerts();
        });

        await this.loadAlertsData();
    }

    async loadAlertsData() {
        const container = document.getElementById('alerts-content');
        const type = document.getElementById('alert-type-filter')?.value || '';
        const severity = document.getElementById('alert-severity-filter')?.value || '';
        const status = document.getElementById('alert-status-filter')?.value || '';
        const date = document.getElementById('alert-date-filter')?.value || '';

        try {
            const params = new URLSearchParams();
            if (type) params.set('event_type', type);
            if (severity) params.set('severity', severity);
            if (status) params.set('status', status);
            if (date) params.set('date', date);
            params.set('page', this._alertsPage || 1);
            params.set('per_page', 10);

            const data = await API.request(`/api/alerts?${params.toString()}`);
            const alerts = data.alerts || [];
            const total = data.total || 0;
            const totalPages = Math.ceil(total / 10) || 1;

            if (alerts.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-check-circle"></i><p>No alerts found</p></div>';
                document.getElementById('alerts-pagination').innerHTML = '';
                return;
            }

            container.innerHTML = `
                <div class="alerts-list">
                    ${alerts.map(alert => {
                const statusLabel = alert.status === 'resolved' ? 'Resolved' : alert.status === 'false_alarm' ? 'False Alarm' : 'Unresolved';
                const statusClass = alert.status === 'resolved' ? 'success' : alert.status === 'false_alarm' ? '' : 'warning';
                const statusStyle = alert.status === 'false_alarm' ? 'background:rgba(148,163,184,0.15);color:#94a3b8;' : '';
                return `
                        <div class="alert-card ${alert.severity}" id="alert-${alert.id}" style="cursor:pointer;" onclick="app.viewAlertDetail(${alert.id})">
                            ${alert.snapshot_path ? `
                                <div style="width:70px;height:70px;border-radius:6px;overflow:hidden;flex-shrink:0;border:2px solid rgba(255,255,255,0.1);">
                                    <img src="${alert.snapshot_path}" style="width:100%;height:100%;object-fit:cover;">
                                </div>
                            ` : ''}
                            <div class="alert-icon">
                                <i class="fa-solid fa-${this.getAlertIcon(alert.event_type)}"></i>
                            </div>
                            <div class="alert-content">
                                <div class="alert-title">${this.formatEventType(alert.event_type)}</div>
                                <div class="alert-meta">
                                    <span><i class="fa-solid fa-clock"></i> ${this.timeAgo(alert.timestamp)}</span>
                                    <span><i class="fa-solid fa-video"></i> Camera ${alert.camera_id}</span>
                                    <span class="badge ${statusClass}" style="font-size:0.65rem;${statusStyle}">${statusLabel}</span>
                                </div>
                            </div>
                            <div class="alert-actions" onclick="event.stopPropagation();">
                                <span class="badge ${alert.severity}">${alert.severity}</span>
                                ${alert.status !== 'resolved' && alert.status !== 'false_alarm' ? `
                                    <button class="btn small success" onclick="app.resolveAlert(${alert.id})" title="Resolve"><i class="fa-solid fa-check"></i></button>
                                    <button class="btn small" onclick="app.markFalseAlarm(${alert.id})" title="False Alarm" style="background:rgba(148,163,184,0.15);color:#94a3b8;border:1px solid rgba(148,163,184,0.3);"><i class="fa-solid fa-ban"></i></button>
                                ` : ''}
                                <button class="btn small danger" onclick="app.deleteAlert(${alert.id})" title="Delete"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </div>
                    `}).join('')}
                </div>
            `;

            // Pagination
            const pagEl = document.getElementById('alerts-pagination');
            if (totalPages > 1) {
                pagEl.innerHTML = `
                    <button class="btn small" ${this._alertsPage <= 1 ? 'disabled' : ''} onclick="app._alertsPage--;app.loadAlertsData();">
                        <i class="fa-solid fa-chevron-left"></i>
                    </button>
                    <span style="color:var(--text-secondary);font-size:0.85rem;">Page ${this._alertsPage} of ${totalPages} (${total} total)</span>
                    <button class="btn small" ${this._alertsPage >= totalPages ? 'disabled' : ''} onclick="app._alertsPage++;app.loadAlertsData();">
                        <i class="fa-solid fa-chevron-right"></i>
                    </button>
                `;
            } else {
                pagEl.innerHTML = `<span style="color:var(--text-secondary);font-size:0.8rem;">${total} alert${total !== 1 ? 's' : ''}</span>`;
            }

        } catch (error) {
            container.innerHTML = `<div class="error-state">Failed: ${error.message}</div>`;
        }
    }

    async viewAlertDetail(id) {
        try {
            const data = await API.request(`/api/alerts/${id}`);
            const alert = data.alert || data;

            document.getElementById('alert-detail-modal')?.remove();
            const modal = document.createElement('div');
            modal.id = 'alert-detail-modal';
            modal.className = 'modal show';

            const statusLabel = alert.status === 'resolved' ? 'Resolved' : alert.status === 'false_alarm' ? 'False Alarm' : 'Unresolved';
            let metadata = {};
            try { metadata = typeof alert.metadata === 'string' ? JSON.parse(alert.metadata) : (alert.metadata || {}); } catch (e) { }

            modal.innerHTML = `
                <div class="modal-content" style="max-width:600px;">
                    <div class="modal-header">
                        <h3><i class="fa-solid fa-${this.getAlertIcon(alert.event_type)}" style="margin-right:0.5rem;"></i>${this.formatEventType(alert.event_type)}</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        ${alert.snapshot_path ? `
                            <div style="margin-bottom:1rem;border-radius:8px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);">
                                <img src="${alert.snapshot_path}" style="width:100%;display:block;">
                            </div>
                        ` : ''}

                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem;">
                            <div style="background:var(--bg-tertiary);padding:0.6rem;border-radius:6px;">
                                <div style="font-size:0.7rem;color:var(--text-secondary);text-transform:uppercase;">Severity</div>
                                <span class="badge ${alert.severity}" style="margin-top:0.2rem;">${alert.severity}</span>
                            </div>
                            <div style="background:var(--bg-tertiary);padding:0.6rem;border-radius:6px;">
                                <div style="font-size:0.7rem;color:var(--text-secondary);text-transform:uppercase;">Status</div>
                                <div style="margin-top:0.2rem;font-weight:600;">${statusLabel}</div>
                            </div>
                            <div style="background:var(--bg-tertiary);padding:0.6rem;border-radius:6px;">
                                <div style="font-size:0.7rem;color:var(--text-secondary);text-transform:uppercase;">Camera</div>
                                <div style="margin-top:0.2rem;">Camera ${alert.camera_id}</div>
                            </div>
                            <div style="background:var(--bg-tertiary);padding:0.6rem;border-radius:6px;">
                                <div style="font-size:0.7rem;color:var(--text-secondary);text-transform:uppercase;">Time</div>
                                <div style="margin-top:0.2rem;">${new Date(alert.timestamp).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true })}</div>
                            </div>
                        </div>

                        ${metadata.description ? `<p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:1rem;">${metadata.description}</p>` : ''}
                        ${metadata.confidence ? `<div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:1rem;">Confidence: <strong>${(metadata.confidence * 100).toFixed(0)}%</strong></div>` : ''}

                        <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
                            ${alert.status !== 'resolved' && alert.status !== 'false_alarm' ? `
                                <button class="btn secondary" id="detail-false-alarm" style="background:rgba(148,163,184,0.15);color:#94a3b8;border:1px solid rgba(148,163,184,0.3);">
                                    <i class="fa-solid fa-ban"></i> False Alarm
                                </button>
                                <button class="btn success" id="detail-resolve">
                                    <i class="fa-solid fa-check"></i> Resolve
                                </button>
                            ` : `<span style="color:var(--text-secondary);font-size:0.85rem;">Alert already ${statusLabel.toLowerCase()}</span>`}
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });

            modal.querySelector('#detail-resolve')?.addEventListener('click', async () => {
                await this.resolveAlert(id);
                modal.remove();
            });
            modal.querySelector('#detail-false-alarm')?.addEventListener('click', async () => {
                await this.markFalseAlarm(id);
                modal.remove();
            });

        } catch (error) {
            Toast.error('Failed to load alert: ' + error.message);
        }
    }

    async resolveAlert(id) {
        try {
            await API.request(`/api/alerts/${id}/resolve`, { method: 'PUT' });
            Toast.success('Alert resolved');
            this.loadAlertsData();
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    async markFalseAlarm(id) {
        try {
            await API.request(`/api/alerts/${id}/false-alarm`, { method: 'PUT' });
            Toast.info('Marked as false alarm');
            this.loadAlertsData();
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    // Keep legacy dismissAlert as alias
    async dismissAlert(id) { return this.resolveAlert(id); }

    async deleteAlert(id) {
        if (!confirm('Delete this alert? This cannot be undone.')) return;
        try {
            await API.request(`/api/alerts/${id}`, { method: 'DELETE' });
            Toast.success('Alert deleted');
            const alertCard = document.getElementById(`alert-${id}`);
            if (alertCard) alertCard.remove();
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    async clearAllAlerts() {
        if (!confirm('Clear ALL alerts? This cannot be undone.')) return;
        try {
            Toast.info('Clearing alerts...');
            await API.request('/api/alerts/clear', { method: 'DELETE' });
            Toast.success('All alerts cleared');
            this.loadAlertsData();
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    playClip(alertId) {
        Toast.info('Video clip playback coming soon');
    }

    // ============ DETECTION TEST ============

    async loadDetectionTest(container) {
        this._detTestVideoUrl = null;
        this._detTestFileId = null;
        this._detTestAlerts = [];
        this._detAudioCtx = null;

        container.innerHTML = `
            <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
                <div>
                    <h2 style="margin:0;"><i class="fa-solid fa-flask" style="color:var(--primary);margin-right:0.5rem;"></i> Activity Detection Lab</h2>
                    <p style="color:var(--text-secondary);margin:0.25rem 0 0;font-size:0.85rem;">Upload a video clip to automatically detect and classify activities with AI</p>
                </div>
                <div style="display:flex;gap:0.5rem;">
                    <button class="btn" id="det-batch-btn" title="Run batch test on clips" style="font-size:0.8rem;">
                        <i class="fa-solid fa-vials"></i> Batch Test
                    </button>
                    <button class="btn" id="det-history-btn" title="Previously tested videos">
                        <i class="fa-solid fa-clock-rotate-left"></i> History
                    </button>
                </div>
            </div>

            <!-- Main grid: left=video+controls, right=alerts sidebar -->
            <div style="display:grid;grid-template-columns:1fr 320px;gap:1rem;align-items:start;" id="det-main-grid">

                <!-- LEFT COLUMN -->
                <div id="det-left-col">

                    <!-- Upload Card -->
                    <div class="card" id="det-upload-card">
                        <div style="display:grid;grid-template-columns:1fr 220px;gap:1rem;align-items:stretch;" id="det-upload-grid">
                            <!-- Drop Zone -->
                            <div id="det-drop-zone" style="border:2px dashed rgba(255,255,255,0.12);border-radius:10px;padding:2rem 1.5rem;text-align:center;cursor:pointer;transition:all 0.25s ease;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                                <i class="fa-solid fa-cloud-arrow-up" style="font-size:2.5rem;color:var(--primary);margin-bottom:0.75rem;"></i>
                                <h3 style="margin:0 0 0.35rem;font-size:1rem;">Drop Video File Here</h3>
                                <p style="color:var(--text-secondary);margin:0 0 0.75rem;font-size:0.8rem;">MP4, AVI, MOV, MKV, WebM, MPG (max 100MB)</p>
                                <button class="btn primary" id="det-browse-btn" style="font-size:0.85rem;">
                                    <i class="fa-solid fa-folder-open"></i> Browse Files
                                </button>
                                <input type="file" id="det-video-input" accept=".mp4,.avi,.mov,.mkv,.webm,.mpg,.mpeg" style="display:none;">
                            </div>

                            <!-- Config Panel -->
                            <div style="display:flex;flex-direction:column;gap:0.75rem;padding:0.5rem 0;justify-content:center;">
                                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-secondary);font-weight:600;">
                                    <i class="fa-solid fa-sliders"></i> Detection Settings
                                </div>
                                <div>
                                    <label style="font-size:0.8rem;display:flex;justify-content:space-between;">
                                        Sample FPS <span id="det-fps-val" style="color:var(--primary);font-weight:600;">10</span>
                                    </label>
                                    <input type="range" id="det-fps-slider" min="1" max="15" value="10" step="1"
                                        style="width:100%;accent-color:var(--primary);">
                                    <p style="font-size:0.68rem;color:var(--text-secondary);margin:0.2rem 0 0;">Higher = more accurate, slower</p>
                                </div>
                                <div style="display:flex;justify-content:space-between;align-items:center;padding:0.4rem 0;border-top:1px solid rgba(255,255,255,0.05);">
                                    <div>
                                        <label style="font-size:0.78rem;margin:0;">Alert Sound</label>
                                    </div>
                                    <label style="position:relative;display:inline-block;width:36px;height:20px;">
                                        <input type="checkbox" id="det-sound-toggle" checked style="opacity:0;width:0;height:0;">
                                        <span style="position:absolute;cursor:pointer;inset:0;background:var(--primary);border-radius:20px;transition:0.3s;"></span>
                                    </label>
                                </div>
                                <div style="padding:0.5rem;background:rgba(99,102,241,0.08);border-radius:8px;border:1px solid rgba(99,102,241,0.15);margin-top:0.2rem;">
                                    <div style="font-size:0.72rem;color:var(--primary);font-weight:600;margin-bottom:0.2rem;"><i class="fa-solid fa-robot"></i> Auto Detection</div>
                                    <p style="font-size:0.68rem;color:var(--text-secondary);margin:0;">YOLOv8-Pose + LSTM classifier will automatically detect Fighting, Running, Falling, Loitering &amp; more</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Processing Indicator -->
                    <div class="card" id="det-processing-card" style="display:none;">
                        <div style="display:flex;align-items:center;gap:0.75rem;">
                            <i class="fa-solid fa-spinner fa-spin" style="font-size:1.3rem;color:var(--primary);"></i>
                            <div style="flex:1;">
                                <h3 style="margin:0;font-size:1rem;" id="det-proc-title">Processing Video...</h3>
                                <p id="det-proc-status" style="color:var(--text-secondary);font-size:0.8rem;margin:0.15rem 0 0;">Uploading...</p>
                            </div>
                        </div>
                        <div style="margin-top:0.75rem;background:rgba(255,255,255,0.05);border-radius:8px;height:6px;overflow:hidden;">
                            <div id="det-proc-bar" style="height:100%;background:var(--primary);border-radius:8px;transition:width 0.4s ease;width:0%;"></div>
                        </div>
                    </div>

                    <!-- Batch Results -->
                    <div id="det-batch-results" style="display:none;"></div>

                    <!-- Results Area -->
                    <div id="det-results-area" style="display:none;"></div>
                </div>

                <!-- RIGHT COLUMN: Alert Feed Sidebar -->
                <div class="card" style="position:sticky;top:1rem;max-height:calc(100vh - 120px);overflow:hidden;display:flex;flex-direction:column;" id="det-sidebar">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
                        <h3 style="margin:0;font-size:0.95rem;">
                            <i class="fa-solid fa-bell" style="color:#f59e0b;margin-right:0.4rem;"></i> Alert Feed
                        </h3>
                        <span id="det-alert-count" style="font-size:0.75rem;background:rgba(239,68,68,0.15);color:#ef4444;padding:0.15rem 0.5rem;border-radius:10px;">0</span>
                    </div>
                    <div id="det-alert-feed" style="flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:0.4rem;">
                        <div style="text-align:center;padding:2rem 0.5rem;color:var(--text-secondary);font-size:0.8rem;">
                            <i class="fa-solid fa-shield-halved" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;opacity:0.4;"></i>
                            Alerts from detection will appear here as the video is analyzed
                        </div>
                    </div>
                    <div style="border-top:1px solid rgba(255,255,255,0.05);padding-top:0.5rem;margin-top:0.5rem;">
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.75rem;">
                            <div style="text-align:center;padding:0.3rem;background:rgba(255,255,255,0.03);border-radius:6px;">
                                <div style="color:var(--text-secondary);">Persons</div>
                                <div id="det-stat-persons" style="font-weight:700;font-size:1rem;">—</div>
                            </div>
                            <div style="text-align:center;padding:0.3rem;background:rgba(255,255,255,0.03);border-radius:6px;">
                                <div style="color:var(--text-secondary);">Status</div>
                                <div id="det-stat-status" style="font-weight:700;font-size:1rem;">—</div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            <!-- History Modal -->
            <div id="det-history-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:100;align-items:center;justify-content:center;">
                <div class="card" style="width:500px;max-width:90vw;max-height:70vh;overflow-y:auto;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                        <h3 style="margin:0;"><i class="fa-solid fa-clock-rotate-left" style="color:var(--primary);margin-right:0.4rem;"></i> Test History</h3>
                        <button class="btn" id="det-history-close" style="font-size:0.8rem;">✕</button>
                    </div>
                    <div id="det-history-list">Loading...</div>
                </div>
            </div>
        `;

        this._detSetupEventListeners();
    }

    _detSetupEventListeners() {
        const fileInput = document.getElementById('det-video-input');
        const dropZone = document.getElementById('det-drop-zone');
        const browseBtn = document.getElementById('det-browse-btn');
        const fpsSlider = document.getElementById('det-fps-slider');
        const fpsVal = document.getElementById('det-fps-val');

        // Browse / Drop
        browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) this._detProcessVideo(e.target.files[0]);
        });

        // Drag & drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--primary)';
            dropZone.style.background = 'rgba(99,102,241,0.06)';
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = 'rgba(255,255,255,0.12)';
            dropZone.style.background = '';
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'rgba(255,255,255,0.12)';
            dropZone.style.background = '';
            if (e.dataTransfer.files.length > 0) this._detProcessVideo(e.dataTransfer.files[0]);
        });

        // FPS slider
        fpsSlider.addEventListener('input', () => { fpsVal.textContent = fpsSlider.value; });

        // Alert sound toggle styling
        const soundCb = document.getElementById('det-sound-toggle');
        if (soundCb) {
            const span = soundCb.nextElementSibling;
            soundCb.addEventListener('change', () => {
                if (span) span.style.background = soundCb.checked ? 'var(--primary)' : 'rgba(255,255,255,0.15)';
            });
        }


        // History & batch buttons
        document.getElementById('det-history-btn')?.addEventListener('click', () => this._detShowHistory());
        document.getElementById('det-history-close')?.addEventListener('click', () => {
            document.getElementById('det-history-modal').style.display = 'none';
        });
        document.getElementById('det-batch-btn')?.addEventListener('click', () => this._detRunBatchTest());
    }

    async _detProcessVideo(file) {
        const allowed = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'mpg', 'mpeg'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowed.includes(ext)) { Toast.error(`Unsupported format: .${ext}`); return; }
        if (file.size > 100 * 1024 * 1024) { Toast.error('File too large (max 100MB)'); return; }

        const sampleFps = document.getElementById('det-fps-slider')?.value || 10;

        // Switch UI
        document.getElementById('det-upload-card').style.display = 'none';
        const procCard = document.getElementById('det-processing-card');
        procCard.style.display = '';
        const bar = document.getElementById('det-proc-bar');
        const status = document.getElementById('det-proc-status');
        const title = document.getElementById('det-proc-title');
        document.getElementById('det-results-area').style.display = 'none';

        this._detTestAlerts = [];
        this._detUpdateAlertFeed();

        const sizeMB = (file.size / 1024 / 1024).toFixed(1);
        title.textContent = `Processing: ${file.name}`;
        status.textContent = `Uploading ${sizeMB} MB...`;
        bar.style.width = '5%';

        const formData = new FormData();
        formData.append('video', file);
        formData.append('sample_fps', sampleFps);

        try {
            let progress = 5;
            const interval = setInterval(() => {
                if (progress < 90) {
                    progress += Math.random() * 2.5;
                    bar.style.width = Math.min(progress, 90) + '%';
                }
                if (progress > 15 && progress < 40) status.textContent = 'Running pose detection on frames...';
                if (progress > 40 && progress < 65) status.textContent = 'Classifying activities...';
                if (progress > 65) status.textContent = 'Building timeline...';
            }, 600);

            const token = localStorage.getItem('jwt_token');
            const response = await fetch('/api/detection/test-video', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });

            clearInterval(interval);

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || `Server error (${response.status})`);
            }

            bar.style.width = '100%';
            status.textContent = 'Complete!';

            const data = await response.json();
            const fn = data.video_info?.filename || '';
            this._detTestFileId = fn.replace('test_', '').split('.')[0];
            this._detTestVideoUrl = data.video_url;

            // Populate alert feed
            this._detTestAlerts = (data.timeline || []).map((t, i) => ({
                id: i + 1, type: t.activity, severity: t.severity,
                time: t.start_time, description: t.description,
                confidence: t.confidence, persons: t.person_count, abnormal: t.is_abnormal,
            }));
            this._detUpdateAlertFeed();

            // Play alert beep if abnormal detected
            const summ = data.summary || {};
            if (summ.status === 'abnormal_detected') {
                this._detPlayAlertBeep();
            }

            // Sidebar stats
            document.getElementById('det-stat-persons').textContent = summ.max_persons_detected ?? 0;
            const statusEl = document.getElementById('det-stat-status');
            if (summ.status === 'abnormal_detected') {
                statusEl.textContent = '⚠ Alert';
                statusEl.style.color = '#ef4444';
            } else {
                statusEl.textContent = '✓ Clear';
                statusEl.style.color = 'var(--success)';
            }

            setTimeout(() => this._detShowResults(data, file.name), 300);

        } catch (error) {
            Toast.error('Detection failed: ' + error.message);
            document.getElementById('det-upload-card').style.display = '';
            procCard.style.display = 'none';
        }
    }

    _detUpdateAlertFeed() {
        const feed = document.getElementById('det-alert-feed');
        const count = document.getElementById('det-alert-count');
        if (!feed) return;

        count.textContent = this._detTestAlerts.length;

        if (this._detTestAlerts.length === 0) {
            feed.innerHTML = `
                <div style="text-align:center;padding:2rem 0.5rem;color:var(--text-secondary);font-size:0.8rem;">
                    <i class="fa-solid fa-shield-halved" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;opacity:0.4;"></i>
                    Alerts from detection will appear here
                </div>`;
            return;
        }

        const sevColors = { high: '#ef4444', medium: '#f59e0b', low: '#3b82f6' };
        feed.innerHTML = this._detTestAlerts.map(a => `
            <div class="det-alert-item" data-time="${a.time}" style="padding:0.5rem 0.6rem;border-radius:8px;background:rgba(255,255,255,0.02);border-left:3px solid ${sevColors[a.severity] || '#3b82f6'};cursor:pointer;transition:background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:600;font-size:0.8rem;text-transform:capitalize;">${a.type}</span>
                    <span style="font-size:0.65rem;font-family:monospace;color:var(--text-secondary);">${this._fmtTime(a.time)}</span>
                </div>
                <div style="font-size:0.72rem;color:var(--text-secondary);margin-top:0.15rem;">
                    ${a.confidence ? (a.confidence * 100).toFixed(0) + '% conf' : ''} • ${a.persons} person${a.persons !== 1 ? 's' : ''}
                </div>
                ${a.description ? `<div style="font-size:0.7rem;color:var(--text-secondary);margin-top:0.1rem;opacity:0.8;">${a.description}</div>` : ''}
            </div>
        `).join('');

        // Click to seek video
        feed.querySelectorAll('.det-alert-item').forEach(item => {
            item.addEventListener('click', () => {
                const t = parseFloat(item.dataset.time);
                const video = document.getElementById('det-video-player');
                if (video && !isNaN(t)) { video.currentTime = t; video.play(); }
            });
        });
    }

    _detShowResults(data, filename) {
        document.getElementById('det-processing-card').style.display = 'none';
        const area = document.getElementById('det-results-area');
        area.style.display = '';

        const vi = data.video_info || {};
        const proc = data.processing || {};
        const summary = data.summary || {};
        const timeline = data.timeline || [];
        const frameResults = data.frame_results || [];
        const videoUrl = data.video_url;
        const sevColors = { high: '#ef4444', medium: '#f59e0b', low: '#3b82f6' };

        area.innerHTML = `
            <!-- Action Bar -->
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;flex-wrap:wrap;gap:0.5rem;">
                <div style="display:flex;gap:0.5rem;align-items:center;">
                    <span style="font-size:0.9rem;font-weight:600;">
                        <i class="fa-solid fa-circle-check" style="color:var(--success);margin-right:0.3rem;"></i> Analysis Complete
                    </span>
                    <span style="font-size:0.75rem;color:var(--text-secondary);">— ${filename}</span>
                </div>
                <div style="display:flex;gap:0.4rem;">
                    <button class="btn" id="det-new-test-btn" style="font-size:0.8rem;">
                        <i class="fa-solid fa-plus"></i> New Test
                    </button>
                    ${this._detTestFileId ? `<button class="btn" id="det-cleanup-btn" style="font-size:0.8rem;color:#ef4444;">
                        <i class="fa-solid fa-trash-can"></i> Delete Video
                    </button>` : ''}
                </div>
            </div>

            <!-- Stats Grid -->
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:0.5rem;margin-bottom:0.75rem;">
                <div class="card" style="padding:0.6rem 0.8rem;">
                    <div style="font-size:0.65rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">Duration</div>
                    <div style="font-size:1.1rem;font-weight:700;margin-top:0.1rem;font-family:monospace;">${vi.duration_str}</div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">${vi.resolution} • ${vi.fps} FPS</div>
                </div>
                <div class="card" style="padding:0.6rem 0.8rem;">
                    <div style="font-size:0.65rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">Frames</div>
                    <div style="font-size:1.1rem;font-weight:700;margin-top:0.1rem;">${proc.frames_processed}</div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">${proc.processing_time_sec}s @ ${proc.fps_achieved} FPS</div>
                </div>
                <div class="card" style="padding:0.6rem 0.8rem;">
                    <div style="font-size:0.65rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">Detections</div>
                    <div style="font-size:1.1rem;font-weight:700;margin-top:0.1rem;color:${summary.abnormal_detections > 0 ? '#ef4444' : 'var(--success)'};">${summary.total_detections}</div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">${summary.abnormal_detections} abnormal</div>
                </div>
                <div class="card" style="padding:0.6rem 0.8rem;">
                    <div style="font-size:0.65rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">Max Persons</div>
                    <div style="font-size:1.1rem;font-weight:700;margin-top:0.1rem;">${summary.max_persons_detected || 0}</div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">in single frame</div>
                </div>
                <div class="card" style="padding:0.6rem 0.8rem;">
                    <div style="font-size:0.65rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">Verdict</div>
                    <div style="font-size:1.1rem;font-weight:700;margin-top:0.1rem;color:${summary.status === 'abnormal_detected' ? '#ef4444' : 'var(--success)'};">
                        ${summary.status === 'abnormal_detected' ? '⚠ ALERT' : '✓ CLEAR'}
                    </div>
                    <div style="font-size:0.7rem;color:var(--text-secondary);">${(summary.activity_types_found || []).join(', ') || 'normal'}</div>
                </div>
            </div>

            <!-- Video Player + Activity Heatmap -->
            ${videoUrl ? `
            <div class="card" style="margin-bottom:0.75rem;padding:0;overflow:hidden;">
                <video id="det-video-player" src="${videoUrl}" controls preload="metadata"
                    style="width:100%;max-height:380px;display:block;background:#000;">
                </video>
                <div style="padding:0.5rem 0.75rem;">
                    <div style="font-size:0.7rem;color:var(--text-secondary);margin-bottom:0.3rem;">Activity Heatmap — click to seek</div>
                    <div id="det-heatmap" style="height:20px;border-radius:4px;overflow:hidden;background:rgba(255,255,255,0.03);display:flex;cursor:pointer;">
                    </div>
                </div>
            </div>
            ` : ''}

            <!-- Timeline -->
            <div class="card">
                <h3 style="margin:0 0 0.75rem;font-size:0.95rem;">
                    <i class="fa-solid fa-timeline" style="color:var(--primary);margin-right:0.4rem;"></i> Activity Timeline
                    <span style="font-size:0.75rem;color:var(--text-secondary);font-weight:400;margin-left:0.5rem;">${timeline.length} event${timeline.length !== 1 ? 's' : ''}</span>
                </h3>
                ${timeline.length === 0 ? `
                    <div style="text-align:center;padding:1.5rem;color:var(--text-secondary);">
                        <i class="fa-solid fa-check-circle" style="font-size:2rem;color:var(--success);display:block;margin-bottom:0.5rem;"></i>
                        No abnormal activities detected — all clear
                    </div>
                ` : `
                    <div style="display:flex;flex-direction:column;gap:0.35rem;">
                        ${timeline.map((t, i) => `
                            <div class="det-timeline-row" data-time="${t.start_time}" style="display:flex;gap:0.75rem;align-items:center;padding:0.55rem 0.6rem;border-radius:8px;background:rgba(255,255,255,0.02);border-left:3px solid ${sevColors[t.severity] || '#3b82f6'};cursor:pointer;transition:background 0.15s;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
                                <div style="min-width:55px;text-align:center;">
                                    <div style="font-size:0.85rem;font-weight:600;font-family:monospace;">${this._fmtTime(t.start_time)}</div>
                                    ${t.end_time !== t.start_time ? `<div style="font-size:0.65rem;color:var(--text-secondary);font-family:monospace;">→${this._fmtTime(t.end_time)}</div>` : ''}
                                </div>
                                <div style="flex:1;min-width:0;">
                                    <div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;">
                                        <span style="font-weight:600;font-size:0.85rem;text-transform:capitalize;">${t.activity}</span>
                                        <span style="font-size:0.6rem;padding:0.1rem 0.4rem;border-radius:3px;background:${sevColors[t.severity]}22;color:${sevColors[t.severity]};font-weight:600;">${t.severity.toUpperCase()}</span>
                                        ${t.is_abnormal ? '<span style="font-size:0.6rem;padding:0.1rem 0.4rem;border-radius:3px;background:#ef444422;color:#ef4444;font-weight:600;">ABNORMAL</span>' : ''}
                                    </div>
                                    <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.1rem;">
                                        ${(t.confidence * 100).toFixed(0)}% conf • ${t.person_count} person${t.person_count !== 1 ? 's' : ''} • frame ${t.start_frame}${t.end_frame !== t.start_frame ? '–' + t.end_frame : ''}
                                    </div>
                                    ${t.description ? `<div style="font-size:0.72rem;color:var(--text-secondary);margin-top:0.1rem;opacity:0.8;">${t.description}</div>` : ''}
                                </div>
                                <i class="fa-solid fa-play" style="color:var(--text-secondary);font-size:0.7rem;opacity:0.5;"></i>
                            </div>
                        `).join('')}
                    </div>
                `}
            </div>
        `;

        this._detWireResultEvents(data);
    }

    _detWireResultEvents(data) {
        const timeline = data.timeline || [];
        const frameResults = data.frame_results || [];
        const duration = data.video_info?.duration_sec || 1;

        // New test button
        document.getElementById('det-new-test-btn')?.addEventListener('click', () => {
            document.getElementById('det-results-area').style.display = 'none';
            document.getElementById('det-upload-card').style.display = '';
            document.getElementById('det-video-input').value = '';
            this._detTestAlerts = [];
            this._detUpdateAlertFeed();
            document.getElementById('det-stat-persons').textContent = '—';
            const st = document.getElementById('det-stat-status');
            st.textContent = '—'; st.style.color = '';
            this._detLoadLabeledClips();
        });

        // Cleanup button
        document.getElementById('det-cleanup-btn')?.addEventListener('click', async () => {
            if (!this._detTestFileId) return;
            const token = localStorage.getItem('jwt_token');
            await fetch(`/api/detection/cleanup/${this._detTestFileId}`, {
                method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }
            });
            Toast.success('Test video deleted');
            const btn = document.getElementById('det-cleanup-btn');
            if (btn) { btn.disabled = true; btn.textContent = 'Deleted'; }
        });

        // Timeline rows → seek video
        document.querySelectorAll('.det-timeline-row').forEach(row => {
            row.addEventListener('click', () => {
                const t = parseFloat(row.dataset.time);
                const video = document.getElementById('det-video-player');
                if (video && !isNaN(t)) { video.currentTime = t; video.play(); }
            });
        });

        // Build activity heatmap
        const heatmap = document.getElementById('det-heatmap');
        if (heatmap && frameResults.length > 0) {
            const sevColors = { high: '#ef4444', medium: '#f59e0b', low: '#3b82f6' };
            const binCount = Math.min(200, Math.max(50, frameResults.length));
            const binDuration = duration / binCount;
            const bins = new Array(binCount).fill(null);
            const sevOrder = { high: 3, medium: 2, low: 1 };

            for (const fr of frameResults) {
                const binIdx = Math.min(Math.floor(fr.time / binDuration), binCount - 1);
                if (fr.abnormal || fr.activity !== 'normal') {
                    const existing = bins[binIdx];
                    if (!existing || (sevOrder[fr.severity] || 0) > (sevOrder[existing.severity] || 0)) {
                        bins[binIdx] = fr;
                    }
                }
            }

            heatmap.innerHTML = bins.map((bin, i) => {
                const color = bin ? (sevColors[bin.severity] || '#3b82f6') : 'rgba(255,255,255,0.05)';
                const opacity = bin ? (bin.abnormal ? '0.9' : '0.5') : '0.3';
                const timeAt = (i * binDuration).toFixed(1);
                return `<div data-time="${timeAt}" style="flex:1;height:100%;background:${color};opacity:${opacity};" title="${bin ? bin.activity + ' @ ' + this._fmtTime(bin.time) : 'normal'}"></div>`;
            }).join('');

            heatmap.addEventListener('click', (e) => {
                const rect = heatmap.getBoundingClientRect();
                const pct = (e.clientX - rect.left) / rect.width;
                const video = document.getElementById('det-video-player');
                if (video) { video.currentTime = pct * duration; video.play(); }
            });
        }
    }

    async _detShowHistory() {
        const modal = document.getElementById('det-history-modal');
        modal.style.display = 'flex';
        const list = document.getElementById('det-history-list');
        list.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--text-secondary);">Loading...</div>';

        try {
            const token = localStorage.getItem('jwt_token');
            const res = await fetch('/api/detection/history', { headers: { 'Authorization': `Bearer ${token}` } });
            const videos = await res.json();
            if (videos.length === 0) {
                list.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-secondary);">No test videos found</div>';
                return;
            }
            list.innerHTML = videos.map(v => `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:0.6rem;border-bottom:1px solid rgba(255,255,255,0.05);">
                    <div>
                        <div style="font-size:0.85rem;font-weight:600;">${v.filename}</div>
                        <div style="font-size:0.75rem;color:var(--text-secondary);">${v.size_mb} MB</div>
                    </div>
                    <a href="${v.url}" target="_blank" class="btn" style="font-size:0.75rem;">
                        <i class="fa-solid fa-play"></i> Play
                    </a>
                </div>
            `).join('');
        } catch {
            list.innerHTML = '<div style="text-align:center;padding:1rem;color:#ef4444;">Failed to load history</div>';
        }
    }

    _fmtTime(seconds) {
        if (seconds == null || isNaN(seconds)) return '0:00';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    // --- Labeled Clips Library ---
    async _detLoadLabeledClips() {
        const grid = document.getElementById('det-my-clips-grid');
        const countEl = document.getElementById('det-clips-count');
        if (!grid) return;

        try {
            const token = localStorage.getItem('jwt_token');
            const res = await fetch('/api/detection/labeled-clips', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const clips = await res.json();

            countEl.textContent = `${clips.length} clip${clips.length !== 1 ? 's' : ''}`;

            if (!clips || clips.length === 0) {
                grid.innerHTML = `<div style="text-align:center;padding:1.5rem;color:var(--text-secondary);font-size:0.8rem;grid-column:1/-1;">
                    <i class="fa-solid fa-upload" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;opacity:0.4;"></i>
                    No labelled clips yet. Upload videos above to get started.
                </div>`;
                return;
            }

            const labelIcons = {
                fighting: '🥊', running: '🏃', falling: '🤸',
                loitering: '🚶', no_activity: '✅', no_person: '🚫'
            };
            const labelColors = {
                fighting: '#ef4444', running: '#f59e0b', falling: '#8b5cf6',
                loitering: '#3b82f6', no_activity: '#10b981', no_person: '#6b7280'
            };

            grid.innerHTML = clips.map(c => `
                <div class="det-labeled-clip" data-file-id="${c.file_id}"
                    style="padding:0.65rem;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);position:relative;transition:all 0.2s ease;"
                    onmouseover="this.style.borderColor='var(--primary)';this.style.background='rgba(99,102,241,0.06)'"
                    onmouseout="this.style.borderColor='rgba(255,255,255,0.06)';this.style.background='rgba(255,255,255,0.03)'">
                    <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.3rem;">
                        <span style="font-size:1rem;">${labelIcons[c.label] || '❓'}</span>
                        <span style="font-size:0.62rem;padding:0.1rem 0.35rem;border-radius:3px;background:${labelColors[c.label] || '#6b7280'}22;color:${labelColors[c.label] || '#6b7280'};font-weight:600;text-transform:uppercase;">${c.label.replace('_', ' ')}</span>
                        <span style="font-size:0.62rem;padding:0.1rem 0.3rem;border-radius:3px;background:rgba(255,255,255,0.05);color:var(--text-secondary);">
                            ${c.person_count === 'crowd' ? '13+ ppl' : c.person_count + ' ppl'}
                        </span>
                    </div>
                    <div style="font-size:0.78rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${c.original_name}">${c.original_name}</div>
                    <div style="font-size:0.68rem;color:var(--text-secondary);margin-top:0.15rem;display:flex;justify-content:space-between;align-items:center;">
                        <span>${c.size_mb} MB</span>
                        <button class="det-delete-clip-btn" data-file-id="${c.file_id}" style="font-size:0.65rem;padding:0.1rem 0.35rem;border-radius:4px;border:1px solid rgba(239,68,68,0.3);background:transparent;color:#ef4444;cursor:pointer;transition:all 0.2s;" title="Delete clip">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                    <div style="position:absolute;bottom:0;left:0;right:0;height:2px;background:${labelColors[c.label] || '#6b7280'};opacity:0.5;"></div>
                </div>
            `).join('');

            // Wire delete buttons
            grid.querySelectorAll('.det-delete-clip-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._detDeleteClip(btn.dataset.fileId);
                });
            });

        } catch (e) {
            grid.innerHTML = `<div style="text-align:center;padding:1rem;color:#ef4444;font-size:0.8rem;grid-column:1/-1;">Failed to load clips</div>`;
        }
    }

    async _detDeleteClip(fileId) {
        if (!confirm('Delete this labeled clip?')) return;
        try {
            const token = localStorage.getItem('jwt_token');
            await fetch(`/api/detection/labeled-clip/${fileId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            Toast.success('Clip deleted');
            this._detLoadLabeledClips();
        } catch (e) {
            Toast.error('Failed to delete clip');
        }
    }

    async _detTriggerRetrain() {
        if (!confirm('Start retraining the LSTM model with all labeled clips? This may take several minutes.')) return;

        const btn = document.getElementById('det-retrain-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Training...';
        }

        try {
            const token = localStorage.getItem('jwt_token');
            const res = await fetch('/api/detection/retrain', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            if (!res.ok) {
                Toast.error(data.error || 'Retrain failed');
                return;
            }
            Toast.success(data.message || 'Retraining started');

            // Poll for completion
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch('/api/detection/retrain-status', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const statusData = await statusRes.json();
                    if (!statusData.running) {
                        clearInterval(pollInterval);
                        Toast.success('Model retraining complete!');
                        if (btn) {
                            btn.disabled = false;
                            btn.innerHTML = '<i class="fa-solid fa-brain"></i> Retrain Model';
                        }
                    }
                } catch {
                    clearInterval(pollInterval);
                }
            }, 5000);

        } catch (e) {
            Toast.error('Failed to start retraining: ' + e.message);
        } finally {
            if (btn && !btn.disabled) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-brain"></i> Retrain Model';
            }
        }
    }


    // --- Alert Beep Sound ---
    _detPlayAlertBeep() {
        const soundEnabled = document.getElementById('det-sound-toggle')?.checked;
        if (!soundEnabled) return;

        try {
            if (!this._detAudioCtx) {
                this._detAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            const ctx = this._detAudioCtx;

            // Two-tone alert: high urgency beep
            const playTone = (freq, startTime, duration) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = freq;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, startTime);
                gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
                osc.start(startTime);
                osc.stop(startTime + duration);
            };

            const now = ctx.currentTime;
            // Three rapid beeps: beep-beep-beep
            playTone(880, now, 0.15);
            playTone(1100, now + 0.18, 0.15);
            playTone(880, now + 0.36, 0.2);
        } catch (e) {
            // Audio not available — silent fallback
        }
    }

    // --- Batch Accuracy Test ---
    async _detRunBatchTest() {
        const batchArea = document.getElementById('det-batch-results');
        if (!batchArea) return;

        document.getElementById('det-results-area').style.display = 'none';
        document.getElementById('det-upload-card').style.display = 'none';
        const procCard = document.getElementById('det-processing-card');
        procCard.style.display = '';
        batchArea.style.display = 'none';

        const bar = document.getElementById('det-proc-bar');
        const status = document.getElementById('det-proc-status');
        const title = document.getElementById('det-proc-title');
        title.textContent = 'Running Batch Accuracy Test...';
        status.textContent = 'Processing all clips through detection pipeline...';
        bar.style.width = '15%';

        const sampleFps = document.getElementById('det-fps-slider')?.value || 5;

        try {
            let progress = 15;
            const interval = setInterval(() => {
                if (progress < 90) { progress += Math.random() * 1.5; bar.style.width = Math.min(progress, 90) + '%'; }
                if (progress > 30 && progress < 50) status.textContent = 'Processing fight clips...';
                if (progress > 50 && progress < 70) status.textContent = 'Processing running clips...';
                if (progress > 70) status.textContent = 'Computing accuracy metrics...';
            }, 800);

            const token = localStorage.getItem('jwt_token');
            const response = await fetch('/api/detection/batch-test', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ sample_fps: parseFloat(sampleFps) }),
            });

            clearInterval(interval);
            bar.style.width = '100%';
            status.textContent = 'Complete!';

            if (!response.ok) throw new Error('Batch test failed');
            const data = await response.json();

            setTimeout(() => {
                procCard.style.display = 'none';
                document.getElementById('det-upload-card').style.display = '';
                batchArea.style.display = '';

                const results = data.results || [];
                const accColor = data.accuracy >= 80 ? 'var(--success)' : data.accuracy >= 60 ? '#f59e0b' : '#ef4444';

                batchArea.innerHTML = `
                    <div class="card" style="margin-bottom:0.75rem;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                            <h3 style="margin:0;font-size:1rem;">
                                <i class="fa-solid fa-vials" style="color:var(--primary);margin-right:0.4rem;"></i> Batch Accuracy Results
                            </h3>
                            <div style="display:flex;align-items:center;gap:1rem;">
                                <span style="font-size:0.85rem;color:var(--text-secondary);">${data.correct}/${data.total} correct</span>
                                <span style="font-size:1.3rem;font-weight:700;color:${accColor};">${data.accuracy}%</span>
                            </div>
                        </div>

                        <div style="width:100%;background:rgba(255,255,255,0.05);border-radius:8px;height:8px;overflow:hidden;margin-bottom:1rem;">
                            <div style="height:100%;width:${data.accuracy}%;background:${accColor};border-radius:8px;transition:width 0.5s ease;"></div>
                        </div>

                        <div style="overflow-x:auto;">
                            <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
                                <thead>
                                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
                                        <th style="text-align:left;padding:0.5rem;color:var(--text-secondary);font-weight:600;">File</th>
                                        <th style="text-align:center;padding:0.5rem;color:var(--text-secondary);font-weight:600;">Expected</th>
                                        <th style="text-align:center;padding:0.5rem;color:var(--text-secondary);font-weight:600;">Detected</th>
                                        <th style="text-align:center;padding:0.5rem;color:var(--text-secondary);font-weight:600;">Persons</th>
                                        <th style="text-align:center;padding:0.5rem;color:var(--text-secondary);font-weight:600;">Time</th>
                                        <th style="text-align:center;padding:0.5rem;color:var(--text-secondary);font-weight:600;">Result</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${results.map(r => `
                                        <tr style="border-bottom:1px solid rgba(255,255,255,0.04);${r.correct ? '' : 'background:rgba(239,68,68,0.05);'}">
                                            <td style="padding:0.5rem;font-weight:500;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${r.file}">${r.file}</td>
                                            <td style="text-align:center;padding:0.5rem;text-transform:capitalize;">${r.expected}</td>
                                            <td style="text-align:center;padding:0.5rem;text-transform:capitalize;">${(r.detected || []).join(', ') || 'normal'}</td>
                                            <td style="text-align:center;padding:0.5rem;">${r.max_persons || 0}</td>
                                            <td style="text-align:center;padding:0.5rem;font-family:monospace;">${r.processing_time ? r.processing_time.toFixed(1) + 's' : '-'}</td>
                                            <td style="text-align:center;padding:0.5rem;">
                                                ${r.correct
                        ? '<span style="color:var(--success);font-weight:600;"><i class="fa-solid fa-check-circle"></i> Pass</span>'
                        : '<span style="color:#ef4444;font-weight:600;"><i class="fa-solid fa-times-circle"></i> Fail</span>'}
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;

                // Play sound based on results
                if (data.accuracy < 100) this._detPlayAlertBeep();

            }, 400);

        } catch (error) {
            Toast.error('Batch test failed: ' + error.message);
            procCard.style.display = 'none';
            document.getElementById('det-upload-card').style.display = '';
        }
    }

    // ============ SETTINGS ============

    async loadSettings(container) {
        container.innerHTML = `
    <div class="settings-grid">
                <div class="card">
                    <h3><i class="fa-solid fa-server"></i> System Status</h3>
                    <p class="hint" style="margin-bottom:0.75rem;">Real-time health check of system components.</p>
                    <div id="system-status">
                        <div class="skeleton" style="height: 40px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 40px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 40px;"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fa-solid fa-video"></i> Stream Configuration</h3>
                    <p class="hint" style="margin-bottom:0.75rem;">Use these endpoints to connect your streaming client.</p>
                    <div class="form-group">
                        <label>Server WebSocket URL</label>
                        <input type="text" value="ws://${window.location.host}/stream" readonly>
                        <p class="hint">WebSocket URL for the streaming client to connect to.</p>
                    </div>
                    <div class="form-group">
                        <label>Stream Command</label>
                        <input type="text" value="python stream_client.py --server http://${window.location.host}" readonly>
                        <p class="hint">Run this command on a machine with cameras connected.</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fa-solid fa-sliders"></i> Detection Thresholds</h3>
                    <p class="hint" style="margin-bottom:0.75rem;">Adjust sensitivity of the ML-based detection models. Higher values reduce false positives but may miss real events.</p>
                    <div class="form-group">
                        <label>Face Recognition Confidence</label>
                        <input type="range" min="50" max="95" value="60" id="face-threshold">
                        <span id="face-threshold-val">60%</span>
                        <p class="hint">Minimum confidence score (50-95%) to consider a face match valid.</p>
                    </div>
                    <div class="form-group">
                        <label>Running Detection Sensitivity</label>
                        <input type="range" min="1" max="5" step="0.5" value="2.5" id="running-threshold">
                        <span id="running-threshold-val">2.5</span>
                        <p class="hint">Speed multiplier threshold (1-5). Lower = more sensitive.</p>
                    </div>
                    <button class="btn primary" onclick="Toast.success('Settings saved!')">
                        <i class="fa-solid fa-save"></i> Save Settings
                    </button>
                </div>

                <div class="card">
                    <h3><i class="fa-solid fa-bell"></i> Notification Settings</h3>
                    <p class="hint" style="margin-bottom:0.75rem;">Configure how you receive alerts when events are detected.</p>
                    <div class="form-group" style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                        <div>
                            <label style="margin-bottom:0;">Desktop Notifications</label>
                            <p class="hint" style="margin:0;">Show browser push notifications for new alerts.</p>
                        </div>
                        <label class="toggle-switch" style="position:relative;display:inline-block;width:44px;height:24px;">
                            <input type="checkbox" id="desktop-notif-toggle" checked style="opacity:0;width:0;height:0;">
                            <span style="position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:rgba(255,255,255,0.15);border-radius:24px;transition:0.3s;"></span>
                        </label>
                    </div>
                    <div class="form-group" style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                        <div>
                            <label style="margin-bottom:0;">Sound Alerts</label>
                            <p class="hint" style="margin:0;">Play a sound when critical alerts are detected.</p>
                        </div>
                        <label class="toggle-switch" style="position:relative;display:inline-block;width:44px;height:24px;">
                            <input type="checkbox" id="sound-notif-toggle" style="opacity:0;width:0;height:0;">
                            <span style="position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:rgba(255,255,255,0.15);border-radius:24px;transition:0.3s;"></span>
                        </label>
                    </div>
                    <div class="form-group" style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;">
                        <div>
                            <label style="margin-bottom:0;">Auto-refresh Dashboard</label>
                            <p class="hint" style="margin:0;">Automatically refresh dashboard data every 30 seconds.</p>
                        </div>
                        <label class="toggle-switch" style="position:relative;display:inline-block;width:44px;height:24px;">
                            <input type="checkbox" id="autorefresh-toggle" checked style="opacity:0;width:0;height:0;">
                            <span style="position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:rgba(255,255,255,0.15);border-radius:24px;transition:0.3s;"></span>
                        </label>
                    </div>
                    <div class="form-group" style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                        <div>
                            <label style="margin-bottom:0;">📧 Email Notifications</label>
                            <p class="hint" style="margin:0;">Send email alerts for high & medium severity events (via AWS SES).</p>
                        </div>
                        <label class="toggle-switch" style="position:relative;display:inline-block;width:44px;height:24px;">
                            <input type="checkbox" id="email-notif-toggle" ${localStorage.getItem('emailNotif') !== 'false' ? 'checked' : ''} style="opacity:0;width:0;height:0;">
                            <span style="position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:rgba(255,255,255,0.15);border-radius:24px;transition:0.3s;"></span>
                        </label>
                    </div>
                    <div class="form-group" style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem 0;">
                        <div>
                            <label style="margin-bottom:0;">Email Severity Filter</label>
                            <p class="hint" style="margin:0;">Only send emails for alerts at or above this level.</p>
                        </div>
                        <select id="email-severity-select" style="padding:0.4rem 0.75rem;border-radius:6px;border:1px solid rgba(255,255,255,0.1);background:var(--bg-card);color:white;">
                            <option value="high" ${localStorage.getItem('emailSeverity') === 'high' ? 'selected' : ''}>High Only</option>
                            <option value="medium" ${localStorage.getItem('emailSeverity') === 'medium' || !localStorage.getItem('emailSeverity') ? 'selected' : ''}>Medium & High</option>
                        </select>
                    </div>
                </div>
            </div>
    `;

        // Load system status
        try {
            const health = await API.healthCheck();
            document.getElementById('system-status').innerHTML = `
    <div class="status-item">
                    <span><i class="fa-solid fa-database"></i> Database</span>
                    <span class="status-badge ${health.database === 'connected' ? 'connected' : 'disconnected'}">
                        ${health.database}
                    </span>
                </div>
                <div class="status-item">
                    <span><i class="fa-solid fa-users"></i> Total Students</span>
                    <span>${health.stats?.total_students || 0}</span>
                </div>
                <div class="status-item">
                    <span><i class="fa-solid fa-bell"></i> Recent Alerts</span>
                    <span>${health.stats?.recent_alerts || 0}</span>
                </div>
                <div class="status-item">
                    <span><i class="fa-solid fa-clock"></i> Server Time</span>
                    <span>${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}</span>
                </div>
`;
        } catch (error) {
            document.getElementById('system-status').innerHTML =
                '<div class="error-state">Failed to load status</div>';
        }

        // Range slider handlers
        document.getElementById('face-threshold').addEventListener('input', (e) => {
            document.getElementById('face-threshold-val').textContent = e.target.value + '%';
        });
        document.getElementById('running-threshold').addEventListener('input', (e) => {
            document.getElementById('running-threshold-val').textContent = e.target.value;
        });
    }

    // ============ UTILITIES ============

    getAlertIcon(type) {
        const icons = {
            running: 'person-running',
            fighting: 'hand-fist',
            loitering: 'clock',
            unauthorized_entry: 'door-open',
            suspicious_activity: 'exclamation'
        };
        return icons[type] || 'triangle-exclamation';
    }

    formatEventType(type) {
        return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    timeAgo(timestamp) {
        const seconds = Math.floor((Date.now() - new Date(timestamp)) / 1000);

        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            if (this.currentPage === 'dashboard') {
                this.loadRecentAlerts();
                this.loadRecentAttendance();
            }
        }, 30000);
    }

    // ============ WEBSOCKET ============

    // Stream mode configuration
    streamModes = {
        jpegws: { port: null, wsPath: '/ws/stream', name: 'JPEG WebSocket' },
        fastrtc: { port: null, wsPath: '/ws/fastrtc', name: 'FastRTC' },
    };
    currentMode = 'jpegws';
    autoSwitch = false;
    _reconnectTimer = null;
    _autoSwitchTimer = null;
    _latencyByMode = { jpegws: [], fastrtc: [] };

    async initStreamConfig() {
        // Load saved mode from server
        try {
            const resp = await fetch('/api/stream/config');
            const config = await resp.json();
            this.currentMode = config.current_mode || 'jpegws';
            this.autoSwitch = config.auto_switch || false;
        } catch (e) {
            console.warn('Could not load stream config:', e);
        }

        // Use document-level event delegation — works even after DOM re-renders
        document.addEventListener('change', (e) => {
            if (e.target && e.target.id === 'stream-mode-select') {
                const newMode = e.target.value;
                if (newMode !== this.currentMode) {
                    this.currentMode = newMode;
                    this.saveStreamConfig();
                    this.switchStream(newMode);
                }
            }
        });

        document.addEventListener('click', (e) => {
            // Check if click was on the toggle or its child (the knob)
            const toggle = e.target.closest('#auto-switch-toggle');
            if (toggle) {
                this.autoSwitch = !this.autoSwitch;
                this.updateToggleVisual(toggle, this.autoSwitch);
                const autoLabel = document.getElementById('auto-switch-label');
                if (autoLabel) autoLabel.textContent = this.autoSwitch ? 'On' : 'Off';
                this.saveStreamConfig();

                if (this.autoSwitch) {
                    this.startAutoSwitch();
                } else {
                    this.stopAutoSwitch();
                }
            }
        });
    }

    // Called after loadLiveMonitor renders the DOM — sync UI state
    syncStreamUI() {
        const modeSelect = document.getElementById('stream-mode-select');
        if (modeSelect) modeSelect.value = this.currentMode;
        const autoToggle = document.getElementById('auto-switch-toggle');
        if (autoToggle) this.updateToggleVisual(autoToggle, this.autoSwitch);
        const autoLabel = document.getElementById('auto-switch-label');
        if (autoLabel) autoLabel.textContent = this.autoSwitch ? 'On' : 'Off';
    }

    updateToggleVisual(toggle, isOn) {
        const knob = toggle.querySelector('div');
        if (isOn) {
            toggle.style.background = 'var(--success, #22c55e)';
            toggle.style.borderColor = 'var(--success, #22c55e)';
            if (knob) knob.style.transform = 'translateX(18px)';
        } else {
            toggle.style.background = 'var(--bg-tertiary)';
            toggle.style.borderColor = 'var(--border)';
            if (knob) knob.style.transform = 'translateX(0)';
        }
        toggle.dataset.on = isOn ? 'true' : 'false';
    }

    async saveStreamConfig() {
        try {
            await fetch('/api/stream/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: this.currentMode, auto_switch: this.autoSwitch }),
            });
        } catch (e) {
            console.warn('Could not save stream config:', e);
        }
    }

    switchStream(mode) {
        console.log(`Switching stream to ${mode} `);
        // Close existing connection
        if (this.streamWs) {
            this.streamWs._manualClose = true;
            this.streamWs.close();
            this.streamWs = null;
        }
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
            this._reconnectTimer = null;
        }
        this.currentMode = mode;
        this._streamActive = false;
        this.frameCount = 0;
        this.connectStream();
    }

    connectSocket() {
        this.initStreamConfig().then(() => {
            this.connectStream();

            // Start auto-switch if enabled
            if (this.autoSwitch) this.startAutoSwitch();
        });

        // Socket.IO for alerts/detections (non-video events)
        if (typeof io !== 'undefined') {
            this.socket = io('/stream');
            this.socket.on('detection', (data) => this.handleDetection(data));
            this.socket.on('new_alert', (data) => {
                const eventType = data.type || data.event_type || 'unknown';
                Toast.warning(`New Alert: ${this.formatEventType(eventType)} `, 'Security Alert');
                this.showDesktopNotification(`Alert: ${this.formatEventType(eventType)} `);

                // Update alert badge count
                const badge = document.getElementById('alert-count');
                if (badge) badge.textContent = parseInt(badge.textContent || '0') + 1;

                // Push to live event feed if on dashboard
                const feed = document.getElementById('live-event-feed');
                if (feed) {
                    const emptyState = feed.querySelector('.empty-state');
                    if (emptyState) emptyState.remove();

                    const entry = document.createElement('div');
                    entry.className = 'list-item';
                    entry.style.cssText = 'animation:fadeIn 0.3s;cursor:pointer;transition:background 0.15s;';
                    entry.onclick = () => { if (data.id) this.viewAlertDetail(data.id); };
                    entry.innerHTML = `
    <div class="item-icon ${data.severity || 'medium'}">
        <i class="fa-solid fa-${this.getAlertIcon(eventType)}"></i>
                        </div>
                        <div class="item-content">
                            <div class="item-title">${this.formatEventType(eventType)}</div>
                            <div class="item-subtitle">Camera ${data.camera_id || '?'} · Just now</div>
                        </div>
                        <span class="badge ${data.severity || 'medium'}">${data.severity || 'medium'}</span>
`;
                    feed.prepend(entry);

                    // Keep max 10 items
                    while (feed.children.length > 10) feed.lastChild.remove();
                }

                // Refresh alerts list if currently viewing alerts page
                if (this.currentPage === 'alerts') {
                    this.loadAlertsData();
                }
            });
        }
    }

    connectStream() {
        const mode = this.streamModes[this.currentMode];
        if (!mode) return;

        const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const portPart = mode.port ? `:${mode.port} ` : (location.port ? `:${location.port} ` : '');
        const streamUrl = `${wsProtocol}//${location.hostname}${portPart}${mode.wsPath}`;

        console.log(`Connecting to ${this.currentMode} stream: ${streamUrl}`);
        this.streamWs = new WebSocket(streamUrl);
        this.streamWs._manualClose = false;

        this.streamWs.onopen = () => {
            console.log(`${this.currentMode} stream connected`);
            // For jpegws mode, send viewer handshake
            if (this.currentMode === 'jpegws') {
                this.streamWs.send(JSON.stringify({ type: 'viewer' }));
            }
            this.updateConnectionStatus(true);
        };

        this.streamWs.onclose = () => {
            if (this.streamWs && this.streamWs._manualClose) return;
            console.log(`${this.currentMode} stream disconnected`);
            this.updateConnectionStatus(false);
            this._streamActive = false;
            // Auto-reconnect
            this._reconnectTimer = setTimeout(() => this.connectStream(), 3000);
        };

        this.streamWs.onerror = (err) => {
            console.error(`${this.currentMode} stream error:`, err);
        };

        this.streamWs.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'frame') {
                    this.displayFrame(data);
                } else if (data.type === 'status') {
                    this.updateConnectionStatus(data.streaming);
                } else if (data.type === 'stream_ended') {
                    this.updateConnectionStatus(false);
                    this._streamActive = false;
                }
            } catch (e) {
                console.error('Message parse error:', e);
            }
        };
    }

    // --- Auto-Switch Logic ---
    startAutoSwitch() {
        this.stopAutoSwitch();
        console.log('Auto-switch enabled: checking latency every 30s');
        this._autoSwitchTimer = setInterval(() => this.checkAndAutoSwitch(), 30000);
    }

    stopAutoSwitch() {
        if (this._autoSwitchTimer) {
            clearInterval(this._autoSwitchTimer);
            this._autoSwitchTimer = null;
        }
    }

    async checkAndAutoSwitch() {
        // Ping both servers and compare latency
        const results = {};
        for (const [mode, config] of Object.entries(this.streamModes)) {
            try {
                const start = Date.now();
                const resp = await fetch(`${location.protocol}//${location.hostname}:${config.port}${config.port === 8080 ? '/health' : ''}`, {
                    signal: AbortSignal.timeout(5000),
                });
                if (resp.ok) {
                    results[mode] = Date.now() - start;
                }
            } catch (e) {
                results[mode] = Infinity;
            }
        }

        console.log('Auto-switch latency check:', results);

        // Check frame-based latency samples
        const jpegwsLatency = this._latencyByMode.jpegws.length > 0
            ? this._latencyByMode.jpegws.reduce((a, b) => a + b) / this._latencyByMode.jpegws.length
            : results.jpegws || Infinity;
        const fastrtcLatency = this._latencyByMode.fastrtc.length > 0
            ? this._latencyByMode.fastrtc.reduce((a, b) => a + b) / this._latencyByMode.fastrtc.length
            : results.fastrtc || Infinity;

        // Switch if the other mode is significantly better (>50ms improvement)
        const currentLatency = this.currentMode === 'jpegws' ? jpegwsLatency : fastrtcLatency;
        const otherMode = this.currentMode === 'jpegws' ? 'fastrtc' : 'jpegws';
        const otherLatency = otherMode === 'jpegws' ? jpegwsLatency : fastrtcLatency;

        if (otherLatency < currentLatency - 50 && otherLatency < Infinity) {
            console.log(`Auto-switching from ${this.currentMode} (${Math.round(currentLatency)}ms) to ${otherMode} (${Math.round(otherLatency)}ms)`);
            const modeSelect = document.getElementById('stream-mode-select');
            if (modeSelect) modeSelect.value = otherMode;
            this.currentMode = otherMode;
            await this.saveStreamConfig();
            this.switchStream(otherMode);
        }

        // Clear old samples
        this._latencyByMode.jpegws = [];
        this._latencyByMode.fastrtc = [];
    }

    updateConnectionStatus(connected) {
        const wsStatus = document.getElementById('ws-status');
        const streamStatus = document.getElementById('stream-status');

        if (wsStatus) {
            wsStatus.textContent = connected ? 'Connected' : 'Disconnected';
            wsStatus.className = `status-badge ${connected ? 'connected' : 'disconnected'}`;
        }

        if (streamStatus) {
            streamStatus.innerHTML = connected
                ? '<i class="fa-solid fa-circle"></i> Connected'
                : '<i class="fa-solid fa-circle"></i> Disconnected';
            streamStatus.className = `feed-status ${connected ? 'connected' : ''}`;
        }
    }

    displayFrame(data) {
        // --- Decode frame once, draw on multiple canvases ---
        const mainCanvas = document.getElementById('main-canvas');
        const activityCanvas = document.getElementById('activity-canvas');
        const faceCanvas = document.getElementById('face-canvas');

        // Need at least one canvas to proceed
        if (!mainCanvas && !activityCanvas && !faceCanvas) return;

        // Hide overlays
        ['feed-overlay', 'activity-overlay', 'face-overlay'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });

        // Decode base64 → Blob → ObjectURL
        const raw = atob(data.frame);
        const bytes = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);

        if (!this._frameImg) this._frameImg = new Image();
        const img = this._frameImg;
        const self = this;

        img.onload = () => {
            const w = img.width, h = img.height;

            // ========== 1. MAIN CANVAS — Raw video only ==========
            if (mainCanvas) {
                mainCanvas.width = w;
                mainCanvas.height = h;
                const ctx = mainCanvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
            }

            // ========== 2. ACTIVITY CANVAS — Video + Skeleton overlay ==========
            if (activityCanvas) {
                activityCanvas.width = w;
                activityCanvas.height = h;
                const actCtx = activityCanvas.getContext('2d');
                actCtx.drawImage(img, 0, 0);

                // Draw skeleton from activity data
                const activity = data.activity;
                if (activity && activity.persons && activity.persons.length > 0) {
                    const actType = activity.type || 'normal';
                    const boneColor = self._ACTIVITY_COLORS[actType] || 'rgba(0, 200, 255, 0.8)';

                    for (const person of activity.persons) {
                        const kps = person.keypoints;
                        const confs = person.confidences;
                        if (!kps || kps.length < 17) continue;

                        // Draw bones (skeleton lines)
                        actCtx.strokeStyle = boneColor;
                        actCtx.lineWidth = 3;
                        actCtx.shadowColor = 'rgba(0, 0, 0, 0.5)';
                        actCtx.shadowBlur = 3;
                        for (const [i, j] of self._SKELETON) {
                            if (confs && (confs[i] < 0.3 || confs[j] < 0.3)) continue;
                            actCtx.beginPath();
                            actCtx.moveTo(kps[i][0], kps[i][1]);
                            actCtx.lineTo(kps[j][0], kps[j][1]);
                            actCtx.stroke();
                        }

                        // Draw joints (dots)
                        actCtx.shadowBlur = 0;
                        for (let k = 0; k < 17; k++) {
                            if (confs && confs[k] < 0.3) continue;
                            actCtx.beginPath();
                            actCtx.arc(kps[k][0], kps[k][1], 4, 0, 2 * Math.PI);
                            actCtx.fillStyle = '#fff';
                            actCtx.fill();
                            actCtx.strokeStyle = boneColor;
                            actCtx.lineWidth = 2;
                            actCtx.stroke();
                        }

                        // Draw bbox
                        if (person.bbox) {
                            const [x1, y1, x2, y2] = person.bbox;
                            actCtx.strokeStyle = boneColor;
                            actCtx.lineWidth = 2;
                            actCtx.setLineDash([6, 4]);
                            actCtx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                            actCtx.setLineDash([]);
                        }
                    }

                    // Activity label badge
                    if (actType !== 'normal') {
                        const label = actType.toUpperCase();
                        actCtx.font = 'bold 18px Inter, sans-serif';
                        const tw = actCtx.measureText(label).width + 24;
                        actCtx.fillStyle = boneColor;
                        actCtx.globalAlpha = 0.85;
                        actCtx.fillRect(w - tw - 10, 10, tw, 32);
                        actCtx.globalAlpha = 1;
                        actCtx.fillStyle = '#fff';
                        actCtx.shadowBlur = 0;
                        actCtx.fillText(label, w - tw, 33);
                    }

                    // Update activity stats
                    const personCount = document.getElementById('person-count');
                    if (personCount) personCount.textContent = activity.persons.length;
                    const actConf = document.getElementById('activity-confidence');
                    if (actConf) actConf.textContent = activity.confidence ? `${(activity.confidence * 100).toFixed(0)}%` : '--';
                    const actStatus = document.getElementById('activity-status');
                    if (actStatus) {
                        actStatus.textContent = actType.charAt(0).toUpperCase() + actType.slice(1);
                        actStatus.style.color = self._ACTIVITY_COLORS[actType] || '#22c55e';
                    }
                    const badge = document.getElementById('activity-badge');
                    if (badge) {
                        badge.textContent = actType.charAt(0).toUpperCase() + actType.slice(1);
                        if (actType !== 'normal') {
                            badge.classList.add('abnormal');
                            badge.style.background = `${self._ACTIVITY_COLORS[actType]}22`;
                            badge.style.color = self._ACTIVITY_COLORS[actType];
                        } else {
                            badge.classList.remove('abnormal');
                            badge.style.background = 'rgba(34, 197, 94, 0.15)';
                            badge.style.color = '#22c55e';
                        }
                    }
                }
            }

            // ========== 3. FACE CANVAS — Video + Face bounding boxes ==========
            if (faceCanvas) {
                faceCanvas.width = w;
                faceCanvas.height = h;
                const faceCtx = faceCanvas.getContext('2d');
                faceCtx.drawImage(img, 0, 0);

                if (data.recognition && data.recognition.recognitions && data.recognition.recognitions.length > 0) {
                    const recognitions = data.recognition.recognitions;

                    recognitions.forEach(rec => {
                        const [rx, ry, rw, rh] = rec.bbox;
                        const recognized = rec.name && rec.name !== 'Unknown';
                        const color = recognized ? '#22c55e' : '#3b82f6';

                        // Face bounding box with glow
                        faceCtx.shadowColor = color;
                        faceCtx.shadowBlur = 8;
                        faceCtx.strokeStyle = color;
                        faceCtx.lineWidth = 3;
                        faceCtx.strokeRect(rx, ry, rw, rh);
                        faceCtx.shadowBlur = 0;

                        // Corner accents (top-left and bottom-right)
                        const cornerLen = Math.min(rw, rh) * 0.2;
                        faceCtx.lineWidth = 4;
                        // Top-left
                        faceCtx.beginPath();
                        faceCtx.moveTo(rx, ry + cornerLen);
                        faceCtx.lineTo(rx, ry);
                        faceCtx.lineTo(rx + cornerLen, ry);
                        faceCtx.stroke();
                        // Top-right
                        faceCtx.beginPath();
                        faceCtx.moveTo(rx + rw - cornerLen, ry);
                        faceCtx.lineTo(rx + rw, ry);
                        faceCtx.lineTo(rx + rw, ry + cornerLen);
                        faceCtx.stroke();
                        // Bottom-left
                        faceCtx.beginPath();
                        faceCtx.moveTo(rx, ry + rh - cornerLen);
                        faceCtx.lineTo(rx, ry + rh);
                        faceCtx.lineTo(rx + cornerLen, ry + rh);
                        faceCtx.stroke();
                        // Bottom-right
                        faceCtx.beginPath();
                        faceCtx.moveTo(rx + rw - cornerLen, ry + rh);
                        faceCtx.lineTo(rx + rw, ry + rh);
                        faceCtx.lineTo(rx + rw, ry + rh - cornerLen);
                        faceCtx.stroke();

                        // Name label
                        const label = `${rec.name} (${(rec.confidence * 100).toFixed(0)}%)`;
                        faceCtx.font = 'bold 14px Inter, sans-serif';
                        const labelW = faceCtx.measureText(label).width + 14;
                        faceCtx.fillStyle = color;
                        faceCtx.globalAlpha = 0.9;
                        faceCtx.fillRect(rx, ry - 24, labelW, 24);
                        faceCtx.globalAlpha = 1;
                        faceCtx.fillStyle = '#fff';
                        faceCtx.fillText(label, rx + 7, ry - 7);
                    });

                    // Update face count
                    const faceCount = document.getElementById('face-count');
                    if (faceCount) faceCount.textContent = recognitions.length;
                }
            }

            URL.revokeObjectURL(url);

            // Update resolution display
            const resDisplay = document.getElementById('resolution-display');
            if (resDisplay) resDisplay.textContent = `${w}x${h}`;
        };
        img.src = url;

        // Update frame count
        this.frameCount = (this.frameCount || 0) + 1;
        const frameCountEl = document.getElementById('frame-count');
        if (frameCountEl) frameCountEl.textContent = this.frameCount;

        // Calculate FPS
        const now = Date.now();
        if (this.lastFrameTime) {
            const fps = 1000 / (now - this.lastFrameTime);
            const fpsDisplay = document.getElementById('fps-display');
            if (fpsDisplay) fpsDisplay.textContent = fps.toFixed(1);
        }
        this.lastFrameTime = now;

        // Calculate end-to-end latency
        let latencyMs = null;
        if (data.timestamp) {
            const clientTimeMs = parseFloat(data.timestamp) * 1000;
            latencyMs = now - clientTimeMs;
        } else if (data.server_time) {
            latencyMs = now - data.server_time;
        }
        if (latencyMs !== null && latencyMs >= 0) {
            const latencyDisplay = document.getElementById('latency-display');
            if (latencyDisplay) {
                if (latencyMs < 1000) {
                    latencyDisplay.textContent = `${Math.round(latencyMs)}ms`;
                } else {
                    latencyDisplay.textContent = `${(latencyMs / 1000).toFixed(1)}s`;
                }
                latencyDisplay.style.color = latencyMs < 300 ? 'var(--success)' : latencyMs < 600 ? 'var(--warning)' : 'var(--danger)';
            }
            if (this._latencyByMode && this._latencyByMode[this.currentMode]) {
                this._latencyByMode[this.currentMode].push(latencyMs);
                if (this._latencyByMode[this.currentMode].length > 100) {
                    this._latencyByMode[this.currentMode].shift();
                }
            }
        }

        // Mark connection as active
        if (!this._streamActive) {
            this._streamActive = true;
            this.updateConnectionStatus(true);
        }
    }

    // COCO skeleton connections for pose drawing
    _SKELETON = [
        [0, 1], [0, 2], [1, 3], [2, 4],         // head
        [5, 6],                             // shoulders
        [5, 7], [7, 9], [6, 8], [8, 10],         // arms
        [5, 11], [6, 12], [11, 12],            // torso
        [11, 13], [13, 15], [12, 14], [14, 16],  // legs
    ];
    _ACTIVITY_COLORS = {
        normal: '#22c55e', running: '#f59e0b', loitering: '#f59e0b',
        fighting: '#ef4444', falling: '#ef4444',
    };

    handleDetection(data) {
        const faces = data.faces || [];
        const activity = data.activity || {};
        const persons = data.persons || [];
        const activityType = typeof activity === 'string' ? activity : (activity.type || 'normal');

        // --- Update text indicators ---
        const faceCount = document.getElementById('face-count');
        if (faceCount) faceCount.textContent = faces.length;

        const activityStatus = document.getElementById('activity-status');
        if (activityStatus) {
            const label = activityType.charAt(0).toUpperCase() + activityType.slice(1);
            activityStatus.textContent = label;
            const c = this._ACTIVITY_COLORS[activityType] || '#22c55e';
            activityStatus.style.color = c;
            activityStatus.style.fontWeight = activityType !== 'normal' ? '700' : '500';
        }

        // --- Update sidebar detections list ---
        const liveDetections = document.getElementById('live-detections');
        if (liveDetections && faces.length > 0) {
            liveDetections.innerHTML = faces.map(face => {
                const name = face.student_name || face.name || 'Unknown';
                const conf = face.confidence ? (face.confidence * 100).toFixed(0) + '%' : '';
                const initial = name[0] || '?';
                const color = face.student_id ? 'var(--success)' : 'var(--text-secondary)';
                return `
                    <div class="list-item" style="padding:0.5rem;">
                        <div class="avatar" style="width:32px;height:32px;font-size:0.8rem;background:${color};">${initial}</div>
                        <div class="item-content">
                            <div class="item-title" style="font-size:0.85rem;">${name}</div>
                            <div class="item-subtitle">${conf}${face.age ? ' · Age ' + face.age : ''}</div>
                        </div>
                    </div>`;
            }).join('');
        } else if (liveDetections && faces.length === 0) {
            liveDetections.innerHTML = '<div class="empty-state small"><i class="fa-solid fa-eye-slash"></i><p>No detections</p></div>';
        }

        // --- Draw overlays on detection canvas ---
        this._drawDetectionOverlay(faces, persons, activityType, activity);
    }

    _drawDetectionOverlay(faces, persons, activityType, activity) {
        const canvas = document.getElementById('skeleton-overlay');
        const videoCanvas = document.getElementById('main-canvas');
        if (!canvas || !videoCanvas) return;

        // Sync size
        canvas.width = videoCanvas.width;
        canvas.height = videoCanvas.height;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw face boxes
        for (const face of faces) {
            const loc = face.location;
            if (!loc) continue;
            const x = loc.left, y = loc.top;
            const w = loc.right - loc.left, h = loc.bottom - loc.top;
            const recognized = !!face.student_id;
            const color = recognized ? '#22c55e' : '#3b82f6';

            // Bounding box
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);

            // Label background
            const name = face.student_name || face.name || 'Unknown';
            const conf = face.confidence ? ` ${(face.confidence * 100).toFixed(0)}%` : '';
            const label = `${name}${conf}`;
            ctx.font = 'bold 14px Inter, sans-serif';
            const tw = ctx.measureText(label).width + 8;
            ctx.fillStyle = color;
            ctx.fillRect(x, y - 22, tw, 22);
            ctx.fillStyle = '#fff';
            ctx.fillText(label, x + 4, y - 6);
        }

        // Draw pose skeletons
        for (const person of persons) {
            const kps = person.keypoints;
            const confs = person.confidences;
            if (!kps || kps.length < 17) continue;

            // Draw bones
            ctx.strokeStyle = 'rgba(0, 200, 255, 0.7)';
            ctx.lineWidth = 2;
            for (const [i, j] of this._SKELETON) {
                if ((confs && confs[i] < 0.3) || (confs && confs[j] < 0.3)) continue;
                ctx.beginPath();
                ctx.moveTo(kps[i][0], kps[i][1]);
                ctx.lineTo(kps[j][0], kps[j][1]);
                ctx.stroke();
            }

            // Draw joints
            for (let k = 0; k < 17; k++) {
                if (confs && confs[k] < 0.3) continue;
                ctx.beginPath();
                ctx.arc(kps[k][0], kps[k][1], 3, 0, 2 * Math.PI);
                ctx.fillStyle = '#00c8ff';
                ctx.fill();
            }
        }

        // Activity badge (top-right)
        if (activityType && activityType !== 'normal') {
            const badgeColor = this._ACTIVITY_COLORS[activityType] || '#f59e0b';
            const label = activityType.toUpperCase();
            const desc = activity.description || '';
            ctx.font = 'bold 16px Inter, sans-serif';
            const tw = ctx.measureText(label).width + 20;
            const bx = canvas.width - tw - 10, by = 10;
            ctx.fillStyle = badgeColor;
            ctx.globalAlpha = 0.85;
            ctx.fillRect(bx, by, tw, 30);
            ctx.globalAlpha = 1;
            ctx.fillStyle = '#fff';
            ctx.fillText(label, bx + 10, by + 21);
            if (desc) {
                ctx.font = '12px Inter, sans-serif';
                ctx.fillStyle = badgeColor;
                ctx.fillText(desc, bx, by + 48);
            }
        }
    }

    showDesktopNotification(message) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('SurveillX Alert', {
                body: message,
                icon: '/static/images/logo.png'
            });
        }
    }
}

// Export for global access
window.SurveillXApp = SurveillXApp;
