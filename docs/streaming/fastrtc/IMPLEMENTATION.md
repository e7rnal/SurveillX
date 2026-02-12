# FastRTC — Implementation Guide

## Step 1: Create the Streaming Server

Create `streaming_server.py` in the project root (see [server.py](./server.py) for full reference):

```python
# streaming_server.py — FastRTC WebRTC + FastAPI server
# Runs on port 8080, separate from Flask on port 5000
```

### Key components:

1. **FastAPI app** — handles WebRTC signaling at `/webrtc/streamer`
2. **aiortc PeerConnection** — receives video track from Windows client
3. **Frame consumer** — calls `track.recv()` in a proper async loop
4. **Socket.IO client** — forwards frames to Flask for browser display
5. **Face recognition** — hooks into the existing `services/` modules

## Step 2: Signaling Endpoint

```python
@app.post("/webrtc/streamer")
async def handle_streamer(request: Request):
    params = await request.json()
    
    pc = RTCPeerConnection(configuration=ICE_CONFIG)
    
    @pc.on("track")
    async def on_track(track):
        if track.kind == "video":
            asyncio.ensure_future(consume_frames(track))
    
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
```

**Why this works (and Flask didn't):** FastAPI runs on uvicorn which has a native asyncio event loop. `track.recv()` is awaited on the **same loop** that owns the PeerConnection.

## Step 3: Frame Consumer

```python
async def consume_frames(track):
    """This is the function that FAILED in Flask but works in FastAPI."""
    frame_count = 0
    while True:
        frame = await track.recv()  # ← This actually works now!
        frame_count += 1
        
        img = frame.to_ndarray(format="bgr24")
        
        # Run face recognition every 5th frame
        if frame_count % 5 == 0:
            process_for_attendance(img)
        
        # Forward to browser every 2nd frame
        if frame_count % 2 == 0:
            forward_to_browser(img)
```

## Step 4: Forward Frames to Flask (for browser)

```python
import socketio

sio = socketio.Client()
sio.connect('http://localhost:5000', namespaces=['/stream'])

def forward_to_browser(img):
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    frame_b64 = base64.b64encode(buffer).decode('utf-8')
    sio.emit('frame', {
        'frame': frame_b64,
        'camera_id': 1,
        'timestamp': str(time.time())
    }, namespace='/stream')
```

## Step 5: Run the Server

```bash
# Terminal 1: Flask (existing)
cd /home/ubuntu/surveillx-backend
source venv/bin/activate
python app.py  # port 5000

# Terminal 2: FastRTC streaming server (NEW)
uvicorn streaming_server:app --host 0.0.0.0 --port 8080
```

## Step 6: Windows Client

The Windows client code is almost identical to before. See [client.py](./client.py).

Key difference: it connects to `:8080/webrtc/streamer` instead of `:5000/webrtc/streamer`.

```python
SERVER_URL = "http://surveillx.duckdns.org:8080"
resp = requests.post(f"{SERVER_URL}/webrtc/streamer", json=payload)
```

## Step 7: Browser (No Changes Needed!)

The browser already listens for `frame` events on the `/stream` Socket.IO namespace. **No browser code changes needed** — the FastRTC server emits frames to Flask, which forwards to the browser via the existing Socket.IO connection.

## Step 8: Process Manager (Production)

Use `supervisord` to manage both servers:

```ini
[program:flask]
command=/home/ubuntu/surveillx-backend/venv/bin/python app.py
directory=/home/ubuntu/surveillx-backend

[program:streaming]
command=/home/ubuntu/surveillx-backend/venv/bin/uvicorn streaming_server:app --host 0.0.0.0 --port 8080
directory=/home/ubuntu/surveillx-backend
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `track.recv()` timeout | Check coturn is running, client has TURN config |
| Socket.IO emit fails | Ensure Flask is running on :5000 before starting FastRTC |
| Codec mismatch | Both sides must support VP8 (default in aiortc) |
| Port 8080 blocked | Open in AWS Security Group |
