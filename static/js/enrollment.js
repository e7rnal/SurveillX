/**
 * Enrollment System Frontend Integration
 * Connects enrollment UI to backend APIs
 */

// API Base URL
const API_BASE = window.location.origin;

/**
 * Generate enrollment link and display it
 */
async function generateEnrollmentLink() {
    const emailInput = document.getElementById('enrollment-email');
    const rollNoInput = document.getElementById('enrollment-roll-no');
    const qrCodeImg = document.getElementById('qr-code-img');
    const regUrl = document.getElementById('reg-url');
    const copyBtn = document.getElementById('btn-copy-url');

    const email = emailInput?.value;
    const rollNo = rollNoInput?.value;

    if (!email) {
        showToast('Please enter student email', 'error');
        return;
    }

    try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch(`${API_BASE}/api/enrollment/generate-link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ email, roll_no: rollNo })
        });

        const data = await response.json();

        if (response.ok) {
            // Build enrollment URL
            const enrollmentUrl = data.token
                ? `${API_BASE}/templates/enroll.html?token=${data.token}`
                : `${API_BASE}/templates/enroll.html`;

            // Update QR code
            if (qrCodeImg) {
                qrCodeImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(enrollmentUrl)}`;
            }

            // Update URL display
            if (regUrl) {
                regUrl.textContent = enrollmentUrl;
            }

            // Show success message
            const message = data.token
                ? 'Enrollment link generated! (Email not sent - copy link below)'
                : 'Enrollment link generated successfully!';

            showToast(message, 'success');

            // Setup copy button
            if (copyBtn) {
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(enrollmentUrl);
                    showToast('Link copied to clipboard!', 'success');
                };
            }

            // Clear inputs
            if (emailInput) emailInput.value = '';
            if (rollNoInput) rollNoInput.value = '';

        } else {
            showToast(data.error || 'Failed to generate link', 'error');
        }
    } catch (error) {
        console.error('Generate link error:', error);
        showToast('Failed to generate enrollment link', 'error');
    }
}

/**
 * Load and display pending enrollments
 */
async function loadPendingEnrollments() {
    const tableBody = document.getElementById('pending-enrollments-body');
    if (!tableBody) return;

    try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch(`${API_BASE}/api/enrollment/pending`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok && data.enrollments) {
            if (data.enrollments.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                            No pending enrollments
                        </td>
                    </tr>
                `;
                return;
            }

            tableBody.innerHTML = data.enrollments.map(enrollment => {
                const timeAgo = getTimeAgo(new Date(enrollment.submitted_at));
                return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);" data-enrollment-id="${enrollment.id}">
                        <td style="padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem;">
                            <div style="width: 36px; height: 36px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                                ${enrollment.name.charAt(0)}
                            </div>
                            <div>
                                <div style="font-weight: 500;">${enrollment.name}</div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary);">${enrollment.email}</div>
                            </div>
                        </td>
                        <td style="padding: 1rem; color: var(--text-secondary);">${enrollment.roll_no || '--'}</td>
                        <td style="padding: 1rem; color: var(--text-secondary);">${enrollment.class || '--'}</td>
                        <td style="padding: 1rem; color: var(--text-secondary);">${timeAgo}</td>
                        <td style="padding: 1rem; display: flex; gap: 0.5rem;">
                            <button class="btn-approve" onclick="approveEnrollment(${enrollment.id})" 
                                style="background: rgba(34, 197, 94, 0.1); color: var(--success); border: 1px solid rgba(34, 197, 94, 0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                                <i class="fa-solid fa-check"></i>
                            </button>
                            <button class="btn-reject" onclick="rejectEnrollment(${enrollment.id})" 
                                style="background: rgba(239, 68, 68, 0.1); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            // Update badge count
            const badge = document.querySelector('.pending-badge');
            if (badge) {
                badge.textContent = data.enrollments.length;
            }
        }
    } catch (error) {
        console.error('Load pending enrollments error:', error);
        showToast('Failed to load pending enrollments', 'error');
    }
}

/**
 * Approve enrollment
 */
async function approveEnrollment(enrollmentId) {
    if (!confirm('Approve this enrollment?')) return;

    try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch(`${API_BASE}/api/enrollment/${enrollmentId}/approve`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Enrollment approved successfully!', 'success');
            // Remove row from table
            const row = document.querySelector(`tr[data-enrollment-id="${enrollmentId}"]`);
            if (row) row.remove();
            // Reload pending enrollments
            loadPendingEnrollments();
            // Reload students list
            if (typeof loadStudents === 'function') loadStudents();
        } else {
            showToast(data.error || 'Failed to approve enrollment', 'error');
        }
    } catch (error) {
        console.error('Approve enrollment error:', error);
        showToast('Failed to approve enrollment', 'error');
    }
}

/**
 * Reject enrollment
 */
async function rejectEnrollment(enrollmentId) {
    const reason = prompt('Reason for rejection:');
    if (!reason) return;

    try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch(`${API_BASE}/api/enrollment/${enrollmentId}/reject`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ reason })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('Enrollment rejected', 'success');
            // Remove row from table
            const row = document.querySelector(`tr[data-enrollment-id="${enrollmentId}"]`);
            if (row) row.remove();
            // Reload pending enrollments
            loadPendingEnrollments();
        } else {
            showToast(data.error || 'Failed to reject enrollment', 'error');
        }
    } catch (error) {
        console.error('Reject enrollment error:', error);
        showToast('Failed to reject enrollment', 'error');
    }
}

/**
 * Load students from API
 */
async function loadStudents() {
    const tableBody = document.getElementById('students-table-body');
    if (!tableBody) return;

    try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch(`${API_BASE}/api/students/`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok && data.students) {
            tableBody.innerHTML = data.students.map(student => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem;">
                        <div style="width: 36px; height: 36px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                            ${student.name.charAt(0)}
                        </div>
                        <span style="font-weight: 500;">${student.name}</span>
                    </td>
                    <td style="padding: 1rem; color: var(--text-secondary);">${student.roll_no}</td>
                    <td style="padding: 1rem;">${student.class || 'N/A'}</td>
                    <td style="padding: 1rem;">
                        <span style="color: var(--success);">
                            <i class="fa-solid fa-circle-check"></i> Active
                        </span>
                    </td>
                    <td style="padding: 1rem;">
                        <button style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: var(--text-secondary); padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">
                            <i class="fa-solid fa-ellipsis-vertical"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            // Update count in tab
            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab) {
                activeTab.innerHTML = `Active (${data.students.length})`;
            }
        }
    } catch (error) {
        console.error('Load students error:', error);
        showToast('Failed to load students', 'error');
    }
}

/**
 * Helper: Get time ago string
 */
function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60
    };

    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
        }
    }

    return 'just now';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--accent)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Make functions globally available
window.generateEnrollmentLink = generateEnrollmentLink;
window.loadPendingEnrollments = loadPendingEnrollments;
window.approveEnrollment = approveEnrollment;
window.rejectEnrollment = rejectEnrollment;
window.loadStudents = loadStudents;
window.showToast = showToast;
