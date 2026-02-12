# SurveillX Windows Client — User Manual

## Quick Start

### 1. Install Python Dependencies
Open **Command Prompt** or **PowerShell** and run:
```cmd
pip install opencv-python websockets
```

### 2. Download the Client
Download `client.py` from the repository:
```
docs/streaming/gstreamer/client.py
```

### 3. Run the Client
```cmd
python client.py --server surveillx.duckdns.org --camera 0
```

---

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--server` | `surveillx.duckdns.org` | Server hostname (no `ws://` prefix) |
| `--camera` | `0` | Camera index (0 = default webcam) |
| `--mode` | `jpegws` | Streaming mode: `jpegws` or `fastrtc` |

### Examples

**Default mode (JPEG WebSocket, port 8443):**
```cmd
python client.py --server surveillx.duckdns.org --camera 0 --mode jpegws
```

**FastRTC mode (port 8080):**
```cmd
python client.py --server surveillx.duckdns.org --camera 0 --mode fastrtc
```

**Use a different camera:**
```cmd
python client.py --camera 1
```

---

## Streaming Modes

### JPEG WebSocket (default)
- **Port:** 8443
- **How it works:** Captures webcam → JPEG encode → WebSocket → Server → Browser
- **Quality:** JPEG quality 85 (configurable in client.py)
- **Best for:** General use, reliable

### FastRTC
- **Port:** 8080
- **How it works:** Same JPEG approach, different server (FastAPI/uvicorn)
- **Best for:** Alternative server, redundancy

> **Important:** The client mode must match the dashboard mode. If the dashboard is set to "FastRTC", run the client with `--mode fastrtc`.

### Dual-Mode (Both at once)

To feed **both** servers simultaneously (required for auto-switch):

```cmd
python client_dual.py --server surveillx.duckdns.org --camera 0
```

Or double-click **`start_dual.bat`**.

This captures the camera once and sends frames to both port 8443 and 8080. The dashboard can then switch between modes instantly since both are receiving frames.

---

## Tuning Video Quality

Edit these values at the top of `client.py`:

```python
JPEG_QUALITY = 85       # 1-100 (higher = better quality, more bandwidth)
TARGET_FPS = 15         # Frames per second (lower = less bandwidth)
FRAME_WIDTH = 1280      # Capture width
FRAME_HEIGHT = 720      # Capture height
```

| Setting | Low Bandwidth | Balanced | High Quality |
|---------|--------------|----------|--------------|
| JPEG_QUALITY | 60 | 85 | 95 |
| TARGET_FPS | 10 | 15 | 25 |
| Resolution | 640×480 | 1280×720 | 1920×1080 |

---

## Troubleshooting

### "Cannot open camera 0"
- Another app may be using the camera (close Zoom, Teams, etc.)
- Try `--camera 1` to use a different camera

### Connection fails / keeps retrying
- Check your internet connection
- Verify the server is running (`surveillx.duckdns.org`)
- Make sure you're using the correct `--mode` (matching port must be open)

### High latency (>500ms)
- Lower `JPEG_QUALITY` to 70
- Lower `TARGET_FPS` to 10
- Lower resolution to 640×480
- Try the other streaming mode (jpegws vs fastrtc)

### Video appears but is laggy
- Close other bandwidth-heavy apps
- Use a wired connection instead of WiFi

---

## Dashboard Features

On the **Live Monitor** page in the browser dashboard:

- **Mode Selector:** Switch between JPEG WebSocket and FastRTC
- **Auto-Switch Toggle:** Automatically uses the lower-latency mode (checks every 30s)
- **Stream Status:** Shows connection, resolution, FPS, frame count, and latency
- **Fullscreen:** Click the Fullscreen button to view the stream in full screen
- **Capture Snapshot:** Save a frame as an image

---

## GStreamer Note

If you previously installed GStreamer on Windows, you can **uninstall it** — it is no longer used. The current approach uses simple JPEG encoding with OpenCV, which is built into the `opencv-python` package.
