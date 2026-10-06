"""Session login + role guards. Roles: 'management' (sees all) and 'fco' (own row + leader)."""
from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_required(role: str):
    """Protect a route. API requests get JSON 401/403; page requests get redirected."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            wants_json = request.path.startswith("/api/")
            if "user_id" not in session:
                return (jsonify(error="Please sign in."), 401) if wants_json \
                    else redirect(url_for("main.login_page"))
            if session.get("role") != role:
                return (jsonify(error="Not allowed."), 403) if wants_json \
                    else redirect(url_for("main.home"))
            return fn(*a, **kw)
        return wrapper
    return deco
