# FastRTC — Architecture

## How It Integrates with SurveillX

FastRTC runs as a **sidecar** alongside Flask. Two servers, one machine:

```
┌─────────────────────────────────────────────────────────────┐
│                        EC2 Server                           │
│                                                             │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  Flask :5000     │     │  FastRTC/FastAPI :8080        │  │
│  │                  │     │                              │  │
│  │  - Auth API      │     │  - WebRTC signaling          │  │
│  │  - Students API  │◄────│  - track.recv() (frames)     │  │
│  │  - Alerts API    │emit │  - Face recognition          │  │
│  │  - Socket.IO     │─────│  - Attendance processing     │  │
│  │  - Dashboard     │     │                              │  │
│  └──────────────────┘     └──────────────────────────────┘  │
│           ▲                          ▲                      │
│           │ Socket.IO                │ WebRTC (UDP)          │
│           │                          │                      │
└───────────┼──────────────────────────┼──────────────────────┘
            │                          │
       Browser                  Windows Client
    (Live Monitor)             (Camera Stream)
```

## Data Flow

```
1. Windows Client captures camera frame
     │
     ▼ WebRTC (VP8 over UDP)
2. FastRTC server receives frame via track.recv()
     │
     ▼ OpenCV decode
3. Face Recognition (dlib)
     │
     ├──► Attendance → PostgreSQL
     │
     ▼ Base64 JPEG encode
4. Socket.IO emit to Flask → Browser
```

## Why Two Servers?

| Concern | Flask :5000 | FastRTC :8080 |
|---------|-------------|---------------|
| HTTP API | ✅ | ❌ |
| Socket.IO (browser) | ✅ | ❌ |
| WebRTC signaling | ❌ | ✅ |
| WebRTC media | ❌ | ✅ |
| Face recognition | ❌ | ✅ (on received frames) |
| asyncio event loop | ❌ (WSGI) | ✅ (ASGI/uvicorn) |

Flask can't run aiortc because it's synchronous (WSGI). FastAPI/uvicorn runs a native asyncio loop, which is what aiortc needs.

## Communication Between Servers

FastRTC server → Flask server via **SocketIO client**:

```python
# In FastRTC server, emit frames to Flask's Socket.IO
import socketio
sio = socketio.Client()
sio.connect('http://localhost:5000', namespaces=['/stream'])

# After processing a frame:
sio.emit('frame', {'frame': base64_jpeg, 'camera_id': 1}, namespace='/stream')
```

This way the browser doesn't need to know about the FastRTC server at all — it just receives frames from Flask's existing Socket.IO connection.

## File Structure After Integration

```
surveillx-backend/
├── app.py                  ← Flask (unchanged)
├── streaming_server.py     ← NEW: FastRTC/FastAPI server
├── api/                    ← Flask blueprints (unchanged)
├── services/
│   └── stream_handler.py   ← Socket.IO namespace (unchanged)
├── static/js/
│   └── app.js              ← Browser code (unchanged — already listens for 'frame')
```
