"""Application factory."""
import logging

from flask import Flask, request

from config import Config
from .db import close_db, connect, init_schema
from .jobs import run_daily_job


def create_app(overrides: dict = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["DATABASE_PATH"] = Config.db_path()
    if overrides:
        app.config.update(overrides)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env and set it.")

    import os
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    conn = connect(app.config["DATABASE_PATH"])
    init_schema(conn)
    conn.close()

    app.teardown_appcontext(close_db)

    from .routes import bp
    app.register_blueprint(bp)

    from .cli import register_cli
    register_cli(app)

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Content-Security-Policy"] = "default-src 'self'"
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    if app.config["ENABLE_SCHEDULER"]:
        _start_scheduler(app)
    return app


def _scheduled_daily(app: Flask) -> None:
    conn = connect(app.config["DATABASE_PATH"])
    try:
        ranked, locked = run_daily_job(conn, app.config)
        app.logger.info("Daily job ok: %d FCOs ranked, month locked now: %s", len(ranked), locked)
    except Exception:
        app.logger.exception("Daily job FAILED")
    finally:
        conn.close()


def _start_scheduler(app: Flask) -> None:
    """Cron '0 12 * * *' in WAT == every day at CALC_HOUR:00, weekends included."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    sched = BackgroundScheduler(timezone=app.config["TIMEZONE"])
    sched.add_job(_scheduled_daily, CronTrigger(hour=app.config["CALC_HOUR"], minute=0,
                                                timezone=app.config["TIMEZONE"]),
                  args=[app], id="daily_12pm", coalesce=True, misfire_grace_time=3600,
                  max_instances=1, replace_existing=True)
    sched.start()
    app.extensions["scheduler"] = sched
