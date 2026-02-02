"""Cameras API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

cameras_bp = Blueprint('cameras', __name__)

@cameras_bp.route('/', methods=['GET'])
@jwt_required()
def get_cameras():
    try:
        db = current_app.db
        cameras = db.get_all_cameras()
        return jsonify({"cameras": cameras})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
