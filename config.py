"""
Configuration Management for SurveillX Backend
Loads environment variables and provides configuration settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://surveillx_user:surveillx_secure_2024@localhost:5432/surveillx')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # AWS SES (Email Service)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    SES_SENDER_EMAIL = os.getenv('SES_SENDER_EMAIL', 'noreply@example.com')
    
    # Enrollment
    ENROLLMENT_LINK_EXPIRY_HOURS = int(os.getenv('ENROLLMENT_LINK_EXPIRY_HOURS', 24))
    REQUIRED_ENROLLMENT_PHOTOS = int(os.getenv('REQUIRED_ENROLLMENT_PHOTOS', 5))
    
    # Video Clips
    CLIPS_DIR = os.getenv('CLIPS_DIR', 'clips')
    MAX_CLIP_DURATION = int(os.getenv('MAX_CLIP_DURATION', 30))
    CLIP_FPS = int(os.getenv('CLIP_FPS', 30))
    CLIP_RESOLUTION = os.getenv('CLIP_RESOLUTION', '1920x1080')
    CLIP_RETENTION_DAYS = int(os.getenv('CLIP_RETENTION_DAYS', 30))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # Face Recognition
    FACE_RECOGNITION_THRESHOLD = float(os.getenv('FACE_RECOGNITION_THRESHOLD', 0.6))
    FACE_DETECTION_MODEL = os.getenv('FACE_DETECTION_MODEL', 'hog')
    
    # ML Detection Thresholds
    RUNNING_VELOCITY_THRESHOLD = float(os.getenv('RUNNING_VELOCITY_THRESHOLD', 2.5))
    FIGHT_DETECTION_THRESHOLD = float(os.getenv('FIGHT_DETECTION_THRESHOLD', 0.7))
    LOITERING_TIME_THRESHOLD = int(os.getenv('LOITERING_TIME_THRESHOLD', 300))
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        pass
