# SurveillX Windows Streaming Client - Development Guide

## Overview

Build a professional Windows streaming client (`SurveillX.exe`) using GStreamer + WebRTC for ultra-low latency video streaming (<50ms). This document provides complete specifications for development in Cursor IDE.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SurveillX.exe (Windows)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │   Camera    │→ │  GStreamer   │→ │    WebRTC         │   │
│  │   Capture   │  │  Pipeline    │  │    Encoder        │   │
│  └─────────────┘  └──────────────┘  └───────────────────┘   │
│         ↓                                    ↓              │
│  ┌─────────────┐                    ┌───────────────────┐   │
│  │    Stats    │                    │   Signaling       │   │
│  │   Display   │                    │   (WebSocket)     │   │
│  └─────────────┘                    └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    surveillx.duckdns.org:5000
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Main application |
| GUI | PyQt6 / CustomTkinter | Professional UI |
| Camera | GStreamer 1.0 | Low-latency capture |
| Streaming | aiortc / GStreamer WebRTC | WebRTC connection |
| Packaging | PyInstaller | Build .exe |
| Config | JSON / YAML | Settings storage |

---

## Server Connection

```
Server URL: http://surveillx.duckdns.org:5000
WebRTC Endpoint: /webrtc/streamer
Health Check: /health
WebSocket: /stream (Socket.IO)

TURN Server (if needed):
  Host: surveillx.duckdns.org:3478
  Username: surveillx
  Password: surveillx2026
```

---

## Required Features

### 1. Main Window
- Camera preview (local)
- Connection status indicator (green/yellow/red)
- Real-time statistics panel
- Start/Stop streaming button
- Settings button
- Minimize to system tray

### 2. Statistics Display
- **Latency**: Round-trip time in ms (target: <50ms)
- **FPS**: Current frames per second
- **Bitrate**: Current upload speed (Kbps/Mbps)
- **Dropped Frames**: Count of dropped frames
- **Connection Quality**: Excellent/Good/Poor indicator
- **Uptime**: Stream duration

### 3. Settings Panel
- **Camera Selection**: Dropdown of available cameras
- **Resolution**: 640x480, 1280x720, 1920x1080
- **FPS**: 15, 24, 30, 60
- **Bitrate**: Auto, 500Kbps, 1Mbps, 2Mbps, 4Mbps
- **Encoder**: H.264, VP8, VP9
- **Server URL**: Editable with test button
- **Auto-reconnect**: Enable/disable
- **Start minimized**: Enable/disable
- **Start on Windows boot**: Enable/disable

### 4. System Tray
- Icon shows connection status
- Right-click menu: Start/Stop, Settings, Exit
- Double-click: Show main window

---

## Project Structure

```
SurveillX-Client/
├── src/
│   ├── main.py              # Entry point
│   ├── app.py               # Main application class
│   ├── ui/
│   │   ├── main_window.py   # Main window UI
│   │   ├── settings_dialog.py
│   │   ├── stats_widget.py
│   │   └── tray_icon.py
│   ├── streaming/
│   │   ├── camera.py        # Camera capture (GStreamer)
│   │   ├── webrtc.py        # WebRTC connection
│   │   ├── signaling.py     # Server signaling
│   │   └── encoder.py       # Video encoding
│   ├── utils/
│   │   ├── config.py        # Configuration management
│   │   ├── logger.py        # Logging setup
│   │   └── stats.py         # Statistics calculator
│   └── resources/
│       ├── icons/           # App icons
│       └── styles/          # CSS/QSS styles
├── config/
│   └── default_settings.json
├── requirements.txt
├── build.py                 # PyInstaller build script
└── README.md
```

---

## Core Code Specifications

### main.py
```python
"""
SurveillX Windows Streaming Client
Entry point for the application
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from app import SurveillXApp

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('surveillx.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("SurveillX")
    app.setOrganizationName("SurveillX")
    
    # Create main window
    window = SurveillXApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### streaming/camera.py (GStreamer)
```python
"""
GStreamer camera capture with low-latency pipeline
"""
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

class CameraCapture:
    def __init__(self, device_index=0, width=640, height=480, fps=30):
        Gst.init(None)
        
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.pipeline = None
        self.on_frame = None
        
    def build_pipeline(self):
        """Build GStreamer pipeline for low-latency capture"""
        # Windows DirectShow source
        pipeline_str = f"""
            ksvideosrc device-index={self.device_index} do-timestamp=true !
            video/x-raw,width={self.width},height={self.height},framerate={self.fps}/1 !
            videoconvert !
            queue max-size-buffers=1 leaky=downstream !
            appsink name=sink emit-signals=true sync=false
        """
        
        self.pipeline = Gst.parse_launch(pipeline_str)
        
        # Get appsink and connect signal
        sink = self.pipeline.get_by_name('sink')
        sink.connect('new-sample', self._on_new_sample)
        
        return self.pipeline
    
    def _on_new_sample(self, sink):
        """Handle new frame from camera"""
        sample = sink.emit('pull-sample')
        if sample and self.on_frame:
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            self.on_frame(buffer, caps)
        return Gst.FlowReturn.OK
    
    def start(self):
        """Start capture"""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.PLAYING)
    
    def stop(self):
        """Stop capture"""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
    
    @staticmethod
    def list_cameras():
        """List available cameras on Windows"""
        # Use DirectShow device enumeration
        cameras = []
        # Implementation using pygrabber or similar
        return cameras
```

### streaming/webrtc.py
```python
"""
WebRTC connection manager using aiortc
"""
import asyncio
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc import RTCConfiguration, RTCIceServer

class WebRTCStreamer:
    def __init__(self, server_url="http://surveillx.duckdns.org:5000"):
        self.server_url = server_url
        self.pc = None
        self.connected = False
        self.on_stats = None
        self.on_state_change = None
        
    def get_ice_config(self):
        """Get ICE servers configuration"""
        return RTCConfiguration(iceServers=[
            RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
            RTCIceServer(
                urls=["turn:surveillx.duckdns.org:3478"],
                username="surveillx",
                credential="surveillx2026"
            )
        ])
    
    async def connect(self, video_track):
        """Establish WebRTC connection"""
        self.pc = RTCPeerConnection(configuration=self.get_ice_config())
        
        @self.pc.on("connectionstatechange")
        async def on_state():
            state = self.pc.connectionState
            self.connected = state == "connected"
            if self.on_state_change:
                self.on_state_change(state)
        
        # Add video track
        self.pc.addTrack(video_track)
        
        # Create and send offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        # Send to signaling server
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/webrtc/streamer",
                json={
                    "sdp": self.pc.localDescription.sdp,
                    "type": self.pc.localDescription.type
                }
            ) as resp:
                answer = await resp.json()
                await self.pc.setRemoteDescription(
                    RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
                )
        
        return True
    
    async def get_stats(self):
        """Get connection statistics"""
        if not self.pc:
            return None
        
        stats = await self.pc.getStats()
        result = {
            "rtt": 0,
            "bitrate": 0,
            "fps": 0,
            "packets_sent": 0,
            "packets_lost": 0
        }
        
        for report in stats.values():
            if report.type == "outbound-rtp" and report.kind == "video":
                result["packets_sent"] = report.packetsSent
                result["bitrate"] = getattr(report, 'bytesSent', 0) * 8
            if report.type == "remote-inbound-rtp":
                result["rtt"] = getattr(report, 'roundTripTime', 0) * 1000
                result["packets_lost"] = getattr(report, 'packetsLost', 0)
        
        return result
    
    async def disconnect(self):
        """Close connection"""
        if self.pc:
            await self.pc.close()
            self.pc = None
            self.connected = False
```

### utils/config.py
```python
"""
Configuration management
"""
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "server": {
        "url": "http://surveillx.duckdns.org:5000",
        "auto_reconnect": True,
        "reconnect_interval": 5
    },
    "camera": {
        "device_index": 0,
        "width": 640,
        "height": 480,
        "fps": 30
    },
    "encoder": {
        "codec": "H264",
        "bitrate": 2000000,
        "keyframe_interval": 30
    },
    "ui": {
        "start_minimized": False,
        "minimize_to_tray": True,
        "show_preview": True,
        "dark_mode": True
    },
    "startup": {
        "run_on_boot": False,
        "auto_start_stream": False
    }
}

