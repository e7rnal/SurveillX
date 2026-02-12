# SurveillX — Service Startup Guide

## Quick Start (One Command)

```bash
cd /home/ubuntu/surveillx-backend
bash start_all.sh
```

That's it. This starts all 4 services in the background with logging.

```bash
bash start_all.sh status   # Check if all services are running
bash start_all.sh stop     # Stop everything
```

---

## What Gets Started

| # | Service | Port | File | Purpose |
|---|---------|------|------|---------|
| 1 | JPEG-WS Hub | 8443 | `gst_streaming_server.py` | Receives camera frames, broadcasts to viewers |
| 2 | FastRTC Hub | 8080 | `fastrtc_server.py` | Alternative streaming server |
| 3 | Flask Dashboard | 5000 | `app.py` | Web UI + REST API + SocketIO |
| 4 | ML Worker | — | `services/ml_worker.py` | Face recognition + activity detection |

## Startup Order Matters

```
1. WS Hub (8443)     ← camera client connects here
2. FastRTC (8080)    ← alternative mode
3. Flask (5000)      ← dashboard & API
4. ML Worker         ← connects to WS Hub as viewer (needs hub running first)
```

---

## Manual Start (if you prefer)

Open 4 terminals or use `&` for background:

```bash
cd /home/ubuntu/surveillx-backend
source venv/bin/activate

# Terminal 1 — Streaming hub
python3 gst_streaming_server.py

# Terminal 2 — FastRTC hub
python3 fastrtc_server.py

# Terminal 3 — Flask dashboard
python3 app.py

# Terminal 4 — ML worker (start AFTER servers are up)
python3 services/ml_worker.py
```

> ⚠️ **Common mistake:** Don't use `&&` between commands — that runs them sequentially (each waits for the previous to exit). Use `&` to background them, or run each in a separate terminal.

---

## Windows Client

After all servers are running, start the camera client on Windows:

```cmd
cd docs\streaming\gstreamer
python client.py --server YOUR_EC2_IP --mode jpegws
```

For dual-mode (sends to both servers):
```cmd
python client_dual.py --server YOUR_EC2_IP
```

---

## Logs

All logs go to `logs/` directory:

```bash
# Watch all logs live
tail -f logs/*.log

# Individual logs
tail -f logs/flask.log       # Dashboard & API
tail -f logs/ws_hub.log      # Streaming hub
tail -f logs/fastrtc.log     # FastRTC hub
tail -f logs/ml_worker.log   # Face recognition & activity detection
```

---

## Verify Everything Works

```bash
# Check ports are bound
ss -tlnp | grep -E ":(5000|8080|8443)"

# Check API
curl http://localhost:5000/health
curl http://localhost:5000/api/stream/config
curl http://localhost:5000/api/ml/status

# Check FastRTC
curl http://localhost:8080/health

# Check ML models loaded (in ml_worker.log)
grep -i "loaded\|ready\|available" logs/ml_worker.log
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port already in use | `bash start_all.sh stop` then restart, or `kill $(lsof -t -i:PORT)` |
| ML Worker can't connect | Make sure WS Hub (8443) is running first |
| No video on dashboard | Start the Windows client, check `logs/ws_hub.log` |
| InsightFace not loading | Check `logs/ml_worker.log`, run `pip install --force-reinstall scipy` |
| Dashboard won't load | Check `logs/flask.log`, verify port 5000 is open in security group |
