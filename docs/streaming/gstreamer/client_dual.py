"""
SurveillX Dual-Mode Client — Sends to BOTH servers simultaneously
Captures webcam once and sends JPEG frames to both:
  - JPEG WebSocket hub (port 8443)
  - FastRTC server (port 8080)

This enables auto-switch on the dashboard by feeding both servers.

Usage:
    python client_dual.py --server surveillx.servebeer.com --camera 0

Requires:
    pip install opencv-python websockets
"""
import argparse
import asyncio
import base64
import json
import logging
import time

import cv2
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("surveillx-dual")

JPEG_QUALITY = 85
TARGET_FPS = 15
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

SERVERS = {
    "jpegws":  {"port": 8443, "ws_path": ""},
    "fastrtc": {"port": 8080, "ws_path": "/ws/stream"},
}


class StreamConnection:
    """Manages a WebSocket connection to one server."""
    def __init__(self, name, server_host, port, ws_path):
        self.name = name
        self.server_host = server_host
        self.url = f"ws://{server_host}:{port}{ws_path}"
        self.ws = None
        self.connected = False
        self.frame_count = 0

    async def connect(self, width, height, fps):
        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(self.url, ping_interval=20, ping_timeout=10, max_size=2*1024*1024),
                timeout=5
            )
            await self.ws.send(json.dumps({
                "type": "hello",
                "mode": "jpeg",
                "width": width,
                "height": height,
                "fps": fps,
            }))
            self.connected = True
            self.frame_count = 0
            logger.info(f"✅ {self.name} connected: {self.url}")
        except Exception as e:
            logger.warning(f"❌ {self.name} connect failed: {e}")
            self.connected = False
            self.ws = None

    async def send_frame(self, frame_b64, camera_id, timestamp, width, height):
        if not self.connected or not self.ws:
            return
        try:
            await self.ws.send(json.dumps({
                "type": "frame",
                "frame": frame_b64,
                "camera_id": camera_id,
                "timestamp": timestamp,
                "width": width,
                "height": height,
            }))
            self.frame_count += 1
        except Exception as e:
            logger.warning(f"{self.name} send error: {e}")
            self.connected = False
            self.ws = None

    async def close(self):
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None
            self.connected = False


async def stream_dual(server_host: str, camera_index: int):
    """Capture frames once, broadcast to both servers."""
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        logger.error(f"Cannot open camera {camera_index}")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info(f"📷 Camera {camera_index}: {w}x{h}")

    # Create connections for both servers
    connections = {
        name: StreamConnection(name, server_host, cfg["port"], cfg["ws_path"])
        for name, cfg in SERVERS.items()
    }

    frame_interval = 1.0 / TARGET_FPS
    total_frames = 0

    while True:
        # Connect any disconnected servers
        for conn in connections.values():
            if not conn.connected:
                await conn.connect(w, h, TARGET_FPS)

        if not any(c.connected for c in connections.values()):
            logger.warning("No servers connected, retrying in 3s...")
            await asyncio.sleep(3)
            continue

        t_start = time.time()
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue

        # Encode once
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        timestamp = str(time.time())

        total_frames += 1

        # Send to all connected servers simultaneously
        tasks = [
            conn.send_frame(frame_b64, 1, timestamp, w, h)
            for conn in connections.values()
            if conn.connected
        ]
        await asyncio.gather(*tasks)

        if total_frames == 1:
            active = [c.name for c in connections.values() if c.connected]
            logger.info(f"🎉 First frame sent to: {', '.join(active)} ({len(buffer)} bytes)")

        if total_frames % 100 == 0:
            status = " | ".join(f"{c.name}: {c.frame_count} frames" for c in connections.values())
            logger.info(f"[{total_frames}] {status}")

        # Throttle
        elapsed = time.time() - t_start
        sleep_time = max(0, frame_interval - elapsed)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SurveillX Dual-Mode Client")
    parser.add_argument("--server", default="surveillx.servebeer.com")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    logger.info("=== SurveillX Dual-Mode Client ===")
    logger.info(f"Server: {args.server} | Camera: {args.camera}")
    logger.info(f"Sending to: JPEG-WS (:{SERVERS['jpegws']['port']}) + FastRTC (:{SERVERS['fastrtc']['port']})")

    try:
        asyncio.run(stream_dual(args.server, args.camera))
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
