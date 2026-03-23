# app/__init__.py
import os
from flask import Flask, redirect, url_for, session, request, abort
from config import get_config
from database import init_db, close_db

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ── Config ────────────────────────────────────────────────
    app.config.from_object(get_config())

    # ── Security Headers ──────────────────────────────────────
    try:
        from flask_talisman import Talisman
        Talisman(app,
            force_https=False,          # True in production with SSL
            strict_transport_security=False,
            content_security_policy=False,
            x_content_type_options=True,
            x_xss_protection=True,
        )
    except Exception as e:
        print(f"[Talisman] Skipped: {e}")

    # ── Rate Limiting ─────────────────────────────────────────
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
        limiter = Limiter(
            get_remote_address,
            app=app,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://",
        )
        app.limiter = limiter
    except Exception as e:
        print(f"[Limiter] Skipped: {e}")

    # ── Database ──────────────────────────────────────────────
    init_db(app)
    app.teardown_appcontext(close_db)

    # ── Blueprints ────────────────────────────────────────────
    from app.auth.routes       import auth_bp
    from app.resume.routes     import resume_bp
    from app.interview.routes  import interview_bp
    from app.admin.routes      import admin_bp
    from app.interviewer.routes import interviewer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(interviewer_bp)

    # ── Security Middleware ───────────────────────────────────
    @app.before_request
    def security_checks():
        # Block direct static file access for sensitive files
        if request.path.startswith('/static/uploads/'):
            if 'user_id' not in session:
                abort(403)

        # Block suspicious user agents
        ua = request.headers.get('User-Agent', '').lower()
        blocked_agents = ['sqlmap', 'nikto', 'nmap', 'masscan', 'zgrab']
        if any(agent in ua for agent in blocked_agents):
            abort(403)

    # ── Security Headers on every response ───────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options']        = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection']       = '1; mode=block'
        response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control']           = 'no-store, no-cache, must-revalidate'
        return response

    # ── Routes ────────────────────────────────────────────────
    @app.route("/")
    def index():
        if 'user_id' in session:
            role = session.get('user_role')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'interviewer':
                return redirect(url_for('interviewer.dashboard'))
        return redirect(url_for("auth.login"))

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    # ── Error Handlers ────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return {"error": "Access denied"}, 403

    @app.errorhandler(404)
    def not_found(e):
        return redirect(url_for("auth.login"))

    @app.errorhandler(429)
    def rate_limited(e):
        return {"error": "Too many requests. Please wait."}, 429

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    return app