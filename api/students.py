"""Students API — CRUD + face enrollment"""
import os
import json
import uuid
import base64
import logging
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)
students_bp = Blueprint('students', __name__)

FACE_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'faces')
os.makedirs(FACE_UPLOAD_DIR, exist_ok=True)


@students_bp.route('/', methods=['GET'])
@jwt_required()
def get_students():
    try:
        db = current_app.db
        search = request.args.get('search', '').strip()
        students = db.get_all_students()

        # Add face count to each student
        for s in students:
            s['face_count'] = db.get_student_face_count(s['id'])

        # Client-side search
        if search:
            sl = search.lower()
            students = [s for s in students if
                        sl in (s.get('name') or '').lower() or
                        sl in str(s.get('roll_no', ''))]

        return jsonify({"students": students})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@students_bp.route('/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    try:
        db = current_app.db
        student = db.get_student_by_id(student_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404
        student['face_count'] = db.get_student_face_count(student_id)
        student['faces'] = db.get_student_faces(student_id)
        return jsonify({"student": student})
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

        # Validate input data
        from api.enrollment import validate_enrollment_data
        validation_errors = validate_enrollment_data(name, roll_no, contact_no)
        if validation_errors:
            return jsonify({
                "error": "Validation failed",
                "details": validation_errors
            }), 400

        face_encoding = None

        # Process photos if provided (same flow as enrollment)
        if photos and len(photos) >= 5:
            from api.enrollment import _decode_photo
            face_service = getattr(current_app, 'face_service', None)

            frames = []
            for i, photo in enumerate(photos):
                frame = _decode_photo(photo)
                if frame is None:
                    return jsonify({"error": f"Photo {i+1} could not be decoded"}), 400
                frames.append(frame)

            if face_service and face_service.app is not None:
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

                encode_result = face_service.encode_multiple(frames)
                if encode_result['embedding']:
                    face_encoding = encode_result['embedding']
                    logger.info(f"Computed face embedding from {encode_result['valid_count']}/5 photos for {name}")

        student_id = db.add_student(
            name=name,
            roll_no=roll_no,
            contact_no=contact_no,
            class_name=class_name,
            face_encoding=face_encoding
        )

        # Add to in-memory face cache
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
    try:
        db = current_app.db
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
    try:
        data = request.get_json()
        db = current_app.db
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


# ==================== FACE ENROLLMENT ====================

@students_bp.route('/<int:student_id>/face', methods=['POST'])
@jwt_required()
def upload_face(student_id):
    """Upload a face photo for a student (base64 JPEG)."""
    try:
        db = current_app.db
        student = db.get_student_by_id(student_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404

        data = request.get_json()
        photo_b64 = data.get('photo')
        if not photo_b64:
            return jsonify({"error": "No photo provided"}), 400

        # Decode base64 → save to disk
        if ',' in photo_b64:
            photo_b64 = photo_b64.split(',', 1)[1]

        photo_bytes = base64.b64decode(photo_b64)
        filename = f"student_{student_id}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(FACE_UPLOAD_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(photo_bytes)

        # Validate face is present in the photo
        import cv2
        import numpy as np
        nparr = np.frombuffer(photo_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        face_service = getattr(current_app, 'face_service', None)
        if face_service and frame is not None:
            validation = face_service.validate_face(frame)
            if not validation.get('valid'):
                os.remove(filepath)
                return jsonify({
                    "error": f"No valid face detected: {validation.get('error', 'unknown')}"
                }), 400

        # Save to DB
        face_id = db.add_student_face(student_id, f"/uploads/faces/{filename}")
        face_count = db.get_student_face_count(student_id)

        # Recompute face encoding from all photos if >= 3
        encoding_updated = False
        if face_count >= 3 and face_service:
            encoding_updated = _recompute_encoding(db, student_id, face_service)

        return jsonify({
            "face_id": face_id,
            "face_count": face_count,
            "encoding_updated": encoding_updated,
            "message": f"Face photo uploaded ({face_count} total)"
        })
    except Exception as e:
        logger.error(f"Face upload error: {e}")
        return jsonify({"error": str(e)}), 500


@students_bp.route('/<int:student_id>/faces', methods=['GET'])
@jwt_required()
def get_faces(student_id):
    """Get all enrolled face photos for a student."""
    try:
        db = current_app.db
        faces = db.get_student_faces(student_id)
        return jsonify({"faces": faces, "count": len(faces)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@students_bp.route('/<int:student_id>/face/<int:face_id>', methods=['DELETE'])
@jwt_required()
def delete_face(student_id, face_id):
    """Delete a face photo and recompute encoding."""
    try:
        db = current_app.db
        photo_path = db.delete_student_face(face_id)

        # Delete file from disk
        if photo_path:
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), photo_path.lstrip('/'))
            if os.path.exists(full_path):
                os.remove(full_path)

        # Recompute encoding
        face_count = db.get_student_face_count(student_id)
        face_service = getattr(current_app, 'face_service', None)
        if face_count >= 3 and face_service:
            _recompute_encoding(db, student_id, face_service)
        elif face_count < 3:
            # Clear face encoding if below minimum
            db.update_student(student_id, face_encoding=None)

        return jsonify({
            "message": "Face deleted",
            "face_count": face_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@students_bp.route('/<int:student_id>/attendance', methods=['GET'])
@jwt_required()
def get_student_attendance(student_id):
    """Get attendance history for a specific student."""
    try:
        db = current_app.db
        limit = int(request.args.get('limit', 30))
        records = db.get_student_attendance_history(student_id, limit=limit)
        return jsonify({"records": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@students_bp.route('/import-csv', methods=['POST'])
@jwt_required()
def import_csv():
    """Bulk import students from CSV (name, roll_no, class)."""
    try:
        import csv
        import io

        data = request.get_json()
        csv_text = data.get('csv', '')
        if not csv_text:
            return jsonify({"error": "No CSV data"}), 400

        db = current_app.db
        reader = csv.DictReader(io.StringIO(csv_text))
        added = 0
        errors = []

        for i, row in enumerate(reader, 1):
            name = row.get('Name', row.get('name', '')).strip()
            roll_no = row.get('Roll No', row.get('roll_no', '')).strip()
            class_name = row.get('Class', row.get('class', '')).strip()

            if not name or not roll_no:
                errors.append(f"Row {i}: missing name or roll_no")
                continue

            # Check for duplicate
            existing = db.get_student_by_roll_no(roll_no)
            if existing:
                errors.append(f"Row {i}: roll_no {roll_no} already exists")
                continue

            db.add_student(name=name, roll_no=roll_no, contact_no='', class_name=class_name, face_encoding=None)
            added += 1

        return jsonify({
            "added": added,
            "errors": errors,
            "message": f"{added} students imported"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== SERVE FACE PHOTOS ====================

@students_bp.route('/face-photo/<path:filename>', methods=['GET'])
def serve_face_photo(filename):
    """Serve face photos from uploads directory."""
    return send_from_directory(FACE_UPLOAD_DIR, filename)


# ==================== HELPERS ====================

def _recompute_encoding(db, student_id, face_service):
    """Recompute face encoding from all face photos."""
    try:
        import cv2
        import numpy as np

        faces = db.get_student_faces(student_id)
        frames = []

        base_dir = os.path.dirname(os.path.dirname(__file__))
        for face in faces:
            path = os.path.join(base_dir, face['photo_path'].lstrip('/'))
            if os.path.exists(path):
                frame = cv2.imread(path)
                if frame is not None:
                    frames.append(frame)

        if len(frames) < 3:
            return False

        encode_result = face_service.encode_multiple(frames)
        if encode_result.get('embedding'):
            db.update_student(student_id, face_encoding=encode_result['embedding'])

            # Update in-memory cache for ML worker
            student = db.get_student_by_id(student_id)
            if student:
                face_service.add_known_face(student_id, student['name'], encode_result['embedding'])

            logger.info(f"Recomputed encoding for student {student_id} from {len(frames)} photos")
            return True
    except Exception as e:
        logger.error(f"Encoding recompute error: {e}")
    return False
