"""
SurveillX Backend - Main Application
Smart Surveillance System with Face Recognition and Behavior Detection
"""

import os
import logging
from flask import Flask, jsonify
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

# Root route
@app.route('/')
def index():
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
    
    # Run with SocketIO
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=(Config.FLASK_ENV == 'development'),
        allow_unsafe_werkzeug=True
    )
