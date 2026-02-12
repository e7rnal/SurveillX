---
description: Rules for implementing video streaming in SurveillX
---

# Streaming Implementation Rules

## Core Rule: WebRTC is the chosen technology
- When the user says "WebRTC", we are using **WebRTC**. Do NOT suggest switching to Socket.IO, HTTP POST, or any other protocol as a replacement.
- If WebRTC has issues, **fix the issues** — do not pivot to a different technology.
- The user has another AI handling the Windows client code. Do NOT modify or create Windows client code unless explicitly asked.

## Known Issues & Solutions (from docs/webrtc_postmortem.md)
- **asyncio in Flask**: Use a persistent background event loop with `asyncio.run_coroutine_threadsafe()`, never `asyncio.run()`.
- **NAT traversal**: Always configure TURN server. The EC2 coturn config, credentials, and UDP ports are already set up.
- **aiortc track.recv() 0 frames**: This was caused by TURN relay on the same machine. Solution: use an external TURN provider OR switch the server-side WebRTC library.
- **Socket.IO browser disconnect**: The WebSocket upgrade can fail; always allow polling fallback with `transports: ['polling', 'websocket']`.

## Architecture Reference
```
Windows Client (WebRTC) ──► EC2 Server ──► Browser Live Monitor
```
- Backend: Flask + Flask-SocketIO on port 5000
- WebRTC blueprint: api/webrtc.py (prefix: /webrtc)
- Stream handler: services/stream_handler.py (Socket.IO /stream namespace)
- Frontend: static/js/app.js → connectSocket() → displayFrame()
- TURN server: coturn on EC2 (port 3478, credentials in /etc/turnserver.conf)
