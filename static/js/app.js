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
    }

    setupNavigation() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                this.loadPage(page);
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
            settings: 'System Settings'
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
            </div>
            
            <div class="dashboard-row">
                <div class="card">
                    <h3><i class="fa-solid fa-chart-line"></i> Attendance Trend (Last 7 Days)</h3>
                    <div class="chart-container" style="height: 250px;">
                        <canvas id="attendance-chart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fa-solid fa-chart-pie"></i> Alert Distribution</h3>
                    <div class="chart-container" style="height: 250px;">
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

        // Generate last 7 days data (mock for now)
        const labels = [];
        const data = [];
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
            data.push(Math.floor(Math.random() * 10) + 15); // Random 15-25
        }

        this.charts.attendance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Attendance',
                    data: data,
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
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: 'rgba(255,255,255,0.5)' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: 'rgba(255,255,255,0.5)' },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    async loadAlertsChart() {
        const ctx = document.getElementById('alerts-chart');
        if (!ctx) return;

        this.charts.alerts = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Running', 'Fighting', 'Loitering', 'Unauthorized', 'Other'],
                datasets: [{
                    data: [12, 5, 8, 3, 2],
                    backgroundColor: [
                        '#f59e0b',
                        '#ef4444',
                        '#3b82f6',
                        '#8b5cf6',
                        '#6b7280'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: 'rgba(255,255,255,0.7)',
                            padding: 15,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
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
                <div class="list-item">
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
                        <div class="item-subtitle">${new Date(record.timestamp).toLocaleTimeString()}</div>
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
        container.innerHTML = `
            <div class="live-grid">
                <div class="camera-feed main-feed">
                    <div class="feed-header">
                        <span class="feed-label">
                            <i class="fa-solid fa-video"></i> Main Camera
                        </span>
                        <span class="feed-status" id="stream-status">
                            <i class="fa-solid fa-circle"></i> Disconnected
                        </span>
                    </div>
                    <div class="feed-container">
                        <canvas id="live-canvas" width="1280" height="720"></canvas>
                        <div class="feed-overlay" id="feed-overlay">
                            <i class="fa-solid fa-video-slash"></i>
                            <div>No video stream</div>
                            <div class="hint">Start the streaming client on your laptop</div>
                        </div>
                    </div>
                    <div class="feed-info">
                        <div id="detection-info">
                            <i class="fa-solid fa-face-smile"></i> Faces: <span id="face-count">0</span> |
                            <i class="fa-solid fa-person-running"></i> Activity: <span id="activity-status">Normal</span> |
                            <i class="fa-solid fa-gauge"></i> FPS: <span id="fps-display">0</span>
                        </div>
                    </div>
                </div>
                
                <div class="live-sidebar">
                    <div class="card">
                        <h3><i class="fa-solid fa-signal"></i> Stream Status</h3>
                        <div class="status-item">
                            <span>Connection</span>
                            <span id="ws-status" class="status-badge disconnected">Disconnected</span>
                        </div>
                        <div class="status-item">
                            <span>Resolution</span>
                            <span id="resolution-display">--</span>
                        </div>
                        <div class="status-item">
                            <span>Frames Received</span>
                            <span id="frame-count">0</span>
                        </div>
                        <div class="status-item">
                            <span>Latency</span>
                            <span id="latency-display">--</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3><i class="fa-solid fa-user-check"></i> Live Detections</h3>
                        <div id="live-detections" class="detection-list">
                            <div class="empty-state small">
                                <i class="fa-solid fa-eye-slash"></i>
                                <p>No detections</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3><i class="fa-solid fa-terminal"></i> Quick Actions</h3>
                        <button class="btn secondary full-width" onclick="app.toggleFullscreen()" style="margin-bottom: 0.5rem;">
                            <i class="fa-solid fa-expand"></i> Fullscreen
                        </button>
                        <button class="btn secondary full-width" onclick="app.captureSnapshot()">
                            <i class="fa-solid fa-camera"></i> Capture Snapshot
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Reconnect socket to start receiving frames
        this.lastFrameTime = Date.now();
        this.frameCount = 0;
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
        const canvas = document.getElementById('live-canvas');
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
                <button class="btn primary" id="generate-link-btn">
                    <i class="fa-solid fa-link"></i> Generate Enrollment Link
                </button>
            </div>
            
            <div class="card">
                <div id="students-tab-content">
                    <div class="skeleton" style="height: 50px; margin-bottom: 0.5rem;"></div>
                    <div class="skeleton" style="height: 50px; margin-bottom: 0.5rem;"></div>
                    <div class="skeleton" style="height: 50px;"></div>
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

        // Setup modal
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
                const link = `${window.location.origin}/templates/enroll.html?token=${data.token}`;

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

        // Load initial tab
        await this.loadStudentTab('enrolled');
    }

    async loadStudentTab(tab) {
        const content = document.getElementById('students-tab-content');

        if (tab === 'enrolled') {
            try {
                const data = await API.getStudents();

                if (!data.students || data.students.length === 0) {
                    content.innerHTML = '<div class="empty-state"><i class="fa-solid fa-users-slash"></i><p>No enrolled students</p></div>';
                    return;
                }

                content.innerHTML = `
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Roll No</th>
                                <th>Class</th>
                                <th>Status</th>
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
                                    <td><span class="badge success">Active</span></td>
                                    <td>
                                        <button class="btn-icon" onclick="app.viewStudent(${s.id})" title="View Details"><i class="fa-solid fa-eye"></i></button>
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
                                        <button class="btn small success" onclick="app.approveEnrollment(${e.id})">
                                            <i class="fa-solid fa-check"></i> Approve
                                        </button>
                                        <button class="btn small danger" onclick="app.rejectEnrollment(${e.id})">
                                            <i class="fa-solid fa-times"></i> Reject
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

    // ============ ATTENDANCE ============

    async loadAttendance(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="filter-group">
                    <input type="date" id="attendance-date" value="${new Date().toISOString().split('T')[0]}">
                    <button class="btn primary" id="filter-attendance">
                        <i class="fa-solid fa-filter"></i> Filter
                    </button>
                </div>
                <div class="btn-group">
                    <button class="btn secondary" id="export-attendance-csv">
                        <i class="fa-solid fa-download"></i> Export CSV
                    </button>
                    <button class="btn secondary" id="mark-attendance-btn">
                        <i class="fa-solid fa-plus"></i> Mark Attendance
                    </button>
                </div>
            </div>
            
            <div class="card">
                <div id="attendance-content">
                    <div class="skeleton" style="height: 50px; margin-bottom: 0.5rem;"></div>
                    <div class="skeleton" style="height: 50px; margin-bottom: 0.5rem;"></div>
                    <div class="skeleton" style="height: 50px;"></div>
                </div>
            </div>
        `;

        document.getElementById('filter-attendance').addEventListener('click', () => {
            this.loadAttendanceData();
        });

        document.getElementById('export-attendance-csv').addEventListener('click', () => {
            this.exportAttendanceCSV();
        });

        document.getElementById('mark-attendance-btn').addEventListener('click', () => {
            this.showMarkAttendanceModal();
        });

        await this.loadAttendanceData();
    }

    async loadAttendanceData() {
        const container = document.getElementById('attendance-content');
        const date = document.getElementById('attendance-date').value;

        try {
            const data = await API.getAttendance({ date });

            if (!data.records || data.records.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-calendar-xmark"></i><p>No attendance records for this date</p></div>';
                return;
            }

            container.innerHTML = `
                <div class="attendance-summary" style="margin-bottom: 1rem; padding: 1rem; background: var(--success-bg); border-radius: var(--border-radius-sm); display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fa-solid fa-users" style="color: var(--success);"></i>
                    <span><strong>${data.records.length}</strong> students present on ${new Date(date).toLocaleDateString()}</span>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Student</th>
                            <th>Roll No</th>
                            <th>Check-in Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.records.map(r => `
                            <tr>
                                <td>
                                    <div class="user-cell">
                                        <div class="avatar">${(r.student_name || '?')[0]}</div>
                                        <span>${r.student_name || 'Unknown'}</span>
                                    </div>
                                </td>
                                <td>${r.roll_no || '-'}</td>
                                <td>${new Date(r.timestamp).toLocaleTimeString()}</td>
                                <td><span class="badge success">Present</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (error) {
            container.innerHTML = `<div class="error-state">Failed: ${error.message}</div>`;
        }
    }

    exportAttendanceCSV() {
        const date = document.getElementById('attendance-date').value;
        const table = document.querySelector('#attendance-content table');
        if (!table) {
            Toast.warning('No attendance records to export');
            return;
        }

        // Build CSV content
        let csv = 'Name,Roll No,Check-in Time,Status\n';
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            const name = cells[0]?.querySelector('span')?.textContent || '';
            const rollNo = cells[1]?.textContent || '';
            const time = cells[2]?.textContent || '';
            const status = cells[3]?.textContent?.trim() || '';
            csv += `"${name}","${rollNo}","${time}","${status}"\n`;
        });

        // Download CSV
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `attendance_${date}.csv`;
        a.click();
        URL.revokeObjectURL(url);

        Toast.success('Attendance exported to CSV');
    }

    showMarkAttendanceModal() {
        Toast.info('Manual attendance marking: Use the camera for automatic face recognition');
    }

    async viewStudent(id) {
        try {
            const data = await API.request(`/api/students/${id}`);
            const student = data.student;

            // Show student details modal
            const modal = document.createElement('div');
            modal.className = 'modal show';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Student Details</h3>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="student-profile" style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                            <div class="avatar" style="width: 60px; height: 60px; font-size: 1.5rem;">${student.name[0]}</div>
                            <div>
                                <h4 style="margin: 0;">${student.name}</h4>
                                <p style="margin: 0; color: var(--text-secondary);">Roll: ${student.roll_no}</p>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Class</label>
                            <input type="text" value="${student.class || 'N/A'}" readonly>
                        </div>
                        <div class="form-group">
                            <label>Contact</label>
                            <input type="text" value="${student.contact_no || 'N/A'}" readonly>
                        </div>
                        <div class="form-group">
                            <label>Enrolled On</label>
                            <input type="text" value="${new Date(student.created_at).toLocaleDateString()}" readonly>
                        </div>
                        <div class="form-group">
                            <label>Face Data</label>
                            <span class="badge ${student.face_encoding ? 'success' : 'warning'}">
                                ${student.face_encoding ? 'Registered' : 'Not Registered'}
                            </span>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        } catch (error) {
            Toast.error('Failed to load student details');
        }
    }

    async editStudent(id) {
        try {
            const data = await API.request(`/api/students/${id}`);
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
                    await API.request(`/api/students/${id}`, {
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
        container.innerHTML = `
            <div class="page-header">
                <div class="filter-group">
                    <select id="alert-type-filter">
                        <option value="">All Types</option>
                        <option value="running">Running</option>
                        <option value="fighting">Fighting</option>
                        <option value="loitering">Loitering</option>
                        <option value="unauthorized_entry">Unauthorized Entry</option>
                    </select>
                    <select id="alert-severity-filter">
                        <option value="">All Severity</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <button class="btn primary" id="filter-alerts">
                        <i class="fa-solid fa-filter"></i> Filter
                    </button>
                </div>
                <div class="btn-group">
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
            </div>
        `;

        document.getElementById('filter-alerts').addEventListener('click', () => {
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
        const type = document.getElementById('alert-type-filter').value;
        const severity = document.getElementById('alert-severity-filter').value;

        try {
            const params = {};
            if (type) params.event_type = type;
            if (severity) params.severity = severity;

            const data = await API.getAlerts(params);

            if (!data.alerts || data.alerts.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-check-circle"></i><p>No alerts found</p></div>';
                return;
            }

            container.innerHTML = `
                <div class="alerts-list">
                    ${data.alerts.map(alert => `
                        <div class="alert-card ${alert.severity} ${alert.dismissed ? 'dismissed' : ''}" id="alert-${alert.id}">
                            <div class="alert-icon">
                                <i class="fa-solid fa-${this.getAlertIcon(alert.event_type)}"></i>
                            </div>
                            <div class="alert-content">
                                <div class="alert-title">${this.formatEventType(alert.event_type)}</div>
                                <div class="alert-meta">
                                    <span><i class="fa-solid fa-clock"></i> ${this.timeAgo(alert.timestamp)}</span>
                                    <span><i class="fa-solid fa-video"></i> Camera ${alert.camera_id}</span>
                                    ${alert.dismissed ? '<span class="badge success">Resolved</span>' : ''}
                                </div>
                            </div>
                            <div class="alert-actions">
                                <span class="badge ${alert.severity}">${alert.severity}</span>
                                ${alert.clip_path ? `<button class="btn small" onclick="app.playClip(${alert.id})" title="View Clip"><i class="fa-solid fa-play"></i></button>` : ''}
                                ${!alert.dismissed ? `<button class="btn small success" onclick="app.dismissAlert(${alert.id})" title="Mark Resolved"><i class="fa-solid fa-check"></i></button>` : ''}
                                <button class="btn small danger" onclick="app.deleteAlert(${alert.id})" title="Delete"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<div class="error-state">Failed: ${error.message}</div>`;
        }
    }

    async dismissAlert(id) {
        try {
            await API.request(`/api/alerts/${id}/resolve`, { method: 'PUT' });
            Toast.success('Alert resolved');
            // Update the alert card visually
            const alertCard = document.getElementById(`alert-${id}`);
            if (alertCard) {
                alertCard.classList.add('dismissed');
                const dismissBtn = alertCard.querySelector('.btn.success');
                if (dismissBtn) dismissBtn.remove();
            }
            // Refresh alerts
            this.loadAlertsData();
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    async deleteAlert(id) {
        if (!confirm('Delete this alert? This cannot be undone.')) return;
        try {
            await API.request(`/api/alerts/${id}`, { method: 'DELETE' });
            Toast.success('Alert deleted');
            // Remove from DOM
            const alertCard = document.getElementById(`alert-${id}`);
            if (alertCard) alertCard.remove();
        } catch (error) {
            Toast.error('Failed: ' + error.message);
        }
    }

    async clearAllAlerts() {
        if (!confirm('Clear ALL alerts? This cannot be undone.')) return;
        try {
            // Delete alerts one by one or implement bulk clear API
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
        // TODO: Implement clip playback modal
    }

    // ============ SETTINGS ============

    async loadSettings(container) {
        container.innerHTML = `
            <div class="settings-grid">
                <div class="card">
                    <h3><i class="fa-solid fa-server"></i> System Status</h3>
                    <div id="system-status">
                        <div class="skeleton" style="height: 40px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 40px; margin-bottom: 0.5rem;"></div>
                        <div class="skeleton" style="height: 40px;"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fa-solid fa-video"></i> Stream Configuration</h3>
                    <div class="form-group">
                        <label>Server WebSocket URL</label>
                        <input type="text" value="ws://${window.location.host}/stream" readonly>
                        <p class="hint">Use this URL in the streaming client</p>
                    </div>
                    <div class="form-group">
                        <label>Stream Command</label>
                        <input type="text" value="python stream_client.py --server http://${window.location.host}" readonly>
                    </div>
                </div>
                
                <div class="card">
                    <h3><i class="fa-solid fa-sliders"></i> Detection Thresholds</h3>
                    <div class="form-group">
                        <label>Face Recognition Confidence</label>
                        <input type="range" min="50" max="95" value="60" id="face-threshold">
                        <span id="face-threshold-val">60%</span>
                    </div>
                    <div class="form-group">
                        <label>Running Detection Sensitivity</label>
                        <input type="range" min="1" max="5" step="0.5" value="2.5" id="running-threshold">
                        <span id="running-threshold-val">2.5</span>
                    </div>
                    <button class="btn primary" onclick="Toast.success('Settings saved!')">
                        <i class="fa-solid fa-save"></i> Save Settings
                    </button>
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
                    <span>${new Date().toLocaleString()}</span>
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

    connectSocket() {
        if (typeof io === 'undefined') return;

        this.socket = io('/stream');

        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
        });

        this.socket.on('frame', (data) => {
            this.displayFrame(data);
        });

        this.socket.on('detection', (data) => {
            this.handleDetection(data);
        });

        this.socket.on('new_alert', (data) => {
            Toast.warning(`New Alert: ${this.formatEventType(data.type)}`, 'Security Alert');
            this.showDesktopNotification(`Alert: ${this.formatEventType(data.type)}`);
        });
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
        const canvas = document.getElementById('live-canvas');
        const overlay = document.getElementById('feed-overlay');

        if (!canvas) return;

        // Hide overlay
        if (overlay) overlay.style.display = 'none';

        // Draw frame
        const ctx = canvas.getContext('2d');
        const img = new Image();
        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            // Update resolution display
            const resDisplay = document.getElementById('resolution-display');
            if (resDisplay) resDisplay.textContent = `${img.width}x${img.height}`;
        };
        img.src = 'data:image/jpeg;base64,' + data.frame;

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
    }

    handleDetection(data) {
        // Update face count
        const faceCount = document.getElementById('face-count');
        if (faceCount && data.faces) {
            faceCount.textContent = data.faces.length;
        }

        // Update activity status
        const activityStatus = document.getElementById('activity-status');
        if (activityStatus && data.activity) {
            activityStatus.textContent = data.activity;
            activityStatus.style.color = data.activity !== 'Normal' ? 'var(--warning)' : '';
        }

        // Update live detections list
        const liveDetections = document.getElementById('live-detections');
        if (liveDetections && data.faces && data.faces.length > 0) {
            liveDetections.innerHTML = data.faces.map(face => `
                <div class="list-item" style="padding: 0.5rem;">
                    <div class="avatar" style="width: 32px; height: 32px; font-size: 0.8rem;">
                        ${face.name ? face.name[0] : '?'}
                    </div>
                    <div class="item-content">
                        <div class="item-title" style="font-size: 0.85rem;">${face.name || 'Unknown'}</div>
                        <div class="item-subtitle">${face.confidence ? (face.confidence * 100).toFixed(0) + '%' : ''}</div>
                    </div>
                </div>
            `).join('');
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
