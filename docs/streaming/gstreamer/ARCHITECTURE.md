# GStreamer + webrtcbin — Architecture

## How It Integrates with SurveillX

GStreamer runs as a **subprocess/sidecar** with a WebSocket signaling server:

```
┌───────────────────────────────────────────────────────────────┐
│                         EC2 Server                            │
│                                                               │
│  ┌──────────────────┐     ┌────────────────────────────────┐  │
│  │  Flask :5000     │     │  GStreamer Process              │  │
│  │                  │     │                                │  │
│  │  - Auth / APIs   │     │  webrtcbin ← UDP (RTP/RTCP)    │  │
│  │  - Socket.IO     │◄────│  appsink  → Python callback    │  │
│  │  - Dashboard     │emit │      ↓                         │  │
│  │                  │─────│  Face Recognition (OpenCV/dlib) │  │
│  └──────────────────┘     │      ↓                         │  │
│           ▲               │  Socket.IO client → Flask      │  │
│           │               └────────────────────────────────┘  │
│      Browser                         ▲                        │
│    (Live Monitor)                    │ WebRTC (UDP)            │
└──────────────────────────────────────┼────────────────────────┘
                                       │
                                 Windows Client
                                (Camera Stream)
```

## Data Flow

```
1. Windows Client: GStreamer/aiortc captures & sends camera
     │
     ▼ WebRTC (VP8/H.264 over UDP, SRTP encrypted)
2. EC2 GStreamer: webrtcbin receives RTP packets
     │
     ▼ GStreamer pipeline decodes to raw video
3. appsink: Grabs raw frames → Python callback
     │
     ├──► Face Recognition (dlib) → Attendance → PostgreSQL
     │
     ▼ JPEG encode → base64
4. Socket.IO client → Flask :5000 → Browser
```

## Why GStreamer is Fastest

| Stage | aiortc (Python) | GStreamer (C) |
|-------|----------------|---------------|
| RTP receive | Python asyncio | C (libnice) |
| SRTP decrypt | Python (pylibsrtp) | C (libsrtp) |
| VP8 decode | Python (libvpx binding) | C (gst-libvpx) |
| Frame to numpy | `frame.to_ndarray()` | `appsink` → numpy |
| **Overhead** | ~20-50ms | ~5-10ms |

GStreamer's entire media pipeline runs in **native C code**. Python only touches the frame at the `appsink` callback — for face recognition and Socket.IO forwarding.

## Signaling Flow

GStreamer's `webrtcbin` uses **WebSocket** for signaling (not HTTP POST):

```
Windows Client                    EC2 Server
     │                                │
     ├──WS connect──────────────────► │
     │                                │
     ├──SDP offer───────────────────► │  (JSON over WebSocket)
     │                                │
     ◄──SDP answer──────────────────┤ │
     │                                │
     ├──ICE candidates──────────────► │  (trickle ICE)
     ◄──ICE candidates──────────────┤ │
     │                                │
     ╠══RTP media (UDP)═════════════╣ │  (direct or via TURN)
```

## GStreamer Pipeline (Server Side)

```
webrtcbin name=recv
    → rtpvp8depay → vp8dec
    → videoconvert → video/x-raw,format=BGR
    → appsink name=sink emit-signals=true sync=false
```

## File Structure After Integration

```
surveillx-backend/
├── app.py                     ← Flask (unchanged)
├── gst_streaming_server.py    ← NEW: GStreamer + WebSocket signaling
├── api/                       ← Flask blueprints (unchanged)
├── services/
│   └── stream_handler.py      ← Socket.IO namespace (unchanged)
├── static/js/
│   └── app.js                 ← Browser code (unchanged)
```
