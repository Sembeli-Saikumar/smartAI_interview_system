# app/auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import email_exists, create_user, get_user_by_email
from database import execute_query

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("auth.register"))

        if email_exists(email):
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))

        hashed_password = generate_password_hash(password)
        create_user(name=name, email=email, hashed_password=hashed_password)

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.login"))

        user = get_user_by_email(email)

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("auth.login"))

        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]

        flash(f"Welcome, {user['name']}!", "success")

        role = user["role"]
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "interviewer":
            return redirect(url_for("interviewer.dashboard"))
        else:
            return redirect(url_for("auth.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please login to access the dashboard.", "warning")
        return redirect(url_for("auth.login"))

    if session.get("user_role") == "admin":
        return redirect(url_for("admin.dashboard"))
    if session.get("user_role") == "interviewer":
        return redirect(url_for("interviewer.dashboard"))

    user_id = session["user_id"]

    # ── Live Stats ───────────────────────────────────────────
    # Resume count
    resume_row = execute_query(
        "SELECT COUNT(*) as count FROM resumes WHERE user_id=%s",
        (user_id,), fetch=True
    )
    resume_count = resume_row[0]["count"] if resume_row else 0

    # Interview count
    interview_row = execute_query(
        "SELECT COUNT(*) as count FROM interview_sessions WHERE user_id=%s",
        (user_id,), fetch=True
    )
    interview_count = interview_row[0]["count"] if interview_row else 0

    # Average score
    score_row = execute_query(
        "SELECT AVG(total_score) as avg FROM interview_sessions WHERE user_id=%s AND total_score IS NOT NULL AND completed_at IS NOT NULL",
        (user_id,), fetch=True
    )
    avg_score = round(score_row[0]["avg"], 1) if score_row and score_row[0]["avg"] else 0

    # Best resume score
    best_resume = execute_query(
        "SELECT overall_score, original_filename FROM resumes WHERE user_id=%s ORDER BY overall_score DESC LIMIT 1",
        (user_id,), fetch=True
    )
    best_score    = best_resume[0]["overall_score"] if best_resume else 0
    best_filename = best_resume[0]["original_filename"] if best_resume else "No resume"

    # Recent interviews
    recent_interviews = execute_query(
        """SELECT id, started_at, completed_at, total_score
           FROM interview_sessions
           WHERE user_id=%s
           ORDER BY started_at DESC LIMIT 5""",
        (user_id,), fetch=True
    )

    return render_template(
        "auth/dashboard.html",
        resume_count      = resume_count,
        interview_count   = interview_count,
        avg_score         = avg_score,
        best_score        = best_score,
        best_filename     = best_filename,
        recent_interviews = recent_interviews or [],
    )


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))