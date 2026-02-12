"""
SurveillX Windows Client — WebRTC Streamer (for FastRTC server)
Sends webcam video via WebRTC to the FastRTC server on port 8080.

Usage:
    python client.py --server http://surveillx.duckdns.org:8080 --camera 0

Requires:
    pip install aiortc opencv-python requests av
"""
import argparse
import asyncio
import logging
import requests
import cv2
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
    VideoStreamTrack,
)
from av import VideoFrame

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("surveillx-client")


class CameraTrack(VideoStreamTrack):
    """Read frames from webcam and send via WebRTC."""

    def __init__(self, camera_index=0, width=640, height=480):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        logger.info(f"Camera {camera_index} opened: {width}x{height}")

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            # Return black frame on failure
            return VideoFrame(width=640, height=480)
        vf = VideoFrame.from_ndarray(frame, format="bgr24")
        vf.pts = pts
        vf.time_base = time_base
        return vf

    def stop(self):
        if self.cap.isOpened():
            self.cap.release()


async def run(server_url: str, camera_index: int):
    # 1. Fetch ICE config from server
    logger.info(f"Fetching ICE config from {server_url}...")
    resp = requests.get(f"{server_url}/webrtc/ice-config")
    resp.raise_for_status()
    ice_data = resp.json()

    # 2. Build ICE configuration
    ice_servers = []
    for srv in ice_data.get("iceServers", []):
        urls = srv["urls"] if isinstance(srv["urls"], list) else [srv["urls"]]
        if "username" in srv:
            ice_servers.append(RTCIceServer(urls=urls, username=srv["username"], credential=srv["credential"]))
        else:
            ice_servers.append(RTCIceServer(urls=urls))

    config = RTCConfiguration(iceServers=ice_servers)
    pc = RTCPeerConnection(configuration=config)

    @pc.on("connectionstatechange")
    async def on_state():
        logger.info(f"Connection: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()

    # 3. Add camera track
    track = CameraTrack(camera_index)
    pc.addTrack(track)

    # 4. Create and send offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    logger.info("Sending SDP offer...")
    resp = requests.post(
        f"{server_url}/webrtc/streamer",
        json={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
    )
    resp.raise_for_status()
    answer = resp.json()

    await pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type=answer["type"]))
    logger.info("Connected! Streaming... Press Ctrl+C to stop.")

    # 5. Keep alive
    try:
        while pc.connectionState in ["connected", "connecting", "new"]:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        track.stop()
        await pc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SurveillX WebRTC Client")
    parser.add_argument("--server", default="http://surveillx.duckdns.org:8080")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()

    try:
        asyncio.run(run(args.server, args.camera))
    except KeyboardInterrupt:
        logger.info("Stopped.")
