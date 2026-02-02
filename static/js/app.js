/**
 * SurveillX Main Application
 * Handles UI updates and page navigation
 */

class SurveillXApp {
    constructor() {
        this.currentPage = 'dashboard';
        this.socket = null;
        this.refreshInterval = null;
    }

    // Initialize app
    async init() {
        // Check auth
        if (!API.isAuthenticated()) {
            window.location.href = '/templates/login.html';
            return;
        }

        // Setup navigation
        this.setupNavigation();

        // Load initial page
        await this.loadPage('dashboard');

        // Start auto-refresh
        this.startAutoRefresh();

        // Connect WebSocket for live updates
        this.connectSocket();
    }

    // Setup sidebar navigation
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
            logoutBtn.addEventListener('click', () => API.logout());
        }
    }

    // Load page content
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

        // Load page content
        const content = document.getElementById('main-content');
        if (!content) return;

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
        } catch (error) {
            content.innerHTML = `<div class="error-state">Failed to load: ${error.message}</div>`;
        }
    }

    // ============ DASHBOARD ============

    async loadDashboard(container) {
        const data = await API.healthCheck();
        const stats = data.stats || {};

        container.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(99, 102, 241, 0.2);">
                        <i class="fa-solid fa-user-check"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.today_attendance || 0}</div>
                        <div class="stat-label">Today's Attendance</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(34, 197, 94, 0.2);">
                        <i class="fa-solid fa-video"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.active_cameras || 0}</div>
                        <div class="stat-label">Active Cameras</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(239, 68, 68, 0.2);">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.recent_alerts || 0}</div>
                        <div class="stat-label">Recent Alerts</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(251, 191, 36, 0.2);">
                        <i class="fa-solid fa-users"></i>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">${stats.total_students || 0}</div>
                        <div class="stat-label">Total Students</div>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-row">
                <div class="card">
                    <h3>Recent Alerts</h3>
                    <div id="recent-alerts-list" class="list-container">Loading...</div>
                </div>
                
                <div class="card">
                    <h3>Today's Attendance</h3>
                    <div id="recent-attendance-list" class="list-container">Loading...</div>
                </div>
            </div>
        `;

        // Load recent alerts
        this.loadRecentAlerts();
        this.loadRecentAttendance();
    }

    async loadRecentAlerts() {
        try {
            const data = await API.getAlerts({ limit: 5 });
            const container = document.getElementById('recent-alerts-list');

            if (!data.alerts || data.alerts.length === 0) {
                container.innerHTML = '<div class="empty-state">No recent alerts</div>';
                return;
            }

            container.innerHTML = data.alerts.map(alert => `
                <div class="list-item alert-item ${alert.severity}">
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

            if (!data.records || data.records.length === 0) {
                container.innerHTML = '<div class="empty-state">No attendance today</div>';
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
                        <span class="feed-label">Main Camera</span>
                        <span class="feed-status" id="stream-status">
                            <i class="fa-solid fa-circle"></i> Disconnected
                        </span>
                    </div>
                    <div class="feed-container">
                        <canvas id="live-canvas" width="640" height="480"></canvas>
                        <div class="feed-overlay" id="feed-overlay">
                            <i class="fa-solid fa-video-slash"></i>
                            <div>No video stream</div>
                            <div class="hint">Start the streaming client on your laptop</div>
                        </div>
                    </div>
                    <div class="feed-info">
                        <div id="detection-info">Faces: 0 | Activity: Normal</div>
                    </div>
                </div>
                
                <div class="live-sidebar">
                    <div class="card">
                        <h4>Stream Status</h4>
                        <div class="status-item">
                            <span>Connection</span>
                            <span id="ws-status" class="status-badge disconnected">Disconnected</span>
                        </div>
                        <div class="status-item">
                            <span>FPS</span>
                            <span id="fps-counter">0</span>
                        </div>
                        <div class="status-item">
                            <span>Faces Detected</span>
                            <span id="face-count">0</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h4>Live Detections</h4>
                        <div id="live-detections" class="detection-list">
                            <div class="empty-state small">No detections</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
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
                <div id="students-tab-content">Loading...</div>
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
                        </div>
                        <div class="form-group">
                            <label>Roll Number (Optional)</label>
                            <input type="text" id="enroll-roll-no" placeholder="CS2024001">
                        </div>
                        <button class="btn primary full-width" id="generate-btn">Generate Link</button>
                        
                        <div id="link-result" class="link-result" style="display: none;">
                            <div class="qr-code">
                                <img id="qr-image" src="" alt="QR Code">
                            </div>
                            <div class="link-display">
                                <input type="text" id="enrollment-link" readonly>
                                <button class="btn" id="copy-link-btn">Copy</button>
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
                alert('Please enter email');
                return;
            }

            try {
                const data = await API.generateEnrollmentLink(email, rollNo);
                const link = `${window.location.origin}/templates/enroll.html?token=${data.token}`;

                document.getElementById('enrollment-link').value = link;
                document.getElementById('qr-image').src =
                    `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(link)}`;
                document.getElementById('link-result').style.display = 'block';
            } catch (error) {
                alert('Failed to generate link: ' + error.message);
            }
        });

        // Copy link handler
        document.getElementById('copy-link-btn').addEventListener('click', () => {
            const input = document.getElementById('enrollment-link');
            input.select();
            document.execCommand('copy');
            alert('Link copied!');
        });

        // Load initial tab
        this.loadStudentTab('enrolled');
    }

    async loadStudentTab(tab) {
        const content = document.getElementById('students-tab-content');

        if (tab === 'enrolled') {
            try {
                const data = await API.getStudents();

                if (!data.students || data.students.length === 0) {
                    content.innerHTML = '<div class="empty-state">No enrolled students</div>';
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
                                        <button class="btn-icon" title="View"><i class="fa-solid fa-eye"></i></button>
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
                    content.innerHTML = '<div class="empty-state">No pending enrollments</div>';
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
            this.loadStudentTab('pending');
        } catch (error) {
            alert('Failed: ' + error.message);
        }
    }

    async rejectEnrollment(id) {
        const reason = prompt('Reason for rejection:');
        if (!reason) return;
        try {
            await API.rejectEnrollment(id, reason);
            this.loadStudentTab('pending');
        } catch (error) {
            alert('Failed: ' + error.message);
        }
    }

    async deleteStudent(id) {
        if (!confirm('Delete this student?')) return;
        try {
            await API.deleteStudent(id);
            this.loadStudentTab('enrolled');
        } catch (error) {
            alert('Failed: ' + error.message);
        }
    }

    // ============ ATTENDANCE ============

    async loadAttendance(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="date-filter">
                    <input type="date" id="attendance-date" value="${new Date().toISOString().split('T')[0]}">
                    <button class="btn" id="filter-attendance">Filter</button>
                </div>
            </div>
            
            <div class="card">
                <div id="attendance-content">Loading...</div>
            </div>
        `;

        document.getElementById('filter-attendance').addEventListener('click', () => {
            this.loadAttendanceData();
        });

        this.loadAttendanceData();
    }

    async loadAttendanceData() {
        const container = document.getElementById('attendance-content');
        const date = document.getElementById('attendance-date').value;

        try {
            const data = await API.getAttendance({ date });

            if (!data.records || data.records.length === 0) {
                container.innerHTML = '<div class="empty-state">No attendance records for this date</div>';
                return;
            }

            container.innerHTML = `
                <div class="attendance-summary">
                    <span>Total: ${data.records.length} present</span>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Student</th>
                            <th>Roll No</th>
                            <th>Time</th>
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
                    <button class="btn" id="filter-alerts">Filter</button>
                </div>
            </div>
            
            <div class="card">
                <div id="alerts-content">Loading...</div>
            </div>
        `;

        document.getElementById('filter-alerts').addEventListener('click', () => {
            this.loadAlertsData();
        });

        this.loadAlertsData();
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
                container.innerHTML = '<div class="empty-state">No alerts found</div>';
                return;
            }

            container.innerHTML = `
                <div class="alerts-list">
                    ${data.alerts.map(alert => `
                        <div class="alert-card ${alert.severity}">
                            <div class="alert-icon">
                                <i class="fa-solid fa-${this.getAlertIcon(alert.event_type)}"></i>
                            </div>
                            <div class="alert-content">
                                <div class="alert-title">${this.formatEventType(alert.event_type)}</div>
                                <div class="alert-meta">
                                    <span><i class="fa-solid fa-clock"></i> ${this.timeAgo(alert.timestamp)}</span>
                                    <span><i class="fa-solid fa-video"></i> Camera ${alert.camera_id}</span>
                                </div>
                            </div>
                            <div class="alert-actions">
                                <span class="badge ${alert.severity}">${alert.severity}</span>
                                ${alert.clip_path ? `<button class="btn small" onclick="app.playClip(${alert.id})">View Clip</button>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (error) {
            container.innerHTML = `<div class="error-state">Failed: ${error.message}</div>`;
        }
    }

    // ============ SETTINGS ============

    async loadSettings(container) {
        container.innerHTML = `
            <div class="settings-grid">
                <div class="card">
                    <h3>System Status</h3>
                    <div id="system-status">Loading...</div>
                </div>
                
                <div class="card">
                    <h3>Stream Configuration</h3>
                    <div class="form-group">
                        <label>Server WebSocket URL</label>
                        <input type="text" value="ws://${window.location.host}/stream" readonly>
                        <p class="hint">Use this URL in the streaming client</p>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Detection Thresholds</h3>
                    <div class="form-group">
                        <label>Face Recognition Confidence</label>
                        <input type="range" min="50" max="95" value="60" id="face-threshold">
                        <span id="face-threshold-val">60%</span>
                    </div>
                    <div class="form-group">
                        <label>Running Detection Velocity</label>
                        <input type="range" min="1" max="5" step="0.5" value="2.5" id="running-threshold">
                        <span id="running-threshold-val">2.5 m/s</span>
                    </div>
                </div>
            </div>
        `;

        // Load system status
        try {
            const health = await API.healthCheck();
            document.getElementById('system-status').innerHTML = `
                <div class="status-item">
                    <span>Database</span>
                    <span class="status-badge ${health.database === 'connected' ? 'success' : 'error'}">
                        ${health.database}
                    </span>
                </div>
                <div class="status-item">
                    <span>Total Students</span>
                    <span>${health.stats?.total_students || 0}</span>
                </div>
                <div class="status-item">
                    <span>Recent Alerts</span>
                    <span>${health.stats?.recent_alerts || 0}</span>
                </div>
            `;
        } catch (error) {
            document.getElementById('system-status').innerHTML =
                '<div class="error-state">Failed to load status</div>';
        }
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
        return icons[type] || 'exclamation';
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
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            if (this.currentPage === 'dashboard') {
                this.loadRecentAlerts();
                this.loadRecentAttendance();
            }
        }, 30000);
    }

    connectSocket() {
        // WebSocket for live video stream
        if (typeof io !== 'undefined') {
            this.socket = io('/stream', {
                transports: ['websocket']
            });

            this.socket.on('connect', () => {
                const status = document.getElementById('ws-status');
                if (status) {
                    status.textContent = 'Connected';
                    status.className = 'status-badge connected';
                }
            });

            this.socket.on('disconnect', () => {
                const status = document.getElementById('ws-status');
                if (status) {
                    status.textContent = 'Disconnected';
                    status.className = 'status-badge disconnected';
                }
            });

            this.socket.on('frame', (data) => {
                this.displayFrame(data);
            });

            this.socket.on('detection', (data) => {
                this.handleDetection(data);
            });
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
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
        img.src = 'data:image/jpeg;base64,' + data.frame;
    }

    handleDetection(data) {
        // Update face count
        const faceCount = document.getElementById('face-count');
        if (faceCount) faceCount.textContent = data.faces?.length || 0;

        // Update detection info
        const info = document.getElementById('detection-info');
        if (info) {
            info.textContent = `Faces: ${data.faces?.length || 0} | Activity: ${data.activity || 'Normal'}`;
        }
    }

    playClip(alertId) {
        alert('Video clip playback coming soon');
    }
}

// Initialize on page load
const app = new SurveillXApp();
document.addEventListener('DOMContentLoaded', () => app.init());
