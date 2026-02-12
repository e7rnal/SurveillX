"""
SurveillX Windows Client — Dual-Mode JPEG Streaming
Sends webcam frames as JPEG over WebSocket.
Supports both JPEG-WS (port 8443) and FastRTC (port 8080) modes.

Usage:
    python client.py --server surveillx.servebeer.com --camera 0 --mode jpegws
    python client.py --server surveillx.servebeer.com --camera 0 --mode fastrtc

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
logger = logging.getLogger("surveillx-client")

# Streaming settings
JPEG_QUALITY = 85       # 1-100, higher = better quality
TARGET_FPS = 15         # Target frames per second
FRAME_WIDTH = 1280      # Capture width
FRAME_HEIGHT = 720      # Capture height

# Mode configuration
MODES = {
    "jpegws": {"port": 8443, "ws_path": ""},
    "fastrtc": {"port": 8080, "ws_path": "/ws/stream"},
}


async def stream(server_host: str, camera_index: int, mode: str):
    """Capture webcam frames and send as JPEG over WebSocket."""
    mode_config = MODES.get(mode)
    if not mode_config:
        logger.error(f"Unknown mode: {mode}. Use 'jpegws' or 'fastrtc'")
        return

    server_url = f"ws://{server_host}:{mode_config['port']}{mode_config['ws_path']}"

    # Open camera
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        logger.error(f"Cannot open camera {camera_index}")
        return

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info(f"Camera {camera_index} opened: {actual_w}x{actual_h}")
    logger.info(f"Mode: {mode} → {server_url}")

    frame_interval = 1.0 / TARGET_FPS
    frame_count = 0
    retry_count = 0
    max_retries = 10

    while retry_count < max_retries:
        try:
            logger.info(f"Connecting to {server_url}...")
            async with websockets.connect(server_url, ping_interval=20, ping_timeout=10, max_size=2*1024*1024) as ws:
                # Send hello
                await ws.send(json.dumps({
                    "type": "hello",
                    "mode": "jpeg",
                    "width": actual_w,
                    "height": actual_h,
                    "fps": TARGET_FPS,
                }))
                logger.info(f"Connected! Streaming at {TARGET_FPS}fps, JPEG quality={JPEG_QUALITY}")
                retry_count = 0

                while True:
                    t_start = time.time()

                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Failed to read frame, retrying...")
                        await asyncio.sleep(0.1)
                        continue

                    # Encode as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')

                    # Send frame
                    await ws.send(json.dumps({
                        "type": "frame",
                        "frame": frame_b64,
                        "camera_id": 1,
                        "timestamp": str(time.time()),
                        "width": actual_w,
                        "height": actual_h,
                    }))

                    frame_count += 1
                    if frame_count == 1:
                        logger.info(f"First frame sent! Size: {len(buffer)} bytes")
                    if frame_count % 100 == 0:
                        logger.info(f"Sent {frame_count} frames")

                    # Throttle to target FPS
                    elapsed = time.time() - t_start
                    sleep_time = max(0, frame_interval - elapsed)
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

        except websockets.exceptions.ConnectionClosed as e:
            retry_count += 1
            logger.warning(f"Connection closed: {e}. Retry {retry_count}/{max_retries}...")
            await asyncio.sleep(2)
        except Exception as e:
            retry_count += 1
            logger.error(f"Error: {e}. Retry {retry_count}/{max_retries}...")
            await asyncio.sleep(2)

    cap.release()
    logger.info(f"Stopped. Total frames sent: {frame_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SurveillX Streaming Client")
    parser.add_argument("--server", default="surveillx.servebeer.com",
                       help="Server hostname (without ws:// or port)")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--mode", choices=["jpegws", "fastrtc"], default="jpegws",
                       help="Streaming mode: jpegws (port 8443) or fastrtc (port 8080)")
    args = parser.parse_args()

    try:
        asyncio.run(stream(args.server, args.camera, args.mode))
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
