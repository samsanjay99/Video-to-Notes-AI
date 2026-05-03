import os
from functools import wraps
from flask import request, jsonify
import jwt

from models.user import User

SECRET_KEY = os.getenv("JWT_SECRET", "change_this_in_production")


def auth_required(f):
    """Decorator that validates JWT and injects current_user into kwargs."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Access denied. No token provided."}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("userId")
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token invalid"}), 401

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 401

        kwargs["current_user"] = user
        return f(*args, **kwargs)
    return decorated
