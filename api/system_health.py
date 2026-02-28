"""
System Health API — real-time server & GPU telemetry for the dashboard.
"""
import os
import time
import platform
import subprocess
import logging

import psutil
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

system_health_bp = Blueprint('system_health', __name__)
logger = logging.getLogger(__name__)

_SERVER_START = time.time()


def _format_uptime(seconds: float) -> dict:
    """Convert seconds into a human-readable uptime dict."""
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    minutes, s = divmod(s, 60)
    return {"days": days, "hours": hours, "minutes": minutes, "seconds": s,
            "text": f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m {s}s"}


def _gpu_info() -> dict:
    """Query nvidia-smi for GPU metrics. Returns empty dict on failure."""
    try:
        out = subprocess.check_output([
            'nvidia-smi',
            '--query-gpu=gpu_name,memory.total,memory.used,memory.free,'
            'utilization.gpu,utilization.memory,temperature.gpu,power.draw',
            '--format=csv,noheader,nounits'
        ], timeout=5, text=True).strip()

        parts = [p.strip() for p in out.split(',')]
        if len(parts) < 8:
            return {}

        return {
            "name": parts[0],
            "vram_total_mb": int(float(parts[1])),
            "vram_used_mb": int(float(parts[2])),
            "vram_free_mb": int(float(parts[3])),
            "vram_percent": round(float(parts[2]) / float(parts[1]) * 100, 1) if float(parts[1]) > 0 else 0,
            "utilization_percent": int(float(parts[4])),
            "memory_utilization_percent": int(float(parts[5])),
            "temperature_c": int(float(parts[6])),
            "power_draw_w": round(float(parts[7]), 1),
            "available": True,
        }
    except Exception as e:
        logger.debug(f"nvidia-smi query failed: {e}")
        return {"available": False}


def _ai_engine_status() -> list:
    """Check the status of AI engines. Uses lightweight checks."""
    engines = []

    # Face Detection (InsightFace buffalo_l)
    try:
        from services.face_service import face_service
        face_ok = face_service and face_service.detector and face_service.detector.available
        engines.append({
            "name": "Face Detection",
            "model": "InsightFace buffalo_l",
            "status": "active" if face_ok else "offline",
            "icon": "fa-face-smile",
        })
    except Exception:
        engines.append({"name": "Face Detection", "model": "buffalo_l", "status": "offline", "icon": "fa-face-smile"})

    # Activity Detection (YOLOv8-pose)
    try:
        yolo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '..', 'engines', 'activity_detection')
        yolo_exists = os.path.exists(os.path.join(yolo_path, 'detector.py'))
        engines.append({
            "name": "Pose Estimation",
            "model": "YOLOv8s-pose",
            "status": "active" if yolo_exists else "offline",
            "icon": "fa-person-running",
        })
    except Exception:
        engines.append({"name": "Pose Estimation", "model": "YOLOv8s-pose", "status": "offline", "icon": "fa-person-running"})

    # LSTM Activity Classifier
    try:
        lstm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '..', 'engines', 'activity_detection', 'activity_lstm.pt')
        engines.append({
            "name": "Activity Classifier",
            "model": "Pose-LSTM",
            "status": "active" if os.path.exists(lstm_path) else "offline",
            "icon": "fa-brain",
        })
    except Exception:
        engines.append({"name": "Activity Classifier", "model": "Pose-LSTM", "status": "offline", "icon": "fa-brain"})

    # Stream Pipeline
    try:
        stream_procs = [p for p in psutil.process_iter(['name', 'cmdline'])
                        if 'ffmpeg' in (p.info.get('name') or '').lower()
                        or any('stream' in (c or '').lower() for c in (p.info.get('cmdline') or []))]
        engines.append({
            "name": "Stream Pipeline",
            "model": "FFmpeg + WebSocket",
            "status": "active" if len(stream_procs) > 0 else "standby",
            "icon": "fa-video",
        })
    except Exception:
        engines.append({"name": "Stream Pipeline", "model": "FFmpeg", "status": "standby", "icon": "fa-video"})

    return engines


@system_health_bp.route('/health', methods=['GET'])
@jwt_required()
def get_system_health():
    """Return comprehensive system health metrics."""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.3)
        load1, load5, load15 = psutil.getloadavg()
        cpu_count = psutil.cpu_count()

        # Memory
        mem = psutil.virtual_memory()

        # Disks — monitor all relevant mount points
        _disk_mounts = [
            ('/', 'Root'),
            ('/opt/dlami/nvme', 'Storage'),
        ]
        disks = []
        for mnt, label in _disk_mounts:
            try:
                d = psutil.disk_usage(mnt)
                disks.append({
                    "mount": mnt,
                    "label": label,
                    "total_gb": round(d.total / (1024 ** 3), 1),
                    "used_gb": round(d.used / (1024 ** 3), 1),
                    "free_gb": round(d.free / (1024 ** 3), 1),
                    "percent": d.percent,
                })
            except Exception:
                pass

        # Network
        net = psutil.net_io_counters()

        # Uptime
        uptime_secs = time.time() - _SERVER_START

        # GPU
        gpu = _gpu_info()

        # AI Engines
        ai_engines = _ai_engine_status()

        return jsonify({
            "server": {
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "python": platform.python_version(),
                "uptime": _format_uptime(uptime_secs),
                "uptime_seconds": int(uptime_secs),
            },
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count,
                "load_avg": [round(load1, 2), round(load5, 2), round(load15, 2)],
            },
            "memory": {
                "total_gb": round(mem.total / (1024 ** 3), 1),
                "used_gb": round(mem.used / (1024 ** 3), 1),
                "available_gb": round(mem.available / (1024 ** 3), 1),
                "percent": mem.percent,
            },
            "disks": disks,
            "disk": disks[0] if disks else {},
            "gpu": gpu,
            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 1),
                "bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 1),
            },
            "ai_engines": ai_engines,
        })
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return jsonify({"error": str(e)}), 500
