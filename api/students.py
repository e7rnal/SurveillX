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
    try:
        data = request.get_json()
        db = current_app.db
        student_id = db.add_student(
            name=data['name'],
            roll_no=data['roll_no'],
            contact_no=data.get('contact_no'),
            class_name=data.get('class'),
            face_encoding=data.get('face_encoding')
        )
        return jsonify({"student_id": student_id, "message": "Student added successfully"})
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
