from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .auth import login_required
from .dashboards import fco_dashboard, management_dashboard
from .db import get_db

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    role = session.get("role")
    if role == "management":
        return redirect(url_for("main.management_page"))
    if role == "fco":
        return redirect(url_for("main.fco_page"))
    return redirect(url_for("main.login_page"))


@bp.get("/login")
def login_page():
    return render_template("login.html")


@bp.post("/api/login")
def api_login():
    body = request.get_json(silent=True) or {}
    user = get_db().execute("SELECT * FROM users WHERE username = ?",
                            (str(body.get("username", "")).strip().lower(),)).fetchone()
    if not user or not check_password_hash(user["password_hash"], str(body.get("password", ""))):
        return jsonify(error="Wrong username or password."), 401
    session.clear()
    session.update(user_id=user["id"], role=user["role"], fco_id=user["fco_id"])
    return jsonify(next=url_for("main.home"))


@bp.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/management")
@login_required("management")
def management_page():
    return render_template("management.html")


@bp.get("/my-bonus")
@login_required("fco")
def fco_page():
    return render_template("fco.html")


@bp.get("/api/management/dashboard")
@login_required("management")
def api_management():
    return jsonify(management_dashboard(get_db(), current_app.config))


@bp.get("/api/fco/dashboard")
@login_required("fco")
def api_fco():
    return jsonify(fco_dashboard(get_db(), current_app.config, session["fco_id"]))


@bp.get("/healthz")
def healthz():
    get_db().execute("SELECT 1")
    return jsonify(status="ok")
