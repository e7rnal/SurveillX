# SurveillX Streaming — Research & Implementation Guides

Two WebRTC approaches for streaming video from Windows client to EC2 server.

## Why WebRTC?

| Metric | HTTP POST (old) | WebRTC |
|--------|----------------|--------|
| Protocol | TCP | UDP |
| Latency | 200-400ms/frame | 50-100ms |
| Encoding | Base64 JPEG (~30% bloat) | VP8/H.264 (native) |
| Connection | New per frame | Persistent |
| **E2E attendance** | **~400-600ms** | **~180-320ms** |

## Two Approaches

### 1. FastRTC (`fastrtc/`)
- **What:** Modern Python WebRTC library (2025), built on FastAPI
- **Latency:** ~180-320ms end-to-end
- **Effort:** Medium
- **Best for:** Quick iteration, Python-native, easy to debug

### 2. GStreamer + webrtcbin (`gstreamer/`)
- **What:** Native C-based media pipeline with WebRTC plugin
- **Latency:** ~160-300ms end-to-end (lowest possible)
- **Effort:** High
- **Best for:** Production deployment, hardware acceleration, maximum performance

## Decision Guide

| If you want... | Choose |
|----------------|--------|
| Fastest to implement | FastRTC |
| Lowest latency | GStreamer |
| Easiest debugging | FastRTC |
| Production-grade | GStreamer |
| Python-only stack | FastRTC |

## Previous Failure: aiortc + Flask

We tried `aiortc` with Flask — it's a **known broken combination**. `track.recv()` never fires because Flask's synchronous WSGI model starves the asyncio event loop. Both approaches below avoid this:
- FastRTC uses **FastAPI** (async-native)
- GStreamer uses **native C code** (no Python event loop dependency)

## Architecture (both approaches)

```
Windows Client ──WebRTC──► EC2 Server ──Socket.IO──► Browser Dashboard
                              │
                         Face Recognition
                              │
                         PostgreSQL (attendance)
```
