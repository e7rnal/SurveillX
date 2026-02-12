# SurveillX Streaming — Architecture & Setup

## Current Approach: JPEG-over-WebSocket (Dual-Mode)

Video frames are captured as JPEG on the Windows client and sent over WebSocket to the EC2 server, which broadcasts them to browser viewers.

```
Windows Client ──JPEG/WS──► EC2 Server Hub ──JPEG/WS──► Browser Dashboard
                               │
                          Face Recognition
                               │
                          PostgreSQL (attendance)
```

## Two Server Modes

| Feature | JPEG WebSocket | FastRTC |
|---------|---------------|---------|
| Port | 8443 | 8080 |
| Server | `gst_streaming_server.py` | `fastrtc_server.py` |
| Framework | `websockets` lib | FastAPI + uvicorn |
| Encoding | JPEG (client-side) | JPEG (client-side) |
| Latency | ~200-400ms | ~200-400ms |

Both accept the same JPEG frames from the client. The dashboard can switch between them (or auto-switch based on latency).

## Client Files

| File | Purpose |
|------|---------|
| `gstreamer/client.py` | Single-mode client (`--mode jpegws` or `--mode fastrtc`) |
| `gstreamer/client_dual.py` | Dual-mode client (sends to both servers simultaneously) |
| `gstreamer/start_dual.bat` | Windows launcher for dual-mode |

See [CLIENT_MANUAL.md](./CLIENT_MANUAL.md) for full usage instructions.

## Running the Servers

```bash
# On EC2
cd /home/ubuntu/surveillx-backend
source venv/bin/activate

# Start JPEG-WS hub (port 8443)
python gst_streaming_server.py &

# Start FastRTC hub (port 8080)
python fastrtc_server.py &

# Start Flask dashboard (port 5000)
python app.py &
```

## Historical Note

Previous approaches (WebRTC via aiortc, GStreamer pipelines) were abandoned due to VP8 codec quality issues and complexity. The JPEG-over-WebSocket approach provides clear video with acceptable latency. Reference implementations are preserved in `fastrtc/` for documentation purposes.
