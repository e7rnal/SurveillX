/**
 * SurveillX API Client
 * Clean wrapper for all backend API calls
 */

const API = {
    baseUrl: window.location.origin,

    // Get stored JWT token
    getToken() {
        return localStorage.getItem('jwt_token');
    },

    // Set JWT token
    setToken(token) {
        localStorage.setItem('jwt_token', token);
    },

    // Clear token (logout)
    clearToken() {
        localStorage.removeItem('jwt_token');
    },

    // Check if authenticated
    isAuthenticated() {
        return !!this.getToken();
    },

    // Make authenticated request
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = this.getToken();

        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, config);

            // Handle 401 - redirect to login
            if (response.status === 401) {
                this.clearToken();
                window.location.href = '/templates/login.html';
                return null;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.message || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // ============ AUTH ============

    async login(username, password) {
        const response = await this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (response && response.token) {
            this.setToken(response.token);
        }

        return response;
    },

    logout() {
        this.clearToken();
        window.location.href = '/templates/login.html';
    },

    // ============ STATS ============

    async getStats() {
        return this.request('/api/stats/');
    },

    async getDashboardData() {
        return this.request('/api/stats/dashboard');
    },

    // ============ STUDENTS ============

    async getStudents() {
        return this.request('/api/students/');
    },

    async getStudent(id) {
        return this.request(`/api/students/${id}`);
    },

    async deleteStudent(id) {
        return this.request(`/api/students/${id}`, { method: 'DELETE' });
    },

    // ============ ATTENDANCE ============

    async getAttendance(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/attendance/${query ? '?' + query : ''}`);
    },

    async getTodayAttendance() {
        return this.request('/api/attendance/today');
    },

    // ============ ALERTS ============

    async getAlerts(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/alerts/${query ? '?' + query : ''}`);
    },

    async getRecentAlerts(limit = 10) {
        return this.request(`/api/alerts/recent?limit=${limit}`);
    },

    async markAlertResolved(id) {
        return this.request(`/api/alerts/${id}/resolve`, { method: 'PUT' });
    },

    // ============ ENROLLMENT ============

    async generateEnrollmentLink(email, rollNo) {
        return this.request('/api/enrollment/generate-link', {
            method: 'POST',
            body: JSON.stringify({ email, roll_no: rollNo })
        });
    },

    async getPendingEnrollments() {
        return this.request('/api/enrollment/pending');
    },

    async approveEnrollment(id) {
        return this.request(`/api/enrollment/${id}/approve`, { method: 'PUT' });
    },

    async rejectEnrollment(id, reason) {
        return this.request(`/api/enrollment/${id}/reject`, {
            method: 'PUT',
            body: JSON.stringify({ reason })
        });
    },

    // ============ CAMERAS ============

    async getCameras() {
        return this.request('/api/cameras/');
    },

    async getCameraStatus() {
        return this.request('/api/cameras/status');
    },

    // ============ HEALTH ============

    async healthCheck() {
        return this.request('/health');
    }
};

// Make available globally
window.API = API;
