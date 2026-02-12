/**
 * SurveillX Browser — Stream Viewer (for GStreamer)
 *
 * IDENTICAL to the FastRTC approach — NO CHANGES NEEDED!
 *
 * The GStreamer server forwards frames to Flask via Socket.IO.
 * The browser already listens for 'frame' events on the /stream namespace.
 *
 * This file is for REFERENCE only.
 */

// The existing app.js already handles everything:
// 1. Connects to Flask Socket.IO /stream namespace
// 2. Listens for 'frame' events
// 3. Renders base64 JPEG to <img> tag

/**
 * ARCHITECTURE:
 * 
 * GStreamer server (port 8443, WebSocket)
 *     ↓ receives WebRTC frames
 *     ↓ face recognition (Python callback)
 *     ↓ JPEG encode → base64
 *     ↓ Socket.IO client emit
 *     ↓
 * Flask server (port 5000)
 *     ↓ Socket.IO broadcast
 *     ↓
 * Browser (this code)
 *     ↓ socket.on('frame')
 *     ↓ render to <img>
 * 
 * NO BROWSER CHANGES NEEDED for either GStreamer or FastRTC approach.
 */
