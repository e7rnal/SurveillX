"""
SurveillX Windows Client — Direct JPEG over WebSocket
Sends webcam frames as JPEG over WebSocket to the server.
Simple, reliable, full quality control — no WebRTC codec issues.

Usage:
    python client.py --server ws://surveillx.duckdns.org:8443 --camera 0

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
JPEG_QUALITY = 85       # 1-100, higher = better quality, larger frames
TARGET_FPS = 15         # Target frames per second
FRAME_WIDTH = 1280      # Capture width
FRAME_HEIGHT = 720      # Capture height


async def stream(server_url: str, camera_index: int):
    """Capture webcam frames and send as JPEG over WebSocket."""

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

    frame_interval = 1.0 / TARGET_FPS
    frame_count = 0
    retry_count = 0
    max_retries = 10

    while retry_count < max_retries:
        try:
            logger.info(f"Connecting to {server_url}...")
            async with websockets.connect(server_url, ping_interval=20, ping_timeout=10) as ws:
                # Send hello message to identify as JPEG client
                await ws.send(json.dumps({
                    "type": "hello",
                    "mode": "jpeg",
                    "width": actual_w,
                    "height": actual_h,
                    "fps": TARGET_FPS,
                }))
                logger.info(f"Connected! Streaming at {TARGET_FPS}fps, JPEG quality={JPEG_QUALITY}")
                retry_count = 0  # Reset on successful connection

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
    parser = argparse.ArgumentParser(description="SurveillX WebSocket Streaming Client")
    parser.add_argument("--server", default="ws://surveillx.duckdns.org:8443")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    try:
        asyncio.run(stream(args.server, args.camera))
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
