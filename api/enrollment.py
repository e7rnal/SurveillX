"""
Enrollment API - Student Self-Registration System
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
import secrets
import hashlib
from datetime import datetime, timedelta

enrollment_bp = Blueprint('enrollment', __name__)

@enrollment_bp.route('/generate-link', methods=['POST'])
@jwt_required()
def generate_enrollment_link():
    """Generate enrollment link and send email"""
    try:
        data = request.get_json()
        email = data.get('email')
        roll_no = data.get('roll_no')
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Generate unique token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Calculate expiry
        expiry_hours = current_app.config['ENROLLMENT_LINK_EXPIRY_HOURS']
        expires_at = datetime.now() + timedelta(hours=expiry_hours)
        
        # Save to database
        db = current_app.db
        token_id = db.create_enrollment_token(token_hash, email, roll_no, expires_at)
        
        if not token_id:
            return jsonify({"error": "Failed to create enrollment token"}), 500
        
        # Return token (email sending optional)
        return jsonify({
            "message": "Enrollment link generated",
            "token": token,
            "expires_at": expires_at.isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrollment_bp.route('/verify/<token>', methods=['GET'])
def verify_token(token):
    """Verify enrollment token"""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db = current_app.db
        token_data = db.get_enrollment_token(token_hash)
        
        if not token_data:
            return jsonify({"error": "Invalid token"}), 404
        
        # Check if expired
        if datetime.now() > token_data['expires_at']:
            return jsonify({"error": "Token expired"}), 400
        
        # Check if used
        if token_data['used']:
            return jsonify({"error": "Token already used"}), 400
        
        return jsonify({
            "valid": True,
            "email": token_data['email'],
            "roll_no": token_data['roll_no']
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrollment_bp.route('/submit', methods=['POST'])
def submit_enrollment():
    """Submit enrollment data"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({"error": "Token is required"}), 400
        
        # Verify token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db = current_app.db
        token_data = db.get_enrollment_token(token_hash)
        
        if not token_data or token_data['used']:
            return jsonify({"error": "Invalid or used token"}), 400
        
        # Create pending enrollment
        enrollment_id = db.create_pending_enrollment(
            token_id=token_data['id'],
            name=data['name'],
            roll_no=data.get('roll_no') or token_data['roll_no'],
            contact_no=data.get('contact_no'),
            class_name=data.get('class'),
            face_encoding=data.get('face_encoding'),
            sample_images=data.get('sample_images', [])
        )
        
        return jsonify({
            "message": "Enrollment submitted successfully",
            "enrollment_id": enrollment_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrollment_bp.route('/pending', methods=['GET'])
@jwt_required()
def get_pending_enrollments():
    """Get all pending enrollments"""
    try:
        db = current_app.db
        enrollments = db.get_pending_enrollments()
        return jsonify({"enrollments": enrollments})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrollment_bp.route('/<int:enrollment_id>', methods=['GET'])
@jwt_required()
def get_enrollment(enrollment_id):
    """Get enrollment details"""
    try:
        db = current_app.db
        enrollment = db.get_pending_enrollment_by_id(enrollment_id)
        if enrollment:
            return jsonify({"enrollment": enrollment})
        return jsonify({"error": "Enrollment not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrollment_bp.route('/<int:enrollment_id>/approve', methods=['PUT'])
@jwt_required()
def approve_enrollment(enrollment_id):
    """Approve enrollment"""
    try:
        db = current_app.db
        student_id = db.approve_enrollment(enrollment_id)
        if student_id:
            return jsonify({
                "message": "Enrollment approved",
                "student_id": student_id
            })
        return jsonify({"error": "Failed to approve enrollment"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrollment_bp.route('/<int:enrollment_id>/reject', methods=['PUT'])
@jwt_required()
def reject_enrollment(enrollment_id):
    """Reject enrollment"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        db = current_app.db
        db.reject_enrollment(enrollment_id, reason)
        return jsonify({"message": "Enrollment rejected"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
