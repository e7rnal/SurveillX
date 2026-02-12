"""Students API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

students_bp = Blueprint('students', __name__)

@students_bp.route('/', methods=['GET'])
@jwt_required()
def get_students():
    try:
        db = current_app.db
        students = db.get_all_students()
        return jsonify({"students": students})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    try:
        db = current_app.db
        student = db.get_student_by_id(student_id)
        if student:
            return jsonify({"student": student})
        return jsonify({"error": "Student not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@students_bp.route('/', methods=['POST'])
@jwt_required()
def add_student():
    """Add a student with optional face photos (5 photos for face encoding)."""
    try:
        data = request.get_json()
        db = current_app.db

        name = data.get('name')
        roll_no = data.get('roll_no')
        contact_no = data.get('contact_no')
        class_name = data.get('class')
        photos = data.get('photos', [])

        if not name or not roll_no:
            return jsonify({"error": "Name and roll number are required"}), 400

        face_encoding = None

        # Process photos if provided (same flow as enrollment)
        if photos and len(photos) >= 5:
            from api.enrollment import _decode_photo
            import json
            import logging
            logger = logging.getLogger(__name__)

            face_service = getattr(current_app, 'face_service', None)

            # Decode all photos
            frames = []
            for i, photo in enumerate(photos):
                frame = _decode_photo(photo)
                if frame is None:
                    return jsonify({"error": f"Photo {i+1} could not be decoded"}), 400
                frames.append(frame)

            if face_service and face_service.app is not None:
                # Validate each photo has a face
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

                # Compute averaged embedding from all photos
                encode_result = face_service.encode_multiple(frames)
                if encode_result['embedding']:
                    face_encoding = encode_result['embedding']
                    logger.info(f"Computed face embedding from {encode_result['valid_count']}/5 photos for {name}")
                else:
                    logger.warning(f"Could not compute embedding: {encode_result['errors']}")

        student_id = db.add_student(
            name=name,
            roll_no=roll_no,
            contact_no=contact_no,
            class_name=class_name,
            face_encoding=face_encoding
        )

        # Add to in-memory face cache for immediate recognition
        if face_encoding:
            face_service = getattr(current_app, 'face_service', None)
            if face_service:
                face_service.add_known_face(student_id, name, face_encoding)

        return jsonify({
            "student_id": student_id,
            "message": "Student added successfully",
            "face_encoded": face_encoding is not None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['DELETE'])
@jwt_required()
def delete_student(student_id):
    """Delete a student by ID"""
    try:
        db = current_app.db
        # Check if student exists first
        student = db.get_student_by_id(student_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        
        db.delete_student(student_id)
        return jsonify({"message": "Student deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['PUT'])
@jwt_required()
def update_student(student_id):
    """Update a student's information"""
    try:
        data = request.get_json()
        db = current_app.db
        
        # Check if student exists
        student = db.get_student_by_id(student_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        
        db.update_student(
            student_id,
            name=data.get('name'),
            roll_no=data.get('roll_no'),
            contact_no=data.get('contact_no'),
            class_name=data.get('class')
        )
        return jsonify({"message": "Student updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
