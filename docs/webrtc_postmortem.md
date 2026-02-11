# WebRTC Streaming Post-Mortem

## Goal
Stream the Windows client's webcam feed to the SurveillX browser dashboard Live Monitor in real-time.

## Architecture Attempted
```
Windows Client (aiortc) ──WebRTC──► EC2 Server (aiortc) ──Socket.IO──► Browser (canvas)
```

---

## Issue 1: `asyncio.run()` Crash in Flask Route

**Problem:** The original `api/webrtc.py` used `asyncio.run()` inside a synchronous Flask route to handle the async aiortc API. This crashed because Flask-SocketIO already runs its own event loop.

**Fix Applied:** Created a persistent background event loop in a daemon thread, used `asyncio.run_coroutine_threadsafe()` to run async code from sync Flask context.

**Result:** ✅ Fixed — SDP exchange started working.

---

## Issue 2: No TURN Server → 0 Frames

**Problem:** WebRTC has two stages:
1. **Signaling** (SDP offer/answer via HTTP) — ✅ worked
2. **Media** (video frames via UDP/RTP) — ❌ failed

Without a TURN relay server, the Windows client (behind NAT/router) and the EC2 server couldn't establish a direct UDP path for media packets. ICE negotiation would show `SUCCEEDED` but `track.recv()` returned 0 frames.

**Fix Applied:** Installed coturn TURN server on EC2, configured with:
- Port 3478 (UDP/TCP)
- `external-ip=13.205.156.238/172.31.12.184`
- Credentials: `surveillx:Vishu@9637`
- Opened UDP ports 10000-60000 in EC2 Security Group

**Result:** ⚠️ Partially fixed — TURN allocation succeeded, ICE candidate pair succeeded, but still 0 frames (see Issue 3).

---

## Issue 3: aiortc `track.recv()` Returns 0 Frames Despite Connected State

**Problem:** Even with TURN configured:
- ICE completed successfully ✅
- Connection state = `connected` ✅
- Track state = `live` ✅
- But `track.recv()` timed out after 30s with **0 frames** ❌

The successful ICE pair was: `172.31.12.184 → 172.31.12.184` (server private IP to TURN relay on same machine). This suggests the TURN relay was working at the ICE/STUN level but **RTP media packets were not flowing** through the DTLS/SRTP layer.

**Root Cause (probable):** aiortc on the server is both the TURN client AND the WebRTC peer on the same machine. The TURN relay allocates a port on the same IP, and the RTP packets loop back through the same network interface. This is a known edge case where aiortc's DTLS/SRTP negotiation fails silently — the connection reports `connected` but the media pipeline never completes.

**This was NOT fixable** without either:
- Using an external TURN server (e.g., Twilio, Xirsys) on a different machine
- OR abandoning WebRTC media transport entirely

---

## Issue 4: coturn `403 Forbidden IP`

**Problem:** coturn's `turnutils_uclient` test returned `error 403 (Forbidden IP)`.

**Cause:** The test tool tried to bind a channel to `127.0.0.1` (loopback), which coturn blocks by default. The `no-loopback-peers` config option was not supported in coturn 4.5.2 (returned `Bad configuration format`).

**Result:** Red herring — the 403 was only from the test tool. Real client connections with public IPs worked at the STUN/allocation level.

---

## Issue 5: Browser Socket.IO "Disconnected"

**Problem:** Even after the server successfully received frames via the HTTP POST fallback endpoint (`/webrtc/frame`), the browser Live Monitor showed "Connection: Disconnected" and "0 Frames Received".

**Causes identified:**
1. `app.js` used `transports: ['websocket']` which skipped HTTP long-polling
2. The WebSocket upgrade returned HTTP 500 (`AssertionError: write() before start_response`) — a known Flask-SocketIO + Werkzeug issue
3. With websocket-only transport and the upgrade failing, Socket.IO had no fallback → connection silently failed

**Status:** Changed to `transports: ['polling', 'websocket']` but wasn't fully verified before cleanup.

---

## Summary of What Worked vs. What Didn't

| Component | Status |
|-----------|--------|
| WebRTC SDP signaling via HTTP | ✅ Works |
| ICE candidate exchange | ✅ Works |
| TURN server allocation | ✅ Works |
| ICE connectivity check | ✅ Succeeds |
| DTLS/SRTP media transport | ❌ 0 frames |
| aiortc `track.recv()` | ❌ Timeout |
| HTTP POST frame endpoint | ✅ 322+ frames received |
| Socket.IO `/stream` → browser | ❌ Connection fails (500 on WS upgrade) |

## Recommendation for Fresh Implementation

For reliable streaming without WebRTC complexity, use **Socket.IO directly** for the full pipeline:

```
Windows Client ──Socket.IO──► Server ──Socket.IO──► Browser
```

- The `client/stream_client.py` already does this via Socket.IO
- The `services/stream_handler.py` already handles frame relay
- The browser `app.js` already has the `displayFrame()` logic
- **No TURN, no ICE, no DTLS** — just WebSocket over existing HTTP
- Works through any firewall, any NAT

The Socket.IO connection between browser and server needs to be debugged separately (the 500 error on WebSocket upgrade).
