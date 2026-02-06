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

@alerts_bp.route('/recent', methods=['GET'])
@jwt_required()
def get_recent_alerts():
    """Get recent alerts with optional limit"""
    try:
        db = current_app.db
        limit = int(request.args.get('limit', 10))
        alerts = db.get_alerts(limit=limit)
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

@alerts_bp.route('/<int:alert_id>/resolve', methods=['PUT'])
@jwt_required()
def resolve_alert(alert_id):
    """Mark an alert as resolved/dismissed"""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        db.dismiss_alert(alert_id)
        return jsonify({"message": "Alert resolved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@alerts_bp.route('/<int:alert_id>/dismiss', methods=['PUT'])
@jwt_required()
def dismiss_alert(alert_id):
    """Alias for resolve - dismiss an alert"""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        db.dismiss_alert(alert_id)
        return jsonify({"message": "Alert dismissed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@alerts_bp.route('/<int:alert_id>', methods=['DELETE'])
@jwt_required()
def delete_alert(alert_id):
    """Delete an alert permanently"""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        db.delete_alert(alert_id)
        return jsonify({"message": "Alert deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@alerts_bp.route('/clear', methods=['DELETE'])
@jwt_required()
def clear_all_alerts():
    """Clear all alerts"""
    try:
        db = current_app.db
        db.clear_alerts()
        return jsonify({"message": "All alerts cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
