---
description: Rules for implementing video streaming in SurveillX
---

# Streaming Implementation Rules

## Core Rule: Latency < 200ms
- Surveillance latency MUST be below 200ms end-to-end.
- FastRTC (port 8080) is the primary streaming mode — use it by default.
- JPEG WS (port 8443) is the fallback if FastRTC is unavailable.
- The user has another AI handling the Windows client code. Do NOT modify Windows client code unless explicitly asked.

## Architecture
```
Windows Client (JPEG/WS) ──► EC2 Server (FastRTC 8080 / JPEG WS 8443) ──► Nginx ──► Browser
```

### Server-side
- FastRTC: `fastrtc_server.py` (FastAPI/uvicorn on port 8080)
  - Client sends to `/ws/stream` (hello + frames)
  - Viewers connect to `/ws/view`
  - Nginx `/ws/fastrtc` → `http://127.0.0.1:8080/ws/view`
- JPEG WS Hub: `gst_streaming_server.py` (websockets on port 8443)
  - Client sends with `{type:"hello", mode:"jpeg"}`
  - Viewers send `{type:"viewer"}`
  - Nginx `/ws/stream` → `http://127.0.0.1:8443`
- Both servers use `asyncio.gather` for parallel broadcast
- Both inject `server_time` (ms) in frame messages for latency measurement

### Browser-side
- `app.js` → `connectStream()` → `displayFrame()`
- Uses Blob URL (not base64 data: URI) for faster frame rendering
- Latency calculated from `data.server_time` or `data.timestamp`
- Color coding: green < 300ms, yellow < 600ms, red > 600ms

## Known Issues & Solutions
- **asyncio in Flask**: Use `asyncio.run_coroutine_threadsafe()`, never `asyncio.run()`.
- **NAT traversal**: Always configure TURN server. EC2 coturn on port 3478.
- **FastRTC 403 through Nginx**: Caused by path mismatch. Nginx must proxy `/ws/fastrtc` to `/ws/view` on port 8080, NOT to the root.
- **Socket.IO disconnect**: Allow polling fallback: `transports: ['polling', 'websocket']`.
