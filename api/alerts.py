"""Alerts API — with snapshots, status management, pagination"""
import os
import json
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from datetime import datetime

alerts_bp = Blueprint('alerts', __name__)

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'snapshots')
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


@alerts_bp.route('/', methods=['GET'])
@jwt_required()
def get_alerts():
    """Get alerts with pagination, status filter, date filter."""
    try:
        db = current_app.db
        severity = request.args.get('severity')
        event_type = request.args.get('event_type')
        status = request.args.get('status')
        date = request.args.get('date')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        alerts, total = db.get_alerts_paginated(
            severity=severity,
            event_type=event_type,
            status=status,
            date=date,
            page=page,
            per_page=per_page,
        )

        # Serialize timestamps and metadata
        for a in alerts:
            if isinstance(a.get('timestamp'), datetime):
                a['timestamp'] = a['timestamp'].isoformat() + 'Z'
            if isinstance(a.get('resolved_at'), datetime):
                a['resolved_at'] = a['resolved_at'].isoformat() + 'Z'
            if isinstance(a.get('created_at'), datetime):
                a['created_at'] = a['created_at'].isoformat() + 'Z'
            if isinstance(a.get('metadata'), str):
                try:
                    a['metadata'] = json.loads(a['metadata'])
                except Exception:
                    pass
            # Ensure status field
            if not a.get('status'):
                a['status'] = 'unresolved'

        return jsonify({
            "alerts": alerts,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/', methods=['POST'])
def create_alert():
    """Create alert — internal endpoint (no JWT), used by Flask auto-alert."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        db = current_app.db
        alert_id = db.create_alert_with_snapshot(
            event_type=data.get('event_type', 'unknown'),
            camera_id=data.get('camera_id', 1),
            clip_path=data.get('clip_path'),
            severity=data.get('severity', 'medium'),
            metadata=data.get('metadata', {}),
            snapshot_path=data.get('snapshot_path'),
            student_id=data.get('student_id'),
        )
        return jsonify({"alert_id": alert_id, "message": "Alert created"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/recent', methods=['GET'])
@jwt_required()
def get_recent_alerts():
    """Get recent alerts with optional limit."""
    try:
        db = current_app.db
        limit = int(request.args.get('limit', 10))
        alerts, _ = db.get_alerts_paginated(per_page=limit, page=1)

        for a in alerts:
            if isinstance(a.get('timestamp'), datetime):
                a['timestamp'] = a['timestamp'].isoformat() + 'Z'
            if isinstance(a.get('metadata'), str):
                try:
                    a['metadata'] = json.loads(a['metadata'])
                except Exception:
                    pass
            if not a.get('status'):
                a['status'] = 'unresolved'

        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/stats', methods=['GET'])
@jwt_required()
def alerts_stats():
    """Alert count by severity in last 24 hours."""
    try:
        db = current_app.db
        query = """
            SELECT severity, COUNT(*) as count
            FROM alerts_logs
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY severity
        """
        results = db.execute_query(query)
        total = sum(r['count'] for r in results)
        by_severity = {r['severity']: r['count'] for r in results}
        return jsonify({
            "total": total,
            "by_severity": by_severity,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404

        if isinstance(alert.get('timestamp'), datetime):
            alert['timestamp'] = alert['timestamp'].isoformat() + 'Z'
        if isinstance(alert.get('resolved_at'), datetime):
            alert['resolved_at'] = alert['resolved_at'].isoformat() + 'Z'
        if isinstance(alert.get('metadata'), str):
            try:
                alert['metadata'] = json.loads(alert['metadata'])
            except Exception:
                pass
        if not alert.get('status'):
            alert['status'] = 'unresolved'

        # Include student name if linked
        if alert.get('student_id'):
            student = db.get_student_by_id(alert['student_id'])
            alert['student_name'] = student['name'] if student else None

        return jsonify({"alert": alert})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/<int:alert_id>/resolve', methods=['PUT'])
@jwt_required()
def resolve_alert(alert_id):
    """Mark alert as resolved."""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        db.update_alert_status(alert_id, 'resolved')
        return jsonify({"message": "Alert resolved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/<int:alert_id>/false-alarm', methods=['PUT'])
@jwt_required()
def false_alarm(alert_id):
    """Mark alert as false alarm."""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        db.update_alert_status(alert_id, 'false_alarm')
        return jsonify({"message": "Alert marked as false alarm"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/<int:alert_id>/dismiss', methods=['PUT'])
@jwt_required()
def dismiss_alert(alert_id):
    """Backwards-compat: dismiss = resolve."""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        db.update_alert_status(alert_id, 'resolved')
        return jsonify({"message": "Alert dismissed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/<int:alert_id>', methods=['DELETE'])
@jwt_required()
def delete_alert(alert_id):
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404

        # Delete snapshot file if exists
        if alert.get('snapshot_path'):
            full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     alert['snapshot_path'].lstrip('/'))
            if os.path.exists(full_path):
                os.remove(full_path)

        db.delete_alert(alert_id)
        return jsonify({"message": "Alert deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/clear', methods=['DELETE'])
@jwt_required()
def clear_all_alerts():
    try:
        db = current_app.db
        db.clear_alerts()
        return jsonify({"message": "All alerts cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/snapshot/<path:filename>', methods=['GET'])
def serve_snapshot(filename):
    """Serve alert snapshot images."""
    return send_from_directory(SNAPSHOT_DIR, filename)


@alerts_bp.route('/distribution', methods=['GET'])
@jwt_required()
def alert_distribution():
    """Alert distribution by event type (for dashboard chart)."""
    try:
        db = current_app.db
        days = int(request.args.get('days', 30))
        dist = db.get_alert_distribution(days=days)
        return jsonify({"distribution": dist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@alerts_bp.route('/test', methods=['POST'])
@jwt_required()
def create_test_alert():
    """Create a fake alert for testing the alert system."""
    import random
    try:
        db = current_app.db
        event_types = ['running', 'fighting', 'loitering', 'unauthorized_entry', 'suspicious_activity']
        severities = ['high', 'medium', 'low']

        event_type = request.json.get('event_type') if request.json else None
        severity = request.json.get('severity') if request.json else None

        event_type = event_type or random.choice(event_types)
        severity = severity or random.choice(severities)

        alert_id = db.create_alert(
            event_type=event_type,
            camera_id=random.randint(1, 4),
            clip_path=None,
            severity=severity,
            metadata=json.dumps({
                'description': f'Test {event_type} alert generated manually',
                'confidence': round(random.uniform(0.7, 0.99), 2),
                'test': True
            })
        )

        # Broadcast via SocketIO if available
        try:
            socketio = current_app.extensions.get('socketio')
            if socketio:
                socketio.emit('new_alert', {
                    'id': alert_id,
                    'type': event_type,
                    'severity': severity,
                    'camera_id': random.randint(1, 4),
                    'timestamp': datetime.now().isoformat() + 'Z'
                }, namespace='/stream')
        except Exception:
            pass

        return jsonify({
            "id": alert_id,
            "event_type": event_type,
            "severity": severity,
            "message": f"Test alert created: {event_type} ({severity})"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
