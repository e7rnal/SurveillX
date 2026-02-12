# FastRTC — Setup Guide

## What is FastRTC?

[FastRTC](https://fastrtc.org) is a Python library (released March 2025) that simplifies WebRTC streaming. It's built on **FastAPI** and wraps `aiortc` with a proper async event loop — solving the exact problem we had with Flask + aiortc.

## Prerequisites

- Python 3.10+ (already on EC2)
- pip / venv

## Step 1: Install Dependencies

```bash
# On EC2 server
cd /home/ubuntu/surveillx-backend
source venv/bin/activate

pip install fastrtc
pip install fastapi uvicorn
```

**Note:** FastRTC pulls in `aiortc` automatically, but runs it inside FastAPI's async loop — so `track.recv()` works correctly.

## Step 2: System Dependencies

FastRTC uses the same native libs as aiortc. These are already installed:

```bash
# Already installed on our EC2:
# - libavcodec, libavformat (from ffmpeg/libav)
# - libopus, libvpx
# If missing:
sudo apt-get install -y libavdevice-dev libavfilter-dev libopus-dev libvpx-dev
```

## Step 3: Ports

| Port | Protocol | Purpose | Status |
|------|----------|---------|--------|
| 5000 | TCP | Flask (main app) | ✅ Open |
| 8080 | TCP | FastRTC/FastAPI (WebRTC signaling) | ❌ **Need to open** |
| 3478 | UDP/TCP | coturn TURN server | ✅ Open |
| 10000-60000 | UDP | WebRTC media (RTP) | ✅ Open |

```bash
# Open port 8080 in AWS Security Group
aws ec2 authorize-security-group-ingress \
  --group-id <YOUR_SG_ID> \
  --protocol tcp \
  --port 8080 \
  --cidr 0.0.0.0/0
```

## Step 4: Verify Installation

```bash
python3 -c "import fastrtc; print(f'FastRTC {fastrtc.__version__} OK')"
python3 -c "from fastrtc import Stream; print('Stream class available')"
```

## Step 5: coturn (TURN Server)

Already configured. Credentials:
- URL: `turn:13.205.156.238:3478`
- Username: `surveillx`
- Credential: `Vishu@9637`

Start coturn:
```bash
sudo turnserver -c /etc/turnserver.conf -o
```

## Windows Client Dependencies

```bash
pip install aiortc opencv-python requests av
```

## Next Steps

→ Read [ARCHITECTURE.md](./ARCHITECTURE.md) for how FastRTC integrates with Flask
→ Read [IMPLEMENTATION.md](./IMPLEMENTATION.md) for step-by-step code guide
