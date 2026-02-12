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

# Register blueprints
from api.auth import auth_bp
from api.students import students_bp
from api.attendance import attendance_bp
from api.alerts import alerts_bp
from api.cameras import cameras_bp
from api.stats import stats_bp
from api.enrollment import enrollment_bp
from api.clips import clips_bp


app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(students_bp, url_prefix='/api/students')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
app.register_blueprint(cameras_bp, url_prefix='/api/cameras')
app.register_blueprint(stats_bp, url_prefix='/api/stats')
app.register_blueprint(enrollment_bp, url_prefix='/api/enrollment')
app.register_blueprint(clips_bp, url_prefix='/api/clips')


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
def enroll_page():
    return send_from_directory('templates', 'enroll.html')

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
    
    # Run with SocketIO
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=(Config.FLASK_ENV == 'development'),
        allow_unsafe_werkzeug=True
    )
