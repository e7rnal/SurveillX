"""
SurveillX FastRTC Streaming Server — Low-Latency WebSocket Hub
Alternative streaming server on port 8080.
Same JPEG-over-WebSocket approach as the main hub (port 8443).

Usage:
    python fastrtc_server.py
    # Or with uvicorn:
    uvicorn fastrtc_server:app --host 0.0.0.0 --port 8080

Architecture:
    Windows Client --WS frame--> This server --WS broadcast--> Browser(s)
"""
import asyncio
import json
import base64
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/fastrtc_streaming.log"),
    ],
)
logger = logging.getLogger("fastrtc")

# ---------- FastAPI App ----------
app = FastAPI(title="SurveillX FastRTC Streaming Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- Connection Registry ----------
viewers: set[WebSocket] = set()
streamer: WebSocket | None = None
frame_count = 0
last_frame_data: str | None = None

# Latency tracking
latency_samples: list[float] = []
MAX_LATENCY_SAMPLES = 50


async def broadcast_to_viewers(message: str):
    """Send a message to all connected browser viewers — parallel for lowest latency."""
    if not viewers:
        return
    async def _safe_send(ws):
        try:
            await ws.send_text(message)
        except Exception:
            return ws
        return None
    results = await asyncio.gather(*[_safe_send(ws) for ws in viewers.copy()])
    dead = {ws for ws in results if ws is not None}
    viewers.difference_update(dead)


# ---------- REST Endpoints ----------
@app.get("/stats")
async def stats():
    """Return server stats for mode comparison."""
    avg_latency = sum(latency_samples) / len(latency_samples) if latency_samples else 0
    return {
        "mode": "fastrtc",
        "port": 8080,
        "streaming": streamer is not None,
        "frames_processed": frame_count,
        "viewers": len(viewers),
        "avg_latency_ms": round(avg_latency, 1),
        "uptime": time.time(),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "fastrtc"}


# ---------- WebSocket Handlers ----------
@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    """Handle camera client sending JPEG frames."""
    global streamer, frame_count, last_frame_data

    await websocket.accept()

    try:
        # Wait for hello handshake
        data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        if data.get("type") != "hello" or data.get("mode") != "jpeg":
            await websocket.close(1008, "Expected {type: 'hello', mode: 'jpeg'}")
            return

        streamer = websocket
        frame_count = 0
        w = data.get("width", 0)
        h = data.get("height", 0)
        fps = data.get("fps", 0)
        logger.info(f"📷 Camera client connected: {w}x{h} @ {fps}fps")
        await websocket.send_json({"type": "ready", "status": "ok"})

        while True:
            msg = await websocket.receive_json()
            if msg.get("type") != "frame":
                continue

            frame_b64 = msg.get("frame", "")
            if not frame_b64:
                continue

            frame_count += 1

            if frame_count == 1:
                raw = base64.b64decode(frame_b64)
                logger.info(f"🎉 FIRST FRAME! size={len(raw)} bytes, viewers={len(viewers)}")

            # Prepare broadcast with server timestamp for latency measurement
            broadcast_msg = json.dumps({
                "type": "frame",
                "frame": frame_b64,
                "camera_id": msg.get("camera_id", 1),
                "timestamp": msg.get("timestamp", ""),
                "server_time": time.time() * 1000,
                "width": msg.get("width", 0),
                "height": msg.get("height", 0),
            })

            last_frame_data = broadcast_msg
            await broadcast_to_viewers(broadcast_msg)

            if frame_count % 200 == 0:
                logger.info(f"Processed {frame_count} frames, viewers={len(viewers)}")

    except WebSocketDisconnect:
        logger.info("Camera client disconnected")
    except Exception as e:
        logger.error(f"Stream error: {e}")
    finally:
        streamer = None
        frame_count = 0
        try:
            await broadcast_to_viewers(json.dumps({"type": "stream_ended"}))
        except Exception:
            pass
        logger.info("Camera client session ended")


@app.websocket("/ws/view")
async def ws_view(websocket: WebSocket):
    """Handle browser viewer receiving frames."""
    await websocket.accept()
    viewers.add(websocket)
    logger.info(f"👁 Viewer connected (total: {len(viewers)})")

    # Send current status
    await websocket.send_json({
        "type": "status",
        "streaming": streamer is not None,
        "frames_processed": frame_count,
    })

    # Send last frame if available
    if last_frame_data:
        try:
            await websocket.send_text(last_frame_data)
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_json()
            # Handle ping for latency measurement
            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "client_time": data.get("client_time", 0),
                    "server_time": time.time() * 1000,
                })
            elif data.get("type") == "latency_report":
                latency_ms = data.get("latency_ms", 0)
                latency_samples.append(latency_ms)
                if len(latency_samples) > MAX_LATENCY_SAMPLES:
                    latency_samples.pop(0)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        viewers.discard(websocket)
        logger.info(f"👁 Viewer disconnected (total: {len(viewers)})")


# ---------- Startup ----------
@app.on_event("startup")
async def startup():
    import os
    os.makedirs("logs", exist_ok=True)
    logger.info("✅ FastRTC streaming server starting on port 8080")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
