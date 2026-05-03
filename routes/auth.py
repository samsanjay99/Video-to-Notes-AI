import os
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
import jwt

from extensions import db
from models.user import User
from middleware.auth import auth_required, SECRET_KEY

auth_bp = Blueprint("auth", __name__)


def make_token(user_id: str) -> str:
    payload = {
        "userId": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# ── POST /api/auth/register ───────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(name) < 2:
        return jsonify({"success": False, "message": "Name must be at least 2 characters"}), 400
    if "@" not in email:
        return jsonify({"success": False, "message": "Valid email required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 400

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"success": True, "token": make_token(user.id), "user": user.to_dict()}), 201


# ── POST /api/auth/login ──────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    # Auto-create demo account
    if not user and email == "demo@meetmind.ai" and password == "demo123":
        user = User(name="Demo User", email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

    if not user or not user.verify_password(password):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    return jsonify({"success": True, "token": make_token(user.id), "user": user.to_dict()})


# ── GET /api/auth/me ──────────────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@auth_required
def me(current_user):
    return jsonify({"success": True, "user": current_user.to_dict()})


# ── PUT /api/auth/profile ─────────────────────────────────────────────────────
@auth_bp.route("/profile", methods=["PUT"])
@auth_required
def update_profile(current_user):
    data = request.get_json() or {}
    if data.get("name"):
        current_user.name = data["name"]
    if data.get("preferences"):
        current_user.preferences = {**(current_user.preferences or {}), **data["preferences"]}
    db.session.commit()
    return jsonify({"success": True, "user": current_user.to_dict()})
