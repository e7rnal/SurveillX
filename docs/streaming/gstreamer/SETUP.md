# GStreamer + webrtcbin — Setup Guide

## What is GStreamer?

[GStreamer](https://gstreamer.freedesktop.org/) is a C-based multimedia framework. Its `webrtcbin` plugin provides native WebRTC support — no Python event loop dependency, hardware-accelerated encoding/decoding, and the **lowest possible latency**.

## Prerequisites

- Ubuntu 22.04+ (our EC2)
- Python 3.10+
- GStreamer 1.20+

## Step 1: Install GStreamer and Plugins

```bash
# Core GStreamer
sudo apt-get update
sudo apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-nice \
    gstreamer1.0-libav

# WebRTC plugin (webrtcbin)
sudo apt-get install -y \
    gstreamer1.0-plugins-bad

# Python bindings (PyGObject + GStreamer introspection)
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gst-plugins-bad-1.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-nice-0.1
```

## Step 2: Verify Installation

```bash
# Check GStreamer version
gst-inspect-1.0 --version

# Check webrtcbin is available
gst-inspect-1.0 webrtcbin

# Check Python bindings
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print('GStreamer OK')"

# Check webrtcbin from Python
python3 -c "
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)
factory = Gst.ElementFactory.find('webrtcbin')
print(f'webrtcbin: {factory is not None}')
"
```

## Step 3: Install Python Dependencies

```bash
cd /home/ubuntu/surveillx-backend
source venv/bin/activate

# websockets for signaling
pip install websockets aiohttp
```

> **Note:** GStreamer's Python bindings (`gi`) are system-level packages, not pip packages. They're installed via `apt` in Step 1.

## Step 4: Ports

Same ports as FastRTC:

| Port | Protocol | Purpose | Status |
|------|----------|---------|--------|
| 5000 | TCP | Flask (main app) | ✅ Open |
| 8443 | TCP | WebSocket signaling (GStreamer) | ❌ **Need to open** |
| 3478 | UDP/TCP | coturn TURN server | ✅ Open |
| 10000-60000 | UDP | WebRTC media (RTP) | ✅ Open |

```bash
# Open port 8443 in AWS Security Group
aws ec2 authorize-security-group-ingress \
  --group-id <YOUR_SG_ID> \
  --protocol tcp \
  --port 8443 \
  --cidr 0.0.0.0/0
```

## Step 5: coturn (TURN Server)

Same as FastRTC approach — already configured:
```bash
sudo turnserver -c /etc/turnserver.conf -o
```

## Windows Client Dependencies

The Windows client for GStreamer can use either:
1. **GStreamer on Windows** (native, lowest latency) — requires Windows GStreamer MSI installer
2. **aiortc** (Python, easier) — same as FastRTC client (`pip install aiortc`)

For option 1:
- Download [GStreamer for Windows](https://gstreamer.freedesktop.org/download/) (MSVC 64-bit)
- Install with all plugins checked
- Add to PATH: `C:\gstreamer\1.0\msvc_x86_64\bin`

## Next Steps

→ Read [ARCHITECTURE.md](./ARCHITECTURE.md) for data flow
→ Read [IMPLEMENTATION.md](./IMPLEMENTATION.md) for step-by-step guide
