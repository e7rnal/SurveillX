document.addEventListener('DOMContentLoaded', () => {
    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const viewContainer = document.getElementById('view-container');
    const pageTitle = document.getElementById('page-title');

    // Routing Layout
    const routes = {
        'dashboard': { title: 'Dashboard Overview' },
        'live': { title: 'Live Monitor' },
        'attendance': { title: 'Attendance Logs' },
        'alerts': { title: 'Security Alerts' },
        'students': { title: 'Student Database' },
        'settings': { title: 'System Settings' }
    };

    /**
     * MOCK DATA TEMPLATES
     * Stored as strings to allow the application to run without a server (file:// protocol)
     */
    const templates = {
        dashboard: `
            <div class="dashboard-grid">
                <div class="stat-card">
                    <div class="stat-header">
                        <span>Daily Attendance</span>
                        <i class="fa-solid fa-users text-accent"></i>
                    </div>
                    <div class="stat-value">124</div>
                    <div class="stat-footer">
                        <i class="fa-solid fa-arrow-up"></i>
                        <span>12% vs yesterday</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-header">
                        <span>Active Cameras</span>
                        <i class="fa-solid fa-video text-success"></i>
                    </div>
                    <div class="stat-value">4/4</div>
                    <div class="stat-footer">
                        <span style="color:var(--text-secondary)">All systems normal</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-header">
                        <span>Security Alerts</span>
                        <i class="fa-solid fa-triangle-exclamation text-warning"></i>
                    </div>
                    <div class="stat-value">3</div>
                    <div class="stat-footer negative">
                        <i class="fa-solid fa-arrow-up"></i>
                        <span>New (Running detected)</span>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-header">
                        <span>System Load</span>
                        <i class="fa-solid fa-microchip text-accent"></i>
                    </div>
                    <div class="stat-value">32%</div>
                    <div class="stat-footer">
                        <span>GPU: 45% | vRAM: 16GB</span>
                    </div>
                </div>
            </div>

            <div class="charts-row">
                <div class="chart-container">
                    <h3 class="section-title">Attendance Trends (Weekly)</h3>
                    <canvas id="attendanceChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="section-title">Alert Distribution</h3>
                    <canvas id="alertsChart"></canvas>
                </div>
            </div>
        `,
        live: `
            <div class="live-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 1.5rem;">
                <!-- Camera Feed Card 1 (MAIN STREAM - Default Camera) -->
                <div class="camera-card" id="main-camera-card" 
                    style="background: var(--bg-card); border-radius: 1rem; overflow: hidden; border: var(--glass-border); grid-column: span 2;">
                    <div class="cam-header"
                        style="padding: 1rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div class="cam-info">
                            <i class="fa-solid fa-circle text-success" id="cam1-status" style="font-size: 0.5rem; margin-right: 0.5rem; animation: pulse 1s infinite;"></i>
                            <span style="font-weight: 500;">Entrance Gate - MAIN AI FEED</span>
                        </div>
                        <div>
                            <span style="font-size: 0.75rem; color: var(--text-secondary); margin-right: 1rem;">1080p | 60fps</span>
                            <span style="background: var(--accent); color: white; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: bold;">AI ACTIVE</span>
                        </div>
                    </div>
                    <div class="cam-feed" id="main-feed"
                        style="aspect-ratio: 16/9; background: #000; position: relative; overflow: hidden;">
                        
                        <!-- Loading State -->
                        <div id="cam1-loading" style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 5;">
                            <i class="fa-solid fa-video" style="font-size: 3rem; color: rgba(255,255,255,0.3); margin-bottom: 1rem;"></i>
                            <p style="color: rgba(255,255,255,0.6);">Initializing camera...</p>
                        </div>

                        <!-- Video Element -->
                        <video id="camera-stream" autoplay playsinline muted
                            style="width: 100%; height: 100%; object-fit: cover; display: none;">
                        </video>

                        <!-- AI Detection Overlay -->
                        <div id="ai-overlay" style="position: absolute; inset: 0; pointer-events: none; display: none;">
                            <!-- Scanning Line Animation -->
                            <div class="scan-line"></div>
                            
                            <!-- Face Detection Box Simulation -->
                            <div class="face-box" style="top: 30%; left: 40%; width: 100px; height: 100px;">
                                <span class="face-tag">Processing...</span>
                            </div>
                        </div>
                        
                        <!-- Overlay Info -->
                        <div style="position: absolute; bottom: 1rem; left: 1rem; color: rgba(255,255,255,0.7); font-family: monospace; font-size: 0.8rem; z-index: 10;">
                            DATETIME: <span id="cam-time">--:--:--</span> <br>
                            CAM_ID: 8847-ENT-01
                        </div>

                        <!-- LIVE Badge -->
                        <div class="overlay"
                            style="position: absolute; top: 1rem; right: 1rem; background: rgba(255,0,0,0.8); padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.75rem; font-weight: bold; z-index: 10;">
                            ● LIVE
                        </div>
                    </div>
                    <div class="cam-footer" style="padding: 1rem; display: flex; gap: 0.5rem; justify-content: space-between; align-items: center;">
                        <div style="display: flex; gap:0.5rem;">
                            <button id="btn-toggle-camera" style="padding: 0.5rem 1rem; background: var(--accent); color: white; border: none; border-radius: 0.5rem; cursor: pointer;">
                                <i class="fa-solid fa-play"></i> Start
                            </button>
                            <button style="padding: 0.5rem 1rem; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 0.5rem; cursor: pointer;">
                                <i class="fa-solid fa-camera"></i> Snapshot
                            </button>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary);">
                            Latency: <span id="latency">--</span>ms
                        </div>
                    </div>
                </div>

                <!-- Camera Feed Card 2 (Secondary - Static Demo) -->
                <div class="camera-card"
                    style="background: var(--bg-card); border-radius: 1rem; overflow: hidden; border: var(--glass-border);">
                    <div class="cam-header"
                        style="padding: 1rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div class="cam-info">
                            <i class="fa-solid fa-circle text-success" style="font-size: 0.5rem; margin-right: 0.5rem;"></i>
                            <span style="font-weight: 500;">Corridor A</span>
                        </div>
                        <span style="font-size: 0.75rem; color: var(--text-secondary);">720p</span>
                    </div>
                    <div class="cam-feed"
                        style="aspect-ratio: 16/9; background: #000; position: relative; display: flex; align-items: center; justify-content: center;">
                        <img src="https://images.unsplash.com/photo-1563205764-6e1b21f36453?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" 
                            style="width: 100%; height: 100%; object-fit: cover; opacity: 0.5;" alt="Corridor">
                        <div class="overlay" style="position: absolute; top: 1rem; right: 1rem; background: rgba(0,0,0,0.6); padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.75rem;">LIVE</div>
                    </div>
                </div>

                <!-- Camera Feed Card 3 (Secondary - Static Demo) -->
                <div class="camera-card"
                    style="background: var(--bg-card); border-radius: 1rem; overflow: hidden; border: var(--glass-border);">
                    <div class="cam-header"
                        style="padding: 1rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div class="cam-info">
                            <i class="fa-solid fa-circle text-success" style="font-size: 0.5rem; margin-right: 0.5rem;"></i>
                            <span style="font-weight: 500;">Library Hall</span>
                        </div>
                        <span style="font-size: 0.75rem; color: var(--text-secondary);">720p</span>
                    </div>
                    <div class="cam-feed"
                        style="aspect-ratio: 16/9; background: #000; position: relative; display: flex; align-items: center; justify-content: center;">
                        <img src="https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" 
                            style="width: 100%; height: 100%; object-fit: cover; opacity: 0.5;" alt="Library">
                        <div class="overlay" style="position: absolute; top: 1rem; right: 1rem; background: rgba(0,0,0,0.6); padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.75rem;">LIVE</div>
                    </div>
                </div>
            </div>

            <style>
                .scan-line {
                    position: absolute;
                    width: 100%;
                    height: 2px;
                    background: rgba(59, 130, 246, 0.8);
                    box-shadow: 0 0 4px rgba(59, 130, 246, 0.8);
                    top: 0;
                    left: 0;
                    animation: scan 3s linear infinite;
                    z-index: 10;
                }
                
                @keyframes scan {
                    0% { top: 0%; opacity: 0; }
                    10% { opacity: 1; }
                    90% { opacity: 1; }
                    100% { top: 100%; opacity: 0; }
                }

                .face-box {
                    position: absolute;
                    border: 2px solid var(--accent);
                    box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
                    z-index: 5;
                    animation: float-box 5s ease-in-out infinite alternate;
                }

                .face-tag {
                    position: absolute;
                    top: -20px;
                    left: 0;
                    background: var(--accent);
                    color: white;
                    font-size: 0.7rem;
                    padding: 2px 4px;
                    border-radius: 2px;
                }

                @keyframes float-box {
                    0% { transform: translate(0, 0); }
                    33% { transform: translate(20px, 15px); }
                    66% { transform: translate(-10px, 30px); }
                    100% { transform: translate(5px, -10px); }
                }

                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.4; }
                    100% { opacity: 1; }
                }
            </style>
        `,
        attendance: `
            <div class="content-header" style="margin-bottom: 2rem;">
                <h2 style="font-size: 1.25rem;">Attendance Logs</h2>
                <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                    <div class="search-box" style="background: var(--bg-card); border: 1px solid rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 0.5rem; display: flex; align-items: center; gap: 0.5rem; flex: 1;">
                        <i class="fa-solid fa-search" style="color: var(--text-secondary);"></i>
                        <input type="text" id="search-attendance" placeholder="Search by name or roll no..." style="background: none; border: none; color: white; outline: none; width: 100%;">
                    </div>
                    <input type="date" id="date-attendance" style="background: var(--bg-card); border: 1px solid rgba(255,255,255,0.1); padding: 0.5rem; border-radius: 0.5rem; color: white; color-scheme: dark;">
                    <button id="btn-export-csv" class="btn-export" style="background: var(--accent); color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer;">
                        <i class="fa-solid fa-download"></i> Export CSV
                    </button>
                </div>
            </div>

            <div class="table-container" style="background: var(--bg-card); border-radius: 1rem; border: var(--glass-border); overflow: hidden;">
                <table style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text-secondary); font-size: 0.85rem;">
                            <th style="padding: 1rem 2rem;">Time</th>
                            <th style="padding: 1rem;">Student Name</th>
                            <th style="padding: 1rem;">Roll No</th>
                            <th style="padding: 1rem;">Class</th>
                            <th style="padding: 1rem;">Captured via</th>
                            <th style="padding: 1rem;">Status</th>
                        </tr>
                    </thead>
                    <tbody id="attendance-table-body">
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 1rem 2rem; color: var(--text-secondary);">09:45 AM</td>
                            <td style="padding: 1rem; font-weight: 500;">Vishnu Jadhav</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">52</td>
                            <td style="padding: 1rem;">BCA - III</td>
                            <td style="padding: 1rem;"><i class="fa-solid fa-video"></i> CAM-01</td>
                            <td style="padding: 1rem;"><span style="color: var(--success);"><i class="fa-solid fa-check-circle"></i> Present</span></td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 1rem 2rem; color: var(--text-secondary);">09:42 AM</td>
                            <td style="padding: 1rem; font-weight: 500;">Rohan Sharma</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">45</td>
                            <td style="padding: 1rem;">BCA - III</td>
                            <td style="padding: 1rem;"><i class="fa-solid fa-video"></i> CAM-01</td>
                            <td style="padding: 1rem;"><span style="color: var(--success);"><i class="fa-solid fa-check-circle"></i> Present</span></td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 1rem 2rem; color: var(--text-secondary);">09:38 AM</td>
                            <td style="padding: 1rem; font-weight: 500;">Priya Singh</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">12</td>
                            <td style="padding: 1rem;">BCA - II</td>
                            <td style="padding: 1rem;"><i class="fa-solid fa-video"></i> CAM-02</td>
                            <td style="padding: 1rem;"><span style="color: var(--success);"><i class="fa-solid fa-check-circle"></i> Present</span></td>
                        </tr>
                        <tr>
                            <td style="padding: 1rem 2rem; color: var(--text-secondary);">09:30 AM</td>
                            <td style="padding: 1rem; font-weight: 500;">Amit Kumar</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">08</td>
                            <td style="padding: 1rem;">BCA - III</td>
                            <td style="padding: 1rem;"><i class="fa-solid fa-video"></i> CAM-01</td>
                            <td style="padding: 1rem;"><span style="color: var(--warning);"><i class="fa-solid fa-clock"></i> Late</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `,
        alerts: `
            <div class="content-header" style="margin-bottom: 2rem;">
                <h2 style="font-size: 1.25rem;">Security Alerts & Logs</h2>
                <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                    <select id="alert-filter" style="background: var(--bg-card); border: 1px solid rgba(255,255,255,0.1); padding: 0.5rem; border-radius: 0.5rem; color: white;">
                        <option value="all">All Severity</option>
                        <option value="critical">Critical</option>
                        <option value="warning">Warning</option>
                        <option value="info">Info</option>
                    </select>
                    <button id="btn-clear-alerts" class="btn-clear" style="background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer;">
                        <i class="fa-solid fa-trash"></i> Clear All
                    </button>
                </div>
            </div>

            <div id="alerts-container" class="alerts-container" style="display: flex; flex-direction: column; gap: 1rem;">
                <div class="alert-item" data-severity="critical" style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--danger); padding: 1rem; border-radius: 0.5rem; display: flex; align-items: flex-start; gap: 1rem;">
                    <div class="alert-icon" style="background: var(--danger); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <i class="fa-solid fa-person-running"></i>
                    </div>
                    <div class="alert-content" style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                            <h3 style="margin: 0; font-size: 1rem; font-weight: 600;">Suspicious Activity Detected</h3>
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">2 mins ago</span>
                        </div>
                        <p style="margin: 0; font-size: 0.9rem; color: var(--text-primary);">Rapid movement detected in Corridor B during class hours.</p>
                        <div style="margin-top: 0.5rem;">
                            <button style="font-size: 0.8rem; background: #1e293b; color: white; border: none; padding: 0.25rem 0.75rem; border-radius: 0.25rem; cursor: pointer;">View Clip</button>
                            <button onclick="this.closest('.alert-item').remove()" style="font-size: 0.8rem; background: none; color: var(--text-secondary); border: none; padding: 0.25rem 0.75rem; cursor: pointer;">Dismiss</button>
                        </div>
                    </div>
                </div>

                <div class="alert-item" data-severity="warning" style="background: rgba(245, 158, 11, 0.1); border-left: 4px solid var(--warning); padding: 1rem; border-radius: 0.5rem; display: flex; align-items: flex-start; gap: 1rem;">
                    <div class="alert-icon" style="background: var(--warning); color: black; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <i class="fa-solid fa-eye-slash"></i>
                    </div>
                    <div class="alert-content" style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                            <h3 style="margin: 0; font-size: 1rem; font-weight: 600;">Camera Obstructed</h3>
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">15 mins ago</span>
                        </div>
                        <p style="margin: 0; font-size: 0.9rem; color: var(--text-primary);">Camera 04 (Library) view is partially blocked.</p>
                         <div style="margin-top: 0.5rem;">
                             <button onclick="this.closest('.alert-item').remove()" style="font-size: 0.8rem; background: none; color: var(--text-secondary); border: none; padding: 0.25rem 0.75rem; cursor: pointer;">Dismiss</button>
                        </div>
                    </div>
                </div>
            </div>
        `,
        students: `
            <div class="content-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <h2 style="margin: 0; font-size: 1.25rem;">Student Database</h2>
                    <div style="background: var(--bg-card); padding: 0.25rem; border-radius: 0.5rem; border: var(--glass-border); display: flex;">
                        <button class="tab-btn active" style="background: var(--accent); color: white; border: none; padding: 0.5rem 1rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.85rem;">Active (124)</button>
                        <button class="tab-btn" style="background: transparent; color: var(--text-secondary); border: none; padding: 0.5rem 1rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.85rem;">Pending Requests <span style="background: var(--danger); color: white; padding: 0 0.4rem; border-radius: 1rem; font-size: 0.7rem;">3</span></button>
                    </div>
                </div>
                <div style="display: flex; gap: 1rem;">
                    <button id="btn-qr" style="background: #334155; color: white; border: var(--glass-border); padding: 0.75rem 1rem; border-radius: 0.5rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s;">
                        <i class="fa-solid fa-qrcode"></i> Registration Link
                    </button>
                    <button id="btn-manual-add" class="btn-primary" style="background: var(--accent); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 0.5rem; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fa-solid fa-plus"></i> Manual Add
                    </button>
                </div>
            </div>

            <!-- QR Code Panel (Enhanced) -->
            <div id="qr-panel"
                style="display: none; margin-bottom: 2rem; background: var(--bg-card); padding: 2rem; border-radius: 1rem; border: 1px solid var(--accent); text-align: center;">
                <h3 style="margin-bottom: 1.5rem; font-size: 1.2rem;"><i class="fa-solid fa-qrcode" style="color: var(--accent); margin-right: 0.5rem;"></i>Student Registration Link</h3>
                
                <div style="background: white; padding: 1.5rem; border-radius: 0.75rem; display: inline-block; margin-bottom: 1.5rem;">
                    <img id="qr-code-img" src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://forms.gle/PLACEHOLDER_FORM_ID" 
                         alt="QR Code" style="display: block;">
                </div>
                
                <div style="background: rgba(59, 130, 246, 0.1); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 0.5rem;">Google Form URL:</p>
                    <p id="reg-url" style="margin: 0; color: var(--accent); font-family: monospace; font-size: 0.95rem; word-break: break-all;">https://forms.gle/PLACEHOLDER_FORM_ID</p>
                </div>
                
                <button id="btn-copy-url" style="background: var(--accent); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 0.5rem; cursor: pointer; font-weight: 500;">
                    <i class="fa-solid fa-copy"></i> Copy Link
                </button>
            </div>

            <!-- Manual Add Student Modal -->
            <div id="manual-add-modal" 
                style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
                <div style="background: var(--bg-card); border-radius: 1rem; border: var(--glass-border); max-width: 600px; width: 90%; max-height: 90vh; overflow-y: auto; position: relative;">
                    
                    <!-- Modal Header -->
                    <div style="padding: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; background: var(--bg-card); z-index: 10;">
                        <h3 style="margin: 0; font-size: 1.25rem;"><i class="fa-solid fa-user-plus" style="color: var(--accent); margin-right: 0.5rem;"></i>Add New Student</h3>
                        <button id="btn-close-modal" style="background: none; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 0.25rem; transition: all 0.2s;">
                            <i class="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                    
                    <!-- Modal Body -->
                    <form id="add-student-form" style="padding: 2rem;">
                        
                        <!-- Photo Upload Section -->
                        <div style="text-align: center; margin-bottom: 2rem;">
                            <div id="photo-preview" style="width: 120px; height: 120px; margin: 0 auto 1rem; border-radius: 50%; background: #334155; display: flex; align-items: center; justify-content: center; overflow: hidden; border: 3px solid var(--accent);">
                                <i class="fa-solid fa-camera" style="font-size: 2.5rem; color: rgba(255,255,255,0.3);"></i>
                                <img id="preview-img" src="" alt="Preview" style="display: none; width: 100%; height: 100%; object-fit: cover;">
                            </div>
                            <input type="file" id="student-photo" accept="image/*" style="display: none;">
                            <button type="button" id="btn-upload-photo" style="background: rgba(59, 130, 246, 0.1); border: 1px solid var(--accent); color: var(--accent); padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.9rem;">
                                <i class="fa-solid fa-upload"></i> Upload Photo
                            </button>
                        </div>
                        
                        <!-- Form Fields -->
                        <div style="display: flex; flex-direction: column; gap: 1.25rem;">
                            
                            <!-- Student Name -->
                            <div>
                                <label style="display: block; margin-bottom: 0.5rem; color: var(--text-primary); font-weight: 500; font-size: 0.9rem;">
                                    <i class="fa-solid fa-user" style="color: var(--accent); margin-right: 0.25rem;"></i> Student Name *
                                </label>
                                <input type="text" id="input-name" required
                                    style="width: 100%; padding: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 0.5rem; color: white; font-size: 0.95rem; outline: none; transition: all 0.2s;"
                                    placeholder="Enter full name">
                            </div>
                            
                            <!-- Roll Number -->
                            <div>
                                <label style="display: block; margin-bottom: 0.5rem; color: var(--text-primary); font-weight: 500; font-size: 0.9rem;">
                                    <i class="fa-solid fa-hashtag" style="color: var(--accent); margin-right: 0.25rem;"></i> Roll Number *
                                </label>
                                <input type="text" id="input-roll" required
                                    style="width: 100%; padding: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 0.5rem; color: white; font-size: 0.95rem; outline: none; transition: all 0.2s;"
                                    placeholder="Enter roll number">
                            </div>
                            
                            <!-- Class/Year -->
                            <div>
                                <label style="display: block; margin-bottom: 0.5rem; color: var(--text-primary); font-weight: 500; font-size: 0.9rem;">
                                    <i class="fa-solid fa-graduation-cap" style="color: var(--accent); margin-right: 0.25rem;"></i> Class *
                                </label>
                                <select id="input-class" required
                                    style="width: 100%; padding: 0.75rem; background: #334155; border: 1px solid rgba(255,255,255,0.1); border-radius: 0.5rem; color: white; font-size: 0.95rem; outline: none; cursor: pointer;">
                                    <option value="" style="background: #334155; color: #94a3b8;">Select Class</option>
                                    <option value="BCA - I" style="background: #334155; color: white;">BCA - I</option>
                                    <option value="BCA - II" style="background: #334155; color: white;">BCA - II</option>
                                    <option value="BCA - III" style="background: #334155; color: white;">BCA - III</option>
                                    <option value="MCA - I" style="background: #334155; color: white;">MCA - I</option>
                                    <option value="MCA - II" style="background: #334155; color: white;">MCA - II</option>
                                </select>
                            </div>
                            
                            <!-- Email (Optional) -->
                            <div>
                                <label style="display: block; margin-bottom: 0.5rem; color: var(--text-primary); font-weight: 500; font-size: 0.9rem;">
                                    <i class="fa-solid fa-envelope" style="color: var(--accent); margin-right: 0.25rem;"></i> Email
                                </label>
                                <input type="email" id="input-email"
                                    style="width: 100%; padding: 0.75rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 0.5rem; color: white; font-size: 0.95rem; outline: none; transition: all 0.2s;"
                                    placeholder="student@example.com">
                            </div>
                        </div>
                        
                        <!-- Form Actions -->
                        <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: flex-end;">
                            <button type="button" id="btn-cancel-form" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: var(--text-secondary); padding: 0.75rem 1.5rem; border-radius: 0.5rem; cursor: pointer; font-weight: 500;">
                                Cancel
                            </button>
                            <button type="submit" style="background: var(--accent); color: white; border: none; padding: 0.75rem 2rem; border-radius: 0.5rem; cursor: pointer; font-weight: 600;">
                                <i class="fa-solid fa-check"></i> Add Student
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="table-container" style="background: var(--bg-card); border-radius: 1rem; border: var(--glass-border); overflow: hidden;">
                <table id="table-active" style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text-secondary); font-size: 0.85rem;">
                            <th style="padding: 1.5rem 2rem;">Student Name</th>
                            <th style="padding: 1.5rem;">Roll No</th>
                            <th style="padding: 1.5rem;">Class</th>
                            <th style="padding: 1.5rem;">Status</th>
                            <th style="padding: 1.5rem;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                    <tbody id="students-table-body">
                        <!-- Populated by JS -->
                    </tbody>
                    </tbody>
                </table>

                <table id="table-pending" style="width: 100%; border-collapse: collapse; text-align: left; display: none;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text-secondary); font-size: 0.85rem;">
                            <th style="padding: 1.5rem 2rem;">Student Name</th>
                            <th style="padding: 1.5rem;">Roll No</th>
                            <th style="padding: 1.5rem;">Class</th>
                            <th style="padding: 1.5rem;">Request Time</th>
                            <th style="padding: 1.5rem;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem;">
                                <div style="width: 36px; height: 36px; background: #334155; border-radius: 50%;"></div>
                                <span>Rahul Verma</span>
                            </td>
                            <td style="padding: 1rem; color: var(--text-secondary);">--</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">BCA - I</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">10 mins ago</td>
                            <td style="padding: 1rem; display: flex; gap: 0.5rem;">
                                <button class="btn-approve" style="background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                                    <i class="fa-solid fa-check"></i>
                                </button>
                                <button class="btn-reject" style="background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                                    <i class="fa-solid fa-xmark"></i>
                                </button>
                            </td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem;">
                                <div style="width: 36px; height: 36px; background: #334155; border-radius: 50%;"></div>
                                <span>Sneha Gupta</span>
                            </td>
                            <td style="padding: 1rem; color: var(--text-secondary);">21</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">MCA - I</td>
                            <td style="padding: 1rem; color: var(--text-secondary);">2 hrs ago</td>
                            <td style="padding: 1rem; display: flex; gap: 0.5rem;">
                                <button class="btn-approve" style="background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                                    <i class="fa-solid fa-check"></i>
                                </button>
                                <button class="btn-reject" style="background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                                    <i class="fa-solid fa-xmark"></i>
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `,
        settings: `
            <div class="content-header" style="margin-bottom: 2rem;">
                <h2 style="font-size: 1.25rem;">System Settings</h2>
            </div>
            <div class="settings-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
                <!-- System Card -->
                <div class="setting-card" style="background: var(--bg-card); padding: 1.5rem; border-radius: 1rem; border: var(--glass-border);">
                    <h3 style="margin-top: 0; margin-bottom: 1.5rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fa-solid fa-server text-accent"></i> System Control
                    </h3>
                    <div class="setting-item" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <div>
                            <span style="display: block; font-weight: 500;">System Active</span>
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">Enable entire surveillance system</span>
                        </div>
                        <label class="switch" style="position: relative; display: inline-block; width: 40px; height: 24px;">
                            <input type="checkbox" id="system-active-toggle" checked style="opacity: 0; width: 0; height: 0; accent-color: var(--success);">
                            <span class="slider" style="position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .4s; border-radius: 24px;"></span>
                            <span class="knob" style="position: absolute; content: ''; height: 16px; width: 16px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; transform: translateX(16px); background-color: var(--success);"></span>
                        </label>
                    </div>
                </div>
            </div>
            <div style="margin-top: 2rem; text-align: right;">
                <button id="btn-save-settings" style="background: var(--accent); color: white; border: none; padding: 0.75rem 2rem; border-radius: 0.5rem; font-weight: 600; cursor: pointer;">Save Changes</button>
            </div>
        `
    };

    const loadView = (viewName) => {
        const route = routes[viewName];
        if (!route) return;

        pageTitle.textContent = route.title;

        // Update Active State
        navItems.forEach(item => {
            if (item.dataset.view === viewName) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Load Content
        if (templates[viewName]) {
            viewContainer.innerHTML = templates[viewName];

            // Post-Load Initializers
            if (viewName === 'dashboard') initCharts();
            if (viewName === 'live') initLive();
            if (viewName === 'students') initStudents();
            if (viewName === 'attendance') initAttendance();
            if (viewName === 'alerts') initAlerts();
            if (viewName === 'settings') initSettings();
        } else {
            viewContainer.innerHTML = `<div style="display:flex; justify-content:center; align-items:center; height:100%; color:var(--text-secondary);">
                <h2><i class="fa-solid fa-code"></i> ${route.title} Module Loading Error</h2>
            </div>`;
        }
    };

    const initCharts = () => {
        // ... (Existing Chart Logic) ...
        const ctx1 = document.getElementById('attendanceChart');
        if (ctx1) {
            new Chart(ctx1.getContext('2d'), {
                type: 'line',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                    datasets: [{
                        label: 'Present Students',
                        data: [110, 115, 124, 120, 124, 98],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        const ctx2 = document.getElementById('alertsChart');
        if (ctx2) {
            new Chart(ctx2.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Running', 'Loitering', 'Unauthorized'],
                    datasets: [{
                        data: [5, 2, 1],
                        backgroundColor: ['#ef4444', '#f59e0b', '#6366f1'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } }
                }
            });
        }
    };

    const initAttendance = () => {
        const searchInput = document.getElementById('search-attendance');
        const exportBtn = document.getElementById('btn-export-csv');
        const tableBody = document.getElementById('attendance-table-body');

        if (searchInput && tableBody) {
            searchInput.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                const rows = tableBody.querySelectorAll('tr');
                rows.forEach(row => {
                    const text = row.innerText.toLowerCase();
                    row.style.display = text.includes(term) ? '' : 'none';
                });
            });
        }

        if (exportBtn && tableBody) {
            exportBtn.addEventListener('click', () => {
                let csv = "Time,Student Name,Roll No,Class,Captured Via,Status\n";
                const rows = tableBody.querySelectorAll('tr');
                rows.forEach(row => {
                    const cols = row.querySelectorAll('td');
                    const data = [];
                    cols.forEach(col => data.push(col.innerText.replace(/(\r\n|\n|\r)/gm, " ")));
                    csv += data.join(",") + "\n";
                });

                const blob = new Blob([csv], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'attendance_logs.csv';
                a.click();
            });
        }
    };

    const initAlerts = () => {
        const filter = document.getElementById('alert-filter');
        const clearBtn = document.getElementById('btn-clear-alerts');
        const container = document.getElementById('alerts-container');

        if (filter) {
            filter.addEventListener('change', (e) => {
                const val = e.target.value.toLowerCase();
                const items = document.querySelectorAll('.alert-item');
                items.forEach(item => {
                    if (val === 'all') {
                        item.style.display = 'flex';
                    } else {
                        item.style.display = item.dataset.severity === val ? 'flex' : 'none';
                    }
                });
            });
        }

        if (clearBtn && container) {
            clearBtn.addEventListener('click', () => {
                if (confirm('Are you sure you want to clear all alerts?')) {
                    container.innerHTML = '<div style="text-align:center; padding: 2rem; color: var(--text-secondary);">No active alerts</div>';
                }
            });
        }
    };

    const initSettings = () => {
        const saveBtn = document.getElementById('btn-save-settings');
        const toggle = document.getElementById('system-active-toggle');

        // Load state
        if (toggle) {
            const savedState = localStorage.getItem('surveillx_system_active');
            if (savedState !== null) {
                toggle.checked = savedState === 'true';
            }
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                const originalText = saveBtn.innerText;
                saveBtn.innerText = 'Saving...';

                if (toggle) {
                    localStorage.setItem('surveillx_system_active', toggle.checked);
                }

                setTimeout(() => {
                    saveBtn.innerText = 'Changes Saved!';
                    saveBtn.style.background = '#22c55e';
                    setTimeout(() => {
                        saveBtn.innerText = originalText;
                        saveBtn.style.background = 'var(--accent)';
                    }, 2000);
                }, 800);
            });
        }
    };

    const initLive = () => {
        let stream = null;
        let isStreaming = false;

        const videoElement = document.getElementById('camera-stream');
        const loadingEl = document.getElementById('cam1-loading');
        const aiOverlay = document.getElementById('ai-overlay');
        const statusIcon = document.getElementById('cam1-status');
        const toggleBtn = document.getElementById('btn-toggle-camera');
        const latencyEl = document.getElementById('latency');

        const updateTime = () => {
            const timeEl = document.getElementById('cam-time');
            if (timeEl) {
                // Clear any existing interval to prevent duplicates if function called multiple times
                if (window.liveClockInterval) clearInterval(window.liveClockInterval);

                window.liveClockInterval = setInterval(() => {
                    const now = new Date();
                    if (document.getElementById('cam-time')) {
                        timeEl.textContent = now.toLocaleTimeString();
                    } else {
                        clearInterval(window.liveClockInterval);
                    }
                }, 1000);
            }
        };

        updateTime();

        // Initialize camera stream
        async function startCamera() {
            if (!videoElement) return;

            try {
                // Request camera access
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 1920 },
                        height: { ideal: 1080 }
                    },
                    audio: false
                });

                // Attach stream to video element
                videoElement.srcObject = stream;

                // Wait for video to be ready
                await new Promise(resolve => {
                    videoElement.onloadedmetadata = () => {
                        videoElement.play();
                        resolve();
                    };
                });

                // Hide loading, show video
                loadingEl.style.display = 'none';
                videoElement.style.display = 'block';

                // Show AI overlay after 1 second
                setTimeout(() => {
                    if (aiOverlay) aiOverlay.style.display = 'block';
                }, 1000);

                // Update button
                if (toggleBtn) {
                    toggleBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop';
                    toggleBtn.style.background = 'rgba(239, 68, 68, 0.8)';
                }
                isStreaming = true;

                // Simulate latency
                if (latencyEl) latencyEl.textContent = Math.floor(Math.random() * 20) + 15;

                console.log('Camera stream started successfully');
            } catch (error) {
                console.error('Error accessing camera:', error);
                if (loadingEl) {
                    loadingEl.innerHTML = `
                        <i class="fa-solid fa-video-slash" style="font-size: 3rem; color: rgba(255,68,68,0.5);"></i>
                        <p style="color: rgba(255,68,68,0.8); margin-top: 1rem;">Camera access denied or not available</p>
                        <p style="color: rgba(255,255,255,0.4); font-size: 0.8rem;">Please grant camera permissions</p>
                    `;
                }
                if (statusIcon) {
                    statusIcon.classList.remove('text-success');
                    statusIcon.style.color = '#ef4444';
                }
                if (toggleBtn) toggleBtn.innerHTML = '<i class="fa-solid fa-play"></i> Retry';
            }
        }

        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }

            if (videoElement) videoElement.style.display = 'none';
            if (aiOverlay) aiOverlay.style.display = 'none';
            if (loadingEl) {
                loadingEl.style.display = 'flex';
                loadingEl.innerHTML = `
                    <i class="fa-solid fa-video" style="font-size: 3rem; color: rgba(255,255,255,0.3); margin-bottom: 1rem;"></i>
                    <p style="color: rgba(255,255,255,0.6);">Camera stopped</p>
                `;
            }

            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start';
                toggleBtn.style.background = 'var(--accent)';
            }
            if (statusIcon) {
                statusIcon.classList.remove('text-success');
                statusIcon.style.color = '#94a3b8';
            }
            isStreaming = false;
        }

        if (toggleBtn) {
            // Remove old event listeners by cloning
            const newBtn = toggleBtn.cloneNode(true);
            toggleBtn.parentNode.replaceChild(newBtn, toggleBtn);

            newBtn.addEventListener('click', () => {
                if (isStreaming) {
                    stopCamera();
                } else {
                    startCamera();
                }
            });

            // Auto start
            setTimeout(startCamera, 500);
        }
    };

    const initStudents = () => {
        // Toggle Tabs
        const tabs = document.querySelectorAll('.tab-btn');
        const tableActive = document.getElementById('table-active');
        const tablePending = document.getElementById('table-pending');

        tabs.forEach((tab, index) => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => {
                    t.style.background = 'transparent';
                    t.style.color = '#94a3b8';
                });
                tab.style.background = '#3b82f6';
                tab.style.color = 'white';

                if (index === 0) {
                    if (tableActive) tableActive.style.display = 'table';
                    if (tablePending) tablePending.style.display = 'none';
                } else {
                    if (tableActive) tableActive.style.display = 'none';
                    if (tablePending) tablePending.style.display = 'table';
                }
            });
        });

        // Toggle QR Panel
        const btnQr = document.getElementById('btn-qr');
        const qrPanel = document.getElementById('qr-panel');

        if (btnQr && qrPanel) {
            // Remove old listeners
            const newBtn = btnQr.cloneNode(true);
            btnQr.parentNode.replaceChild(newBtn, btnQr);

            newBtn.addEventListener('click', () => {
                qrPanel.style.display = qrPanel.style.display === 'none' ? 'block' : 'none';
            });
        }

        // Copy Registration URL
        const btnCopyUrl = document.getElementById('btn-copy-url');
        const regUrl = document.getElementById('reg-url');

        if (btnCopyUrl && regUrl) {
            btnCopyUrl.addEventListener('click', () => {
                const url = regUrl.textContent;
                navigator.clipboard.writeText(url).then(() => {
                    const originalHTML = btnCopyUrl.innerHTML;
                    btnCopyUrl.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                    btnCopyUrl.style.background = '#22c55e';
                    setTimeout(() => {
                        btnCopyUrl.innerHTML = originalHTML;
                        btnCopyUrl.style.background = 'var(--accent)';
                    }, 2000);
                });
            });
        }

        // Approve/Reject Buttons
        document.querySelectorAll('.btn-approve').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const row = e.target.closest('tr');
                if (confirm('Approve this student registration request?')) {
                    // Animation
                    row.style.transform = 'translateX(20px)';
                    row.style.opacity = '0';
                    setTimeout(() => {
                        row.remove();
                        // Update counter (mock)
                        alert('Student request approved. Added to Active Database.');
                    }, 300);
                }
            });
        });

        document.querySelectorAll('.btn-reject').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const row = e.target.closest('tr');
                if (confirm('Reject this registration request?')) {
                    row.style.transform = 'translateX(20px)';
                    row.style.opacity = '0';
                    setTimeout(() => {
                        row.remove();
                    }, 300);
                }
            });
        });

        // --- LOCAL STORAGE PERSISTENCE START ---
        const renderStudents = () => {
            const tbody = document.getElementById('students-table-body');
            if (!tbody) return;

            tbody.innerHTML = '';

            // Get from local storage or use default
            let students = JSON.parse(localStorage.getItem('surveillx_students'));
            if (!students) {
                // Default Dummy Data
                students = [
                    { name: 'Vishnu Jadhav', roll: '52', class: 'BCA - III', status: 'Active' }
                ];
                localStorage.setItem('surveillx_students', JSON.stringify(students));
            }

            students.forEach(student => {
                const newRow = document.createElement('tr');
                newRow.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                newRow.innerHTML = `
                    <td style="padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem;">
                         <div style="width: 36px; height: 36px; background: #334155; border-radius: 50%;"></div>
                        <span>${student.name}</span>
                    </td>
                    <td style="padding: 1rem; color: var(--text-secondary);">${student.roll}</td>
                    <td style="padding: 1rem; color: var(--text-secondary);">${student.class}</td>
                    <td style="padding: 1rem;"><span style="background: rgba(34, 197, 94, 0.1); color: var(--success); padding: 0.25rem 0.75rem; border-radius: 1rem; font-size: 0.8rem;">${student.status}</span></td>
                    <td style="padding: 1rem;">
                        <button style="background: none; border: none; color: var(--text-secondary); cursor: pointer;"><i class="fa-solid fa-ellipsis"></i></button>
                    </td>
                `;
                tbody.appendChild(newRow);
            });

            // Update Active Count
            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab) {
                activeTab.textContent = `Active (${students.length})`;
            }
        };

        // Render initially
        renderStudents();
        // --- LOCAL STORAGE PERSISTENCE END ---


        // Manual Add Modal Controls
        const btnManualAdd = document.getElementById('btn-manual-add');
        const manualAddModal = document.getElementById('manual-add-modal');
        const btnCloseModal = document.getElementById('btn-close-modal');
        const btnCancelForm = document.getElementById('btn-cancel-form');
        const addStudentForm = document.getElementById('add-student-form');
        const previewImg = document.getElementById('preview-img');
        const photoPreview = document.getElementById('photo-preview');
        const btnUploadPhoto = document.getElementById('btn-upload-photo');
        const studentPhoto = document.getElementById('student-photo');

        // Close Modal Function
        function closeModal() {
            if (manualAddModal) {
                manualAddModal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
            if (addStudentForm) addStudentForm.reset();
            if (previewImg) previewImg.style.display = 'none';
            if (photoPreview) photoPreview.querySelector('.fa-camera').style.display = 'block';
        }

        // Open Modal
        if (btnManualAdd && manualAddModal) {
            btnManualAdd.addEventListener('click', () => {
                manualAddModal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            });
        }

        // Close UI Handlers
        if (btnCloseModal) btnCloseModal.addEventListener('click', closeModal);
        if (btnCancelForm) btnCancelForm.addEventListener('click', closeModal);
        if (manualAddModal) {
            manualAddModal.addEventListener('click', (e) => {
                if (e.target === manualAddModal) closeModal();
            });
        }

        // Photo Upload
        if (btnUploadPhoto && studentPhoto) {
            btnUploadPhoto.addEventListener('click', () => studentPhoto.click());

            studentPhoto.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        if (previewImg) {
                            previewImg.src = event.target.result;
                            previewImg.style.display = 'block';
                        }
                        if (photoPreview) photoPreview.querySelector('.fa-camera').style.display = 'none';
                    };
                    reader.readAsDataURL(file);
                }
            });
        }

        // Form Submission
        if (addStudentForm && tableActive) {
            addStudentForm.addEventListener('submit', (e) => {
                e.preventDefault();

                const name = document.getElementById('input-name').value;
                const roll = document.getElementById('input-roll').value;
                const studentClass = document.getElementById('input-class').value;
                const email = document.getElementById('input-email').value;
                const photo = document.getElementById('student-photo').files[0];

                if (!name || !roll || !studentClass) {
                    alert('Please fill in all required fields');
                    return;
                }

                // VALIDATION: Student Name (No digits allowed)
                if (/\d/.test(name)) {
                    alert('Student Name cannot contain digits. Please enter a valid name.');
                    return;
                }

                // VALIDATION: Roll Number (Digits Only)
                if (!/^\d+$/.test(roll)) {
                    alert('Invalid Roll Number: Must contain only digits (0-9).');
                    return;
                }

                // VALIDATION: Email (Format check if provided)
                if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                    alert('Invalid Email Address. Please enter a valid email.');
                    return;
                }

                // SAVE TO LOCAL STORAGE
                const newStudent = {
                    name,
                    roll,
                    class: studentClass,
                    status: 'Active'
                };

                let students = JSON.parse(localStorage.getItem('surveillx_students')) || [];
                students.unshift(newStudent); // Add to beginning
                localStorage.setItem('surveillx_students', JSON.stringify(students));

                alert(`Student "${name}" added successfully!`);
                closeModal();

                // Re-render
                renderStudents();
            });
        }
    };

    // Event Listeners
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.getAttribute('href').substring(1);
            loadView(view);
        });
    });

    // Initial Load
    // Handle hash if present (e.g., #live), otherwise default to dashboard
    const initialView = window.location.hash ? window.location.hash.substring(1) : 'dashboard';
    loadView(initialView || 'dashboard');
});

