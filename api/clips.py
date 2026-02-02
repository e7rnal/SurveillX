"""
Video Clips API - Manage security alert video clips
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required
import os
from pathlib import Path

clips_bp = Blueprint('clips', __name__)

@clips_bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_clip(alert_id):
    """Get video clip for alert"""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        if not alert['clip_path']:
            return jsonify({"error": "No clip available for this alert"}), 404
        
        clip_path = alert['clip_path']
        if not os.path.exists(clip_path):
            return jsonify({"error": "Clip file not found"}), 404
        
        return send_file(clip_path, mimetype='video/mp4')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clips_bp.route('/list', methods=['GET'])
@jwt_required()
def list_clips():
    """List all available clips"""
    try:
        clips_dir = current_app.config['CLIPS_DIR']
        clips = []
        
        if os.path.exists(clips_dir):
            for root, dirs, files in os.walk(clips_dir):
                for file in files:
                    if file.endswith('.mp4'):
                        full_path = os.path.join(root, file)
                        clips.append({
                            "filename": file,
                            "path": full_path,
                            "size": os.path.getsize(full_path),
                            "created": os.path.getctime(full_path)
                        })
        
        return jsonify({"clips": clips})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clips_bp.route('/download/<int:alert_id>', methods=['GET'])
@jwt_required()
def download_clip(alert_id):
    """Download video clip"""
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        
        if not alert or not alert['clip_path']:
            return jsonify({"error": "Clip not found"}), 404
        
        return send_file(
            alert['clip_path'],
            as_attachment=True,
            download_name=f"alert_{alert_id}_clip.mp4"
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@clips_bp.route('/storage-stats', methods=['GET'])
@jwt_required()
def storage_stats():
    """Get storage statistics"""
    try:
        clips_dir = current_app.config['CLIPS_DIR']
        total_size = 0
        total_clips = 0
        
        if os.path.exists(clips_dir):
            for root, dirs, files in os.walk(clips_dir):
                for file in files:
                    if file.endswith('.mp4'):
                        total_clips += 1
                        total_size += os.path.getsize(os.path.join(root, file))
        
        return jsonify({
            "total_clips": total_clips,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
