"""
Enrollment API - Student Self-Registration System
Handles enrollment link generation, face photo validation, and approval with
InsightFace embedding generation.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
import secrets
import hashlib
import base64
import numpy as np
import cv2
import json
import logging
from datetime import datetime, timedelta

enrollment_bp = Blueprint('enrollment', __name__)
logger = logging.getLogger(__name__)


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

        if datetime.now() > token_data['expires_at']:
            return jsonify({"error": "Token expired"}), 400

        if token_data['used']:
            return jsonify({"error": "Token already used"}), 400

        return jsonify({
            "valid": True,
            "email": token_data['email'],
            "roll_no": token_data['roll_no']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _decode_photo(photo_item):
    """
    Decode a photo from the enrollment submission.
    Accepts either:
      - A dict with {data: "data:image/jpeg;base64,...", pose: "Front Face"}
      - A plain base64 data URL string
    Returns: BGR numpy array (for OpenCV/InsightFace) or None
    """
    try:
        if isinstance(photo_item, dict):
            raw = photo_item.get('data', '')
        else:
            raw = photo_item

        # Strip data URI prefix if present
        if ',' in raw:
            raw = raw.split(',', 1)[1]

        img_bytes = base64.b64decode(raw)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.warning(f"Photo decode error: {e}")
        return None


@enrollment_bp.route('/submit', methods=['POST'])
def submit_enrollment():
    """
    Submit enrollment data with 5 pose photos.
    Validates that each photo contains a detectable face (using InsightFace if available).
    Stores photos and optionally pre-computes face embedding.
    """
    try:
        data = request.get_json()
        token = data.get('token')
        name = data.get('name')
        photos = data.get('photos', [])

        if not name:
            return jsonify({"error": "Name is required"}), 400

        if len(photos) < 5:
            return jsonify({"error": "At least 5 photos required"}), 400

        db = current_app.db
        token_data = None

        # Verify token if provided
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            token_data = db.get_enrollment_token(token_hash)

            if not token_data or token_data['used']:
                return jsonify({"error": "Invalid or used token"}), 400

        # ---- Validate faces in photos using InsightFace ----
        face_service = getattr(current_app, 'face_service', None)
        face_validated = False
        encoding_json = None

        frames = []
        for i, photo in enumerate(photos):
            frame = _decode_photo(photo)
            if frame is None:
                return jsonify({"error": f"Photo {i+1} could not be decoded"}), 400
            frames.append(frame)

        if face_service and face_service.app is not None:
            # Validate each photo has exactly one face
            validation_errors = []
            for i, frame in enumerate(frames):
                result = face_service.validate_face(frame)
                if not result['valid']:
                    pose_name = photos[i].get('pose', f'Photo {i+1}') if isinstance(photos[i], dict) else f'Photo {i+1}'
                    validation_errors.append(f"{pose_name}: {result['error']}")

            if validation_errors:
                return jsonify({
                    "error": "Face validation failed",
                    "details": validation_errors
                }), 400

            # Pre-compute averaged embedding from all 5 poses
            encode_result = face_service.encode_multiple(frames)
            if encode_result['embedding']:
                encoding_json = json.dumps(encode_result['embedding'])
                face_validated = True
                logger.info(f"Pre-computed enrollment embedding from {encode_result['valid_count']}/5 photos")
            else:
                logger.warning(f"Could not pre-compute embedding: {encode_result['errors']}")

        # Extract photo data URLs for storage
        photo_data = []
        for p in photos:
            if isinstance(p, dict):
                photo_data.append(p.get('data', ''))
            else:
                photo_data.append(p)

        # Create pending enrollment
        enrollment_id = db.create_pending_enrollment(
            token_id=token_data['id'] if token_data else None,
            name=name,
            roll_no=data.get('roll_no') or (token_data['roll_no'] if token_data else None),
            contact_no=data.get('contact_no'),
            class_name=data.get('class'),
            face_encoding=encoding_json,
            sample_images=photo_data
        )

        return jsonify({
            "message": "Enrollment submitted successfully",
            "enrollment_id": enrollment_id,
            "face_validated": face_validated,
        })

    except Exception as e:
        logger.error(f"Enrollment submit error: {e}")
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
    """
    Approve enrollment — creates student with face embedding.
    If embedding was pre-computed during submit, uses that.
    Otherwise, decodes stored photos and generates embedding now.
    """
    try:
        db = current_app.db
        enrollment = db.get_pending_enrollment_by_id(enrollment_id)
        if not enrollment:
            return jsonify({"error": "Enrollment not found"}), 404

        logger.info(f"Approving enrollment {enrollment_id}: {enrollment['name']}")
        logger.info(f"  Roll no: {enrollment.get('roll_no')}")
        logger.info(f"  Has sample_images: {enrollment.get('sample_images') is not None}")
        logger.info(f"  Has pre-computed face_encoding: {enrollment.get('face_encoding') is not None}")

        # Check if we have a pre-computed embedding
        face_encoding = enrollment.get('face_encoding')

        if not face_encoding:
            # Try to generate embedding from stored photos
            face_service = getattr(current_app, 'face_service', None)
            logger.info(f"  Face service available: {face_service is not None}")
            
            if face_service:
                logger.info(f"  Face service model loaded: {face_service.app is not None}")
            
            sample_images = enrollment.get('sample_images')

            if not face_service:
                logger.warning("Face service not available - cannot generate embedding!")
            elif not sample_images:
                logger.warning("No sample images in enrollment - cannot generate embedding!")
            elif face_service and sample_images:
                try:
                    if isinstance(sample_images, str):
                        sample_images = json.loads(sample_images)

                    logger.info(f"  Decoding {len(sample_images)} photos...")
                    frames = [_decode_photo(p) for p in sample_images]
                    frames = [f for f in frames if f is not None]
                    logger.info(f"  Successfully decoded {len(frames)}/{len(sample_images)} photos")

                    if frames:
                        logger.info("  Generating face embedding...")
                        result = face_service.encode_multiple(frames)
                        if result['embedding']:
                            face_encoding = json.dumps(result['embedding'])
                            logger.info(f"✅ Generated embedding from {result['valid_count']} photos (size: {len(result['embedding'])})")
                        else:
                            logger.error(f"Failed to generate embedding: {result.get('errors', 'Unknown error')}")
                    else:
                        logger.error("No valid frames decoded from photos!")
                except Exception as e:
                    logger.error(f"Error generating embedding on approval: {e}", exc_info=True)

        # Create student
        student_id = db.add_student(
            name=enrollment['name'],
            roll_no=enrollment['roll_no'],
            contact_no=enrollment.get('contact_no'),
            class_name=enrollment.get('class'),
            face_encoding=json.loads(face_encoding) if face_encoding else None
        )

        if not student_id:
            return jsonify({"error": "Failed to create student"}), 500

        # Update enrollment status
        query = "UPDATE pending_enrollments SET status = 'approved' WHERE id = %s"
        db.execute_query(query, (enrollment_id,), fetch=False, commit=True)

        # Mark token as used
        if enrollment.get('token_id'):
            db.mark_token_used(enrollment['token_id'])

        # Add to face service in-memory cache for immediate recognition
        face_service = getattr(current_app, 'face_service', None)
        if face_service and face_encoding:
            emb = json.loads(face_encoding) if isinstance(face_encoding, str) else face_encoding
            face_service.add_known_face(student_id, enrollment['name'], emb)

        return jsonify({
            "message": "Enrollment approved",
            "student_id": student_id,
            "face_encoded": face_encoding is not None
        })

    except Exception as e:
        logger.error(f"Enrollment approval error: {e}")
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
