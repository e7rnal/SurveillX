"""Authentication API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    try:
        db = current_app.db
        query = "SELECT * FROM admin_users WHERE username = %s"
        results = db.execute_query(query, (username,))
        
        if not results:
            return jsonify({"error": "Invalid credentials"}), 401
        
        user = results[0]
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            access_token = create_access_token(identity=username)
            return jsonify({
                "token": access_token,
                "user": {
                    "username": user['username'],
                    "role": user.get('role', 'admin')  # Default to admin if role column missing
                }
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

