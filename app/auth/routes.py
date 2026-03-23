# app/auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import execute_query
from datetime import datetime

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Register ──────────────────────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role     = request.form.get("role", "candidate")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        existing = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetch=True)
        if existing:
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        execute_query(
            "INSERT INTO users (name, email, password, role, created_at) VALUES (%s,%s,%s,%s,%s)",
            (name, email, generate_password_hash(password), role, datetime.now())
        )

        # ── Send emails ───────────────────────────────────────
        try:
            from app.email_service import send_interviewer_registered_admin, send_interviewer_welcome
            # Notify admin about new registration
            send_interviewer_registered_admin(name, email)
            # Send welcome mail to interviewer with login details
            send_interviewer_welcome(name, email, password)
            print(f"[Email] Registration emails sent for {email}")
        except Exception as e:
            print(f"[Email Error] {e}")

        flash("Account created! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ── Login ─────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = execute_query("SELECT * FROM users WHERE email=%s", (email,), fetch=True)

        if not user:
            flash("Email not found.", "danger")
            return redirect(url_for("auth.login"))

        user = user[0]

        if not check_password_hash(user["password"], password):
            flash("Incorrect password.", "danger")
            return redirect(url_for("auth.login"))

        # ── Interviewer login block ────────────────────────────
        if user["role"] == "interviewer" and not user.get("is_active", 1):
            flash("Your account is deactivated. Please contact admin.", "danger")
            return redirect(url_for("auth.login"))

        session["user_id"]   = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]
        session["user_email"]= user["email"]

        if user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        elif user["role"] == "interviewer":
            return redirect(url_for("interviewer.dashboard"))
        else:
            return redirect(url_for("interviewer.dashboard"))

    return render_template("auth/login.html")


# ── Dashboard (Candidate) ─────────────────────────────────────
@auth_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    resume_count = execute_query(
        "SELECT COUNT(*) as c FROM resumes WHERE user_id=%s", (user_id,), fetch=True
    )
    interview_count = execute_query(
        "SELECT COUNT(*) as c FROM interview_sessions WHERE user_id=%s", (user_id,), fetch=True
    )
    avg_score = execute_query(
        "SELECT AVG(total_score) as avg FROM interview_sessions WHERE user_id=%s AND total_score IS NOT NULL",
        (user_id,), fetch=True
    )
    best_resume = execute_query(
        "SELECT MAX(overall_score) as best FROM resumes WHERE user_id=%s", (user_id,), fetch=True
    )

    stats = {
        "resume_count"   : resume_count[0]["c"] if resume_count else 0,
        "interview_count": interview_count[0]["c"] if interview_count else 0,
        "avg_score"      : round(avg_score[0]["avg"], 1) if avg_score and avg_score[0]["avg"] else 0,
        "best_resume"    : best_resume[0]["best"] if best_resume and best_resume[0]["best"] else 0,
    }

    return render_template("auth/dashboard.html", stats=stats)


# ── Logout ────────────────────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))