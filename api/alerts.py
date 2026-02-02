"""Alerts API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/', methods=['GET'])
@jwt_required()
def get_alerts():
    try:
        db = current_app.db
        severity = request.args.get('severity')
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', 100))
        
        alerts = db.get_alerts(severity=severity, event_type=event_type, limit=limit)
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@alerts_bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if alert:
            return jsonify({"alert": alert})
        return jsonify({"error": "Alert not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