class Config:
    def __init__(self):
        self.config_dir = Path(os.environ.get('APPDATA', '.')) / 'SurveillX'
        self.config_file = self.config_dir / 'settings.json'
        self.config = DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        """Load config from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                saved = json.load(f)
                self._merge(self.config, saved)
    
    def save(self):
        """Save config to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _merge(self, base, override):
        """Deep merge configs"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, *keys):
        """Get nested config value"""
        value = self.config
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value
    
    def set(self, *keys, value):
        """Set nested config value"""
        config = self.config
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        config[keys[-1]] = value
        self.save()
```

---

## Build Configuration

### requirements.txt
```
PyQt6>=6.5.0
aiortc>=1.6.0
aiohttp>=3.9.0
PyGObject>=3.44.0
opencv-python>=4.8.0
numpy>=1.24.0
pyinstaller>=6.0.0
```

### build.py (PyInstaller)
```python
"""
Build script for creating SurveillX.exe
"""
import PyInstaller.__main__
import os

def build():
    PyInstaller.__main__.run([
        'src/main.py',
        '--name=SurveillX',
        '--onefile',
        '--windowed',
        '--icon=src/resources/icons/surveillx.ico',
        '--add-data=src/resources;resources',
        '--add-data=config;config',
        '--hidden-import=aiortc',
        '--hidden-import=aiohttp',
        '--hidden-import=gi',
        '--hidden-import=PyQt6',
        '--collect-all=aiortc',
        '--collect-binaries=gi',
        '--clean',
        '--noconfirm'
    ])

if __name__ == "__main__":
    build()
```

---

## GStreamer Windows Installation

1. Download from: https://gstreamer.freedesktop.org/download/
2. Install both **Runtime** and **Development** packages (MSVC 64-bit)
3. Add to PATH: `C:\gstreamer\1.0\msvc_x86_64\bin`
4. Set environment variable:
   ```
   GST_PLUGIN_PATH=C:\gstreamer\1.0\msvc_x86_64\lib\gstreamer-1.0
   ```

---

## UI Design Specifications

### Color Scheme (Dark Mode)
```css
/* Main colors */
--bg-primary: #1a1a2e;
--bg-secondary: #16213e;
--bg-tertiary: #0f3460;
--accent: #e94560;
--accent-hover: #ff6b6b;
--text-primary: #ffffff;
--text-secondary: #a0a0a0;
--success: #00d26a;
--warning: #ffc107;
--error: #dc3545;
```

### Status Indicators
- 🟢 Connected (streaming)
- 🟡 Connecting / Reconnecting
- 🔴 Disconnected / Error
- ⚪ Idle (not started)

---

## Future Features (Roadmap)

| Priority | Feature | Description |
|----------|---------|-------------|
| P1 | Multi-camera | Stream from multiple cameras |
| P1 | Audio support | Include microphone audio |
| P2 | Recording | Local recording while streaming |
| P2 | Bandwidth adaptive | Auto-adjust quality |
| P3 | Hardware encoding | NVENC/QuickSync support |
| P3 | Screen share | Capture desktop/window |
| P3 | Remote config | Server-pushed settings |

---

## Testing Checklist

- [ ] Camera detection works
- [ ] Preview shows local video
- [ ] WebRTC connection establishes
- [ ] Stats display correctly (latency, FPS, bitrate)
- [ ] Reconnection works on disconnect
- [ ] Settings persist across restarts
- [ ] System tray works
- [ ] .exe builds successfully
- [ ] .exe runs on clean Windows install

---

## Cursor IDE Prompt

Copy this prompt into Cursor IDE to start development:

```
I need to build a professional Windows streaming client application called SurveillX.

Requirements:
1. Python 3.11+ with PyQt6 for GUI
2. GStreamer for low-latency camera capture
3. aiortc for WebRTC streaming
4. Professional dark-mode UI with:
   - Camera preview
   - Real-time stats (latency, FPS, bitrate, dropped frames)
   - Connection status indicator
   - Settings panel (camera, resolution, FPS, bitrate, encoder)
   - System tray with status icon

Server details:
- URL: http://surveillx.duckdns.org:5000
- WebRTC endpoint: POST /webrtc/streamer
- TURN server: surveillx.duckdns.org:3478 (user: surveillx, pass: surveillx2026)

Key features:
- Target latency: <50ms
- Auto-reconnect on disconnect
- Settings persistence in %APPDATA%/SurveillX
- Build as single .exe using PyInstaller

Start by creating the project structure and implementing the camera capture with GStreamer.
```
