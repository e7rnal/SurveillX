"""
WebRTC API Blueprint - Placeholder
WebRTC was removed due to media transport issues (see docs/webrtc_postmortem.md).
Streaming is handled via Socket.IO through services/stream_handler.py.
"""
import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

webrtc_bp = Blueprint('webrtc', __name__)


@webrtc_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get streaming stats."""
    return jsonify({
        "available": False,
        "message": "WebRTC disabled. Use Socket.IO streaming instead.",
        "streaming_endpoint": "/stream (Socket.IO namespace)"
    })
