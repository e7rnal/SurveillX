"""Statistics API"""
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/', methods=['GET'])
@jwt_required()
def get_stats():
    try:
        db = current_app.db
        stats = db.get_dashboard_stats()
        return jsonify({"stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
