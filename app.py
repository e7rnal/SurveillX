"""
SurveillX Backend - Main Application
Smart Surveillance System with Face Recognition and Behavior Detection
"""

import os
import logging
from flask import Flask, jsonify, redirect, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from config import Config
from services.db_manager import DBManager
from services.email_service import EmailService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.url_map.strict_slashes = False  # Allow both /api/alerts and /api/alerts/

# Initialize extensions
CORS(app, resources={r"/*": {"origins": "*"}})
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
db = DBManager(Config.DATABASE_URL)

# Make db available to blueprints
app.db = db

# Initialize email service
try:
    email_service = EmailService(
        aws_access_key=os.getenv('AWS_ACCESS_KEY_ID', ''),
        aws_secret_key=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        aws_region=os.getenv('AWS_REGION', 'ap-south-1'),
        sender_email=os.getenv('SES_SENDER_EMAIL', ''),
    )
    app.email_service = email_service
    ALERT_EMAIL_RECIPIENT = os.getenv('ALERT_EMAIL_RECIPIENT', os.getenv('SES_SENDER_EMAIL', ''))
except Exception as e:
    logger.warning(f"Email service not available: {e}")
    email_service = None
    app.email_service = None
    ALERT_EMAIL_RECIPIENT = ''

# Register blueprints
from api.auth import auth_bp
from api.students import students_bp
from api.attendance import attendance_bp
from api.alerts import alerts_bp
from api.cameras import cameras_bp
from api.stats import stats_bp
from api.enrollment import enrollment_bp
from api.clips import clips_bp
from api.detection import detection_bp
from api.system_health import system_health_bp


app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(students_bp, url_prefix='/api/students')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
app.register_blueprint(cameras_bp, url_prefix='/api/cameras')
app.register_blueprint(stats_bp, url_prefix='/api/stats')
app.register_blueprint(enrollment_bp, url_prefix='/api/enrollment')
app.register_blueprint(clips_bp, url_prefix='/api/clips')
app.register_blueprint(detection_bp, url_prefix='/api/detection')
app.register_blueprint(system_health_bp, url_prefix='/api/system')


# Frontend routes
@app.route('/')
def root():
    return redirect('/templates/login.html')

@app.route('/templates/login.html')
def login_page():
    return send_from_directory('templates', 'login.html')

@app.route('/templates/index.html')
def index_page():
    return send_from_directory('templates', 'index.html')

@app.route('/templates/register.html')
def register_page():
    return send_from_directory('templates', 'register.html')

@app.route('/templates/enroll.html')
@app.route('/enroll')
def enroll_page():
    return send_from_directory('templates', 'enroll.html')

# API endpoint to serve partial HTML templates
@app.route('/api/partials/<page>')
def serve_partial(page):
    """Serve partial HTML templates for SPA pages"""
    allowed_partials = ['dashboard', 'live', 'alerts', 'attendance', 'students', 'settings', 'detection-test']
    if page in allowed_partials:
        try:
            return send_from_directory('templates/partials', f'{page}.html')
        except Exception as e:
            logger.error(f"Failed to load partial {page}: {e}")
            return jsonify({"error": "Partial not found"}), 404
    return jsonify({"error": "Invalid partial"}), 400


