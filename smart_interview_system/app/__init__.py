# app/__init__.py
import os
from flask import Flask, redirect, url_for
from config import get_config
from database import init_db, close_db


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Load config from config.py
    app.config.from_object(get_config())

    # Initialise MySQL connection pool
    init_db(app)

    # Return DB connection to pool after every request
    app.teardown_appcontext(close_db)

    # Register Blueprints
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.resume.routes import resume_bp
    app.register_blueprint(resume_bp)

    from app.interview.routes import interview_bp
    app.register_blueprint(interview_bp)

    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    from app.interviewer.routes import interviewer_bp
    app.register_blueprint(interviewer_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @app.route("/health")
    def health():
        return {"status": "ok", "app": "Smart Interview System"}, 200

    return app