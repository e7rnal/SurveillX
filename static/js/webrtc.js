/**
 * WebRTC Client for Browser
 * Handles WebRTC connection and video display for ultra-low latency streaming
 */

class WebRTCClient {
    constructor() {
        this.pc = null;
        this.connectionId = null;
        this.onConnected = null;
        this.onDisconnected = null;
        this.onError = null;
        this.onStats = null;
        this.statsInterval = null;
        this.videoElement = null;
    }

    /**
     * Initialize WebRTC connection
     * @param {HTMLVideoElement} videoElement - Video element to display stream
     * @returns {Promise<boolean>}
     */
    async connect(videoElement) {
        this.videoElement = videoElement;

        console.log('Initializing WebRTC connection...');

        // Create RTCPeerConnection with STUN servers
        const config = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };

        this.pc = new RTCPeerConnection(config);

        // Handle ICE candidates
        this.pc.onicecandidate = (event) => {
            if (event.candidate) {
                console.log('ICE candidate:', event.candidate.type);
            }
        };

        // Handle connection state changes
        this.pc.onconnectionstatechange = () => {
            console.log('Connection state:', this.pc.connectionState);

            switch (this.pc.connectionState) {
                case 'connected':
                    if (this.onConnected) this.onConnected();
                    this.startStatsMonitoring();
                    break;
                case 'disconnected':
                case 'failed':
                case 'closed':
                    if (this.onDisconnected) this.onDisconnected(this.pc.connectionState);
                    this.stopStatsMonitoring();
                    break;
            }
        };

        // Handle incoming tracks (video from server)
        this.pc.ontrack = (event) => {
            console.log('Received track:', event.track.kind);

            if (event.track.kind === 'video' && this.videoElement) {
                this.videoElement.srcObject = event.streams[0];
                this.videoElement.play().catch(e => {
                    console.warn('Autoplay blocked:', e);
                });
            }
        };

        // Add transceiver for receiving video
        this.pc.addTransceiver('video', { direction: 'recvonly' });

        try {
            // Create offer
            const offer = await this.pc.createOffer();
            await this.pc.setLocalDescription(offer);

            // Wait for ICE gathering
            await this.waitForIceGathering();

            // Send offer to server
            const response = await fetch('/webrtc/offer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...API.getAuthHeaders()
                },
                body: JSON.stringify({
                    sdp: this.pc.localDescription.sdp,
                    type: this.pc.localDescription.type
                })
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const answer = await response.json();
            this.connectionId = answer.connection_id;

            // Set remote description (server's answer)
            await this.pc.setRemoteDescription({
                sdp: answer.sdp,
                type: answer.type
            });

            console.log('WebRTC connected, ID:', this.connectionId);
            return true;

        } catch (error) {
            console.error('WebRTC connection failed:', error);
            if (this.onError) this.onError(error);
            return false;
        }
    }

    /**
     * Wait for ICE gathering to complete
     */
    async waitForIceGathering() {
        if (this.pc.iceGatheringState === 'complete') {
            return;
        }

        return new Promise((resolve) => {
            const checkState = () => {
                if (this.pc.iceGatheringState === 'complete') {
                    this.pc.removeEventListener('icegatheringstatechange', checkState);
                    resolve();
                }
            };

            this.pc.addEventListener('icegatheringstatechange', checkState);

            // Timeout after 5 seconds
            setTimeout(() => {
                this.pc.removeEventListener('icegatheringstatechange', checkState);
                resolve();
            }, 5000);
        });
    }

    /**
     * Start monitoring connection stats
     */
    startStatsMonitoring() {
        this.statsInterval = setInterval(async () => {
            if (!this.pc) return;

            const stats = await this.pc.getStats();
            let videoStats = null;

            stats.forEach(report => {
                if (report.type === 'inbound-rtp' && report.kind === 'video') {
                    videoStats = {
                        framesReceived: report.framesReceived,
                        framesDecoded: report.framesDecoded,
                        framesDropped: report.framesDropped,
                        bytesReceived: report.bytesReceived,
                        packetsLost: report.packetsLost,
                        jitter: report.jitter,
                        timestamp: report.timestamp
                    };
                }
            });

            if (videoStats && this.onStats) {
                this.onStats(videoStats);
            }
        }, 1000);
    }

    /**
     * Stop monitoring connection stats
     */
    stopStatsMonitoring() {
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
            this.statsInterval = null;
        }
    }

    /**
     * Disconnect and cleanup
     */
    disconnect() {
        this.stopStatsMonitoring();

        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }

        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }

        this.connectionId = null;
        console.log('WebRTC disconnected');
    }

    /**
     * Get connection state
     */
    getState() {
        return this.pc ? this.pc.connectionState : 'closed';
    }
}

// Export for use
window.WebRTCClient = WebRTCClient;
