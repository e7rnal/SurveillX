/**
 * SurveillX Browser — Stream Viewer (for FastRTC)
 * 
 * NO CHANGES NEEDED to the existing app.js!
 * 
 * The FastRTC server emits frames to Flask via Socket.IO.
 * The browser already listens for 'frame' events on the /stream namespace.
 * This file is just for REFERENCE — showing what the browser does.
 * 
 * The existing connectSocket() in app.js already handles everything:
 */

// This is what app.js already does (no changes needed):
function connectSocket() {
    // Connect to Flask's Socket.IO /stream namespace
    const socket = io('/stream', {
        transports: ['polling', 'websocket']  // polling first, then upgrade
    });

    socket.on('connect', () => {
        console.log('Stream connected');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        console.log('Stream disconnected');
        updateConnectionStatus(false);
    });

    socket.on('frame', (data) => {
        // data.frame = base64 JPEG
        // data.camera_id = camera identifier
        // data.timestamp = frame timestamp
        displayFrame(data);
    });

    socket.on('detection', (data) => {
        // data contains face detection results
        displayDetections(data);
    });
}

function displayFrame(data) {
    const img = document.getElementById('live-feed');
    if (img && data.frame) {
        img.src = 'data:image/jpeg;base64,' + data.frame;
    }
}

/**
 * SUMMARY:
 * - Browser connects to Flask :5000 via Socket.IO (existing)
 * - FastRTC server on :8080 receives WebRTC frames
 * - FastRTC forwards frames to Flask via Socket.IO client
 * - Flask broadcasts to browser — no browser changes needed!
 * 
 * The only scenario where browser changes are needed is if you want
 * the browser to connect DIRECTLY to the FastRTC server via WebRTC
 * (for lower latency). But Socket.IO relay adds only ~20ms, so
 * it's not worth the complexity.
 */
