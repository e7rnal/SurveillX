"""
SurveillX Windows Client — WebRTC via aiortc (for GStreamer server)
Sends webcam video via WebRTC to the GStreamer server.
Uses WebSocket signaling (not HTTP POST).

Usage:
    python client.py --server ws://surveillx.duckdns.org:8443 --camera 0

Requires:
    pip install aiortc opencv-python websockets av
"""
import argparse
import asyncio
import json
import logging

import cv2
import websockets
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCConfiguration,
    RTCIceServer,
    VideoStreamTrack,
)
from av import VideoFrame

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("surveillx-client")

# ICE config — includes TURN for NAT traversal
ICE_CONFIG = RTCConfiguration(
    iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(
            urls=["turn:13.205.156.238:3478", "turn:13.205.156.238:3478?transport=tcp"],
            username="surveillx",
            credential="Vishu@9637",
        ),
    ]
)


class CameraTrack(VideoStreamTrack):
    """Capture webcam frames and emit as WebRTC video."""

    def __init__(self, camera_index=0, width=640, height=480):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")
        logger.info(f"Camera {camera_index} opened: {width}x{height}")

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            return VideoFrame(width=640, height=480)
        vf = VideoFrame.from_ndarray(frame, format="bgr24")
        vf.pts = pts
        vf.time_base = time_base
        return vf

    def stop(self):
        if self.cap.isOpened():
            self.cap.release()


async def run(server_url: str, camera_index: int):
    pc = RTCPeerConnection(configuration=ICE_CONFIG)
    track = CameraTrack(camera_index)
    pc.addTrack(track)

    @pc.on("connectionstatechange")
    async def on_state():
        logger.info(f"Connection: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

    logger.info(f"Connecting to {server_url}...")
    async with websockets.connect(server_url) as ws:
        # Trickle ICE: send candidates as they're generated
        @pc.on("icecandidate")
        async def on_ice(candidate):
            if candidate:
                await ws.send(json.dumps({
                    "type": "ice",
                    "candidate": candidate.candidate,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                }))

        # Create and send offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        await ws.send(json.dumps({
            "type": "offer",
            "sdp": pc.localDescription.sdp,
        }))
        logger.info("SDP offer sent")

        # Receive messages (answer + ICE candidates)
        async for msg in ws:
            data = json.loads(msg)

            if data["type"] == "answer":
                logger.info("Received SDP answer")
                answer = RTCSessionDescription(sdp=data["sdp"], type="answer")
                await pc.setRemoteDescription(answer)
                logger.info("Connected! Streaming... Press Ctrl+C to stop.")

            elif data["type"] == "ice":
                # Add remote ICE candidate from server
                candidate = RTCIceCandidate(
                    sdpMLineIndex=data["sdpMLineIndex"],
                    candidate=data["candidate"],
                )
                await pc.addIceCandidate(candidate)

    track.stop()
    await pc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SurveillX WebRTC Client (GStreamer server)")
    parser.add_argument("--server", default="ws://surveillx.duckdns.org:8443")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    try:
        asyncio.run(run(args.server, args.camera))
    except KeyboardInterrupt:
        logger.info("Stopped.")
