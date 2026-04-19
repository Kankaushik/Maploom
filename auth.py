from __future__ import annotations
import os
from functools import wraps
from flask import request, session, jsonify
from dotenv import load_dotenv

load_dotenv()
SESSION_KEY = os.getenv("FLASK_SECRET", "change-me-please")

def init_app(app):
    app.secret_key = SESSION_KEY

def login_user(user_id: int, role: str):
    session["uid"] = user_id
    session["role"] = role

def logout_user():
    session.clear()

def current_role() -> str | None:
    return session.get("role")

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper
