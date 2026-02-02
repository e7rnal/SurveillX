/**
 * Toast Notification System
 * Professional toast notifications with animations and auto-dismiss
 */

class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', title = null, duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: 'fa-circle-check',
            error: 'fa-circle-xmark',
            warning: 'fa-triangle-exclamation',
            info: 'fa-circle-info'
        };

        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Info'
        };

        toast.innerHTML = `
            <i class="fa-solid ${icons[type]} toast-icon"></i>
            <div class="toast-content">
                <div class="toast-title">${title || titles[type]}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;

        this.container.appendChild(toast);

        // Auto dismiss
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);

        // Play sound for alerts (optional)
        if (type === 'error' || type === 'warning') {
            this.playAlertSound();
        }

        return toast;
    }

    success(message, title = null) {
        return this.show(message, 'success', title);
    }

    error(message, title = null) {
        return this.show(message, 'error', title);
    }

    warning(message, title = null) {
        return this.show(message, 'warning', title);
    }

    info(message, title = null) {
        return this.show(message, 'info', title);
    }

    playAlertSound() {
        // Create a simple beep sound
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 520;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (e) {
            // Audio not supported or blocked
        }
    }
}

// Global toast instance
const Toast = new ToastManager();