# Serve uploaded files (face photos, snapshots)
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded files — face photos, alert snapshots."""
    return send_from_directory('uploads', filename)


# API root
@app.route('/api')
def api_info():
    return jsonify({
        "message": "SurveillX Backend API",
        "version": "1.0.0",
        "status": "online"
    })

# Health check
@app.route('/health')
def health():
    try:
        # Test database connection
        stats = db.get_dashboard_stats()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# Internal endpoint: receive frames from streaming server and broadcast to browser
@app.route('/api/stream/frame', methods=['POST'])
def receive_frame():
    """Receive a frame from the streaming server and broadcast to browser clients."""
    try:
        data = request.get_json(silent=True)
        if not data or 'frame' not in data:
            return jsonify({"error": "No frame data"}), 400

        # Broadcast to all /stream Socket.IO clients (the browser)
        import time as _time
        socketio.emit('frame', {
            'frame': data['frame'],
            'camera_id': data.get('camera_id', 1),
            'timestamp': data.get('timestamp', ''),
            'server_time': _time.time() * 1000,
        }, namespace='/stream')

        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"Frame receive error: {e}")
        return jsonify({"error": str(e)}), 500


# ---------- Attendance & Alert Auto-processing ----------
import time as _time

# In-memory dedup caches
_attendance_cache = {}   # student_id → last_marked_timestamp
_alert_cooldown = {}     # event_type → last_created_timestamp
ATTENDANCE_DEDUP_SEC = 30 * 60   # 30 minutes
ALERT_COOLDOWN_SEC = 60          # 60 seconds

# Store latest detection for REST polling fallback
_latest_detection = {}


def _auto_mark_attendance(faces):
    """Auto-mark attendance for recognized faces (with 30-min dedup)."""
    now = _time.time()
    logger.info(f"🔍 _auto_mark_attendance called with {len(faces)} faces")
    for face in faces:
        student_id = face.get('student_id')
        name = face.get('student_name', f'ID:{student_id}')
        if not student_id:
            logger.debug(f"  Skipping face without student_id: {face.get('student_name', 'unknown')}")
            continue
        logger.info(f"  Processing: {name} (id={student_id})")
        # Check in-memory cache first (fast)
        last = _attendance_cache.get(student_id, 0)
        if now - last < ATTENDANCE_DEDUP_SEC:
            logger.info(f"  ⏭️ Skipped {name}: in-memory cache dedup ({int(now - last)}s ago)")
            continue
        # Double-check in DB
        try:
            recent = db.check_recent_attendance(student_id, minutes=30)
            if recent:
                _attendance_cache[student_id] = now
                logger.info(f"  ⏭️ Skipped {name}: DB dedup (recent record found)")
                continue
            db.mark_attendance(student_id)
            _attendance_cache[student_id] = now
            logger.info(f"📝 Auto-marked attendance for {name} (id={student_id})")
        except Exception as e:
            logger.error(f"❌ Attendance error for student {student_id}: {e}", exc_info=True)


def _auto_create_alert(activity, snapshot_path=None):
    """Auto-create alert for abnormal activity (with 60-sec cooldown)."""
    if not activity.get('is_abnormal'):
        return
    now = _time.time()
    event_type = activity.get('type', 'unknown')
    last = _alert_cooldown.get(event_type, 0)
    if now - last < ALERT_COOLDOWN_SEC:
        return
    try:
        alert_id = db.create_alert_with_snapshot(
            event_type=event_type,
            camera_id=1,
            clip_path=None,
            severity=activity.get('severity', 'medium'),
            metadata={
                'description': activity.get('description', ''),
                'confidence': activity.get('confidence', 0),
            },
            snapshot_path=snapshot_path,
        )
        _alert_cooldown[event_type] = now
        logger.info(f"🚨 Auto-created alert #{alert_id}: {event_type} ({activity.get('severity')}) snapshot={'yes' if snapshot_path else 'no'}")

        # Broadcast alert event to frontend
        socketio.emit('new_alert', {
            'id': alert_id,
            'event_type': event_type,
            'severity': activity.get('severity', 'medium'),
            'description': activity.get('description', ''),
            'snapshot_path': snapshot_path,
        }, namespace='/stream')

        # Send email notification for high-severity alerts
        if email_service and ALERT_EMAIL_RECIPIENT and activity.get('severity') in ('high', 'medium'):
            try:
                from datetime import datetime
                email_service.send_alert_email(
                    recipient_email=ALERT_EMAIL_RECIPIENT,
                    alert_data={
                        'event_type': event_type,
                        'severity': activity.get('severity', 'medium'),
                        'camera_id': 1,
                        'description': activity.get('description', ''),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    },
                    base_url=os.getenv('BASE_URL', 'http://localhost:5000'),
                )
            except Exception as email_err:
                logger.error(f"Alert email failed: {email_err}")
    except Exception as e:
        logger.error(f"Alert creation error: {e}")


# Internal endpoint: receive ML detections and broadcast to browser
@app.route('/api/stream/detections', methods=['POST'])
def receive_detections():
    """Receive detection results from ML worker and broadcast to dashboard."""
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.warning("⚠️ Received empty detection data")
            return jsonify({"error": "No data"}), 400

        # Serialize face data (remove numpy arrays)
        faces = data.get('faces', [])
        for face in faces:
            face.pop('embedding', None)  # Don't broadcast raw embeddings

        activity = data.get('activity', {})

        # --- Auto-mark attendance for recognized faces ---
        _auto_mark_attendance(faces)

        # --- Auto-create alerts for abnormal activity ---
        _auto_create_alert(activity, snapshot_path=data.get('snapshot_path'))

        # Broadcast to dashboard
        detection_data = {
            'faces': faces,
            'activity': {
                'type': activity.get('type', 'normal'),
                'is_abnormal': activity.get('is_abnormal', False),
                'severity': activity.get('severity', 'low'),
                'confidence': activity.get('confidence', 0),
                'description': activity.get('description', ''),
            },
            'persons': activity.get('persons', []),
            'timestamp': data.get('timestamp', ''),
        }
        
        socketio.emit('detection', detection_data, namespace='/stream')
        
        # Store for REST polling fallback
        global _latest_detection
        _latest_detection = detection_data

        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"❌ Detection broadcast error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/detections/latest')
def get_latest_detection():
    """REST fallback: returns the latest detection data for polling."""
    return jsonify(_latest_detection or {
        'faces': [],
        'activity': {'type': 'normal', 'is_abnormal': False, 'severity': 'low', 'confidence': 0, 'description': ''},
        'persons': [],
        'timestamp': ''
    })


# ML worker status
@app.route('/api/ml/status')
def ml_status():
    """Return ML service availability."""
    return jsonify({
        "face_service": "available",
        "activity_detector": "available",
        "note": "ML processing runs in separate ml_worker.py process",
    })


# Internal endpoint: load known faces for ML Worker (no auth required)
@app.route('/api/internal/known-faces', methods=['GET'])
def get_known_faces():
    """Return all students with face encodings for ML Worker.
    This is an internal endpoint — no JWT required.
    Only accessible from localhost (ML Worker runs on same host).
    """
    try:
        # Security: only allow from localhost
        remote = request.remote_addr
        if remote not in ('127.0.0.1', '::1', 'localhost'):
            return jsonify({"error": "Forbidden"}), 403

        students = db.get_all_students()
        faces = []
        for s in students:
            if s.get('face_encoding'):
                faces.append({
                    'id': s['id'],
                    'name': s['name'],
                    'face_encoding': s['face_encoding'],
                })
        logger.info(f"🧠 ML Worker requested known faces: {len(faces)} found")
        return jsonify({"faces": faces})
    except Exception as e:
        logger.error(f"Error loading known faces: {e}")
        return jsonify({"error": str(e)}), 500


# ---------- Stream Mode Configuration ----------
import json as _json

STREAM_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'stream_config.json')

def _load_stream_config():
    try:
        with open(STREAM_CONFIG_FILE) as f:
            return _json.load(f)
    except Exception:
        return {"mode": "jpegws", "auto_switch": False}

def _save_stream_config(config):
    with open(STREAM_CONFIG_FILE, 'w') as f:
        _json.dump(config, f)

@app.route('/api/stream/config', methods=['GET'])
def get_stream_config():
    """Return available streaming modes and current active mode."""
    config = _load_stream_config()
    return jsonify({
        "current_mode": config.get("mode", "jpegws"),
        "auto_switch": config.get("auto_switch", False),
        "modes": {
            "jpegws": {
                "name": "JPEG WebSocket",
                "port": 8443,
                "description": "Direct JPEG frames over WebSocket",
                "ws_path": "",
            },
            "fastrtc": {
                "name": "FastRTC",
                "port": 8080,
                "description": "FastAPI/uvicorn WebSocket hub",
                "ws_path": "/ws/view",
            }
        }
    })

@app.route('/api/stream/config', methods=['POST'])
def set_stream_config():
    """Set streaming mode: jpegws, fastrtc, or auto."""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "").lower()
    auto_switch = data.get("auto_switch", None)

    config = _load_stream_config()

    if mode and mode in ("jpegws", "fastrtc"):
        config["mode"] = mode
    if auto_switch is not None:
        config["auto_switch"] = bool(auto_switch)

    _save_stream_config(config)
    logger.info(f"Stream config updated: mode={config['mode']}, auto_switch={config['auto_switch']}")
    return jsonify({"ok": True, **config})


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Cleanup on shutdown
@app.teardown_appcontext
def shutdown_session(exception=None):
    pass

if __name__ == '__main__':
    logger.info("Starting SurveillX Backend...")
    logger.info(f"Server running on {Config.HOST}:{Config.PORT}")
    
    # Register stream handler namespace
    try:
        from services.stream_handler import stream_handler
        socketio.on_namespace(stream_handler)
        logger.info("Stream handler registered")
    except Exception as e:
        logger.warning(f"Stream handler not loaded: {e}")

    # Initialize face recognition service (attach to app for enrollment API)
    try:
        from services.face_service import FaceService
        face_svc = FaceService(db_manager=app.db, threshold=0.4, gpu_id=0)
        app.face_service = face_svc
        logger.info(f"Face service initialized: {face_svc.get_stats()}")
    except Exception as e:
        app.face_service = None
        logger.warning(f"Face service not loaded: {e}")
    
    # Run with SocketIO
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=(Config.FLASK_ENV == 'development'),
        allow_unsafe_werkzeug=True
    )

