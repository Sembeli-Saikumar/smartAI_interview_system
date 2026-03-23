# app/admin/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, Response
from app.models.admin import get_total_stats, get_all_users, get_all_resumes, get_all_interviews, delete_user
from database import execute_query
from werkzeug.security import generate_password_hash
import csv
import io
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("user_role") != "admin":
            flash("Admin access only.", "danger")
            return redirect(url_for("auth.dashboard"))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    search = request.args.get("search", "").strip()

    stats      = get_total_stats()
    resumes    = get_all_resumes()
    interviews = get_all_interviews()

    # Search users
    if search:
        users = execute_query(
            "SELECT * FROM users WHERE name LIKE %s OR email LIKE %s ORDER BY created_at DESC",
            (f"%{search}%", f"%{search}%"), fetch=True
        )
    else:
        users = get_all_users()

    # File size display
    for r in resumes:
        size = r["file_size"]
        if size < 1024:            r["size_display"] = f"{size} B"
        elif size < 1024*1024:     r["size_display"] = f"{size/1024:.1f} KB"
        else:                      r["size_display"] = f"{size/(1024*1024):.1f} MB"

    # Analytics — interviews per day (last 7 days)
    daily_interviews = execute_query(
        """SELECT DATE(started_at) as day, COUNT(*) as count
           FROM interview_sessions
           WHERE started_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
           GROUP BY DATE(started_at) ORDER BY day""",
        fetch=True
    )

    # Score distribution
    score_dist = execute_query(
        """SELECT
            SUM(CASE WHEN total_score >= 80 THEN 1 ELSE 0 END) as excellent,
            SUM(CASE WHEN total_score >= 60 AND total_score < 80 THEN 1 ELSE 0 END) as good,
            SUM(CASE WHEN total_score >= 40 AND total_score < 60 THEN 1 ELSE 0 END) as average,
            SUM(CASE WHEN total_score < 40 AND total_score IS NOT NULL THEN 1 ELSE 0 END) as poor
           FROM interview_sessions WHERE completed_at IS NOT NULL""",
        fetch=True
    )

    # Leaderboard — top 5 candidates
    leaderboard = execute_query(
        """SELECT u.name, u.email,
            COUNT(s.id) as total_interviews,
            MAX(s.total_score) as best_score,
            AVG(s.total_score) as avg_score
           FROM users u
           JOIN interview_sessions s ON s.user_id = u.id
           WHERE s.completed_at IS NOT NULL AND s.total_score IS NOT NULL
           GROUP BY u.id ORDER BY avg_score DESC LIMIT 5""",
        fetch=True
    )

    # Interviewers
    interviewers = execute_query(
        """SELECT u.id, u.name, u.email, u.created_at,
            COALESCE(u.is_active, 1) as is_active,
            COUNT(s.id) as session_count
           FROM users u
           LEFT JOIN interview_sessions s ON s.user_id = u.id
           WHERE u.role = 'interviewer'
           GROUP BY u.id ORDER BY u.created_at DESC""",
        fetch=True
    )

    # Schedules
    schedules = execute_query(
        """SELECT sc.*, c.name as candidate_name, c.email as candidate_email,
            i.name as interviewer_name
           FROM interview_schedules sc
           JOIN users c ON c.id = sc.candidate_id
           LEFT JOIN users i ON i.id = sc.interviewer_id
           ORDER BY sc.scheduled_at DESC LIMIT 20""",
        fetch=True
    ) if _table_exists("interview_schedules") else []

    # Candidates for schedule dropdown
    candidates = execute_query(
        "SELECT id, name, email FROM users WHERE role='candidate' ORDER BY name",
        fetch=True
    )

    # Skills analytics from resumes
    skills_raw = execute_query(
        "SELECT skills FROM resumes WHERE skills IS NOT NULL AND skills != ''",
        fetch=True
    ) or []
    skill_counts = {}
    for row in skills_raw:
        for sk in (row["skills"] or "").split(","):
            sk = sk.strip()
            if sk:
                skill_counts[sk] = skill_counts.get(sk, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Recent activity feed
    recent_users = execute_query(
        "SELECT name, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 5",
        fetch=True
    ) or []
    recent_resumes = execute_query(
        """SELECT u.name, r.original_filename, r.uploaded_at, r.overall_score
           FROM resumes r JOIN users u ON u.id=r.user_id
           ORDER BY r.uploaded_at DESC LIMIT 5""",
        fetch=True
    ) or []
    recent_interviews_done = execute_query(
        """SELECT u.name, s.completed_at, s.total_score
           FROM interview_sessions s JOIN users u ON u.id=s.user_id
           WHERE s.completed_at IS NOT NULL
           ORDER BY s.completed_at DESC LIMIT 5""",
        fetch=True
    ) or []

    # Live / active sessions
    live_sessions = execute_query(
        """SELECT s.id, u.name, u.email, s.started_at,
               COUNT(a.id) as answer_count
           FROM interview_sessions s
           JOIN users u ON u.id=s.user_id
           LEFT JOIN interview_answers a ON a.session_id=s.id
           WHERE s.completed_at IS NULL
           GROUP BY s.id ORDER BY s.started_at DESC LIMIT 10""",
        fetch=True
    ) or []

    # System health
    avg_score_all = execute_query(
        "SELECT ROUND(AVG(total_score),1) as avg FROM interview_sessions WHERE total_score IS NOT NULL",
        fetch=True
    )
    total_answers = execute_query(
        "SELECT COUNT(*) as c FROM interview_answers", fetch=True
    )
    avg_score_val = avg_score_all[0]["avg"] if avg_score_all and avg_score_all[0]["avg"] else 0
    total_api_calls = total_answers[0]["c"] if total_answers else 0

    import time
    uptime_hours = round((time.time() - getattr(dashboard, '_start', time.time())) / 3600, 1)
    if not hasattr(dashboard, '_start'):
        dashboard._start = time.time()

    return render_template(
        "admin/dashboard.html",
        stats                  = stats,
        users                  = users or [],
        resumes                = resumes or [],
        interviews             = interviews or [],
        daily_interviews       = daily_interviews or [],
        score_dist             = score_dist[0] if score_dist else {},
        leaderboard            = leaderboard or [],
        interviewers           = interviewers or [],
        schedules              = schedules or [],
        candidates             = candidates or [],
        search                 = search,
        top_skills             = top_skills or [],
        recent_users           = recent_users,
        recent_resumes         = recent_resumes,
        recent_interviews_done = recent_interviews_done,
        live_sessions          = live_sessions,
        avg_score_val          = avg_score_val,
        total_api_calls        = total_api_calls,
        uptime_hours           = uptime_hours,
    )


def _table_exists(table_name):
    try:
        result = execute_query(
            "SELECT COUNT(*) as c FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s",
            (table_name,), fetch=True
        )
        return result and result[0]["c"] > 0
    except:
        return False


# ── Delete User ───────────────────────────────────────────────
@admin_bp.route("/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def remove_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.dashboard"))
    delete_user(user_id)
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.dashboard"))


# ── Add Interviewer ───────────────────────────────────────────
@admin_bp.route("/add-interviewer", methods=["POST"])
@admin_required
def add_interviewer():
    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        flash("All fields required.", "danger")
        return redirect(url_for("admin.dashboard"))

    existing = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetch=True)
    if existing:
        flash("Email already exists.", "danger")
        return redirect(url_for("admin.dashboard"))

    execute_query(
        "INSERT INTO users (name, email, password, role, created_at) VALUES (%s,%s,%s,'interviewer',%s)",
        (name, email, generate_password_hash(password), datetime.now())
    )

    # ── Send welcome email to interviewer ─────────────────────
    try:
        from app.email_service import send_interviewer_welcome
        send_interviewer_welcome(name, email, password)
    except Exception as e:
        print(f"[Email Error] {e}")

    flash(f"Interviewer '{name}' added & welcome email sent!", "success")
    return redirect(url_for("admin.dashboard"))


# ── Toggle Interviewer Active ─────────────────────────────────
@admin_bp.route("/toggle-interviewer/<int:user_id>", methods=["POST"])
@admin_required
def toggle_interviewer(user_id):
    user = execute_query("SELECT is_active, name FROM users WHERE id=%s", (user_id,), fetch=True)
    if user:
        new_status = 0 if user[0].get("is_active", 1) else 1
        execute_query("UPDATE users SET is_active=%s WHERE id=%s", (new_status, user_id))
        status_text = "activated" if new_status else "deactivated"
        flash(f"Interviewer {status_text} successfully.", "success")
    return redirect(url_for("admin.dashboard"))


# ── Change User Role ──────────────────────────────────────────
@admin_bp.route("/change-role/<int:user_id>", methods=["POST"])
@admin_required
def change_role(user_id):
    new_role = request.form.get("role")
    if new_role not in ("admin", "interviewer", "candidate"):
        flash("Invalid role.", "danger")
        return redirect(url_for("admin.dashboard"))
    if user_id == session["user_id"]:
        flash("Cannot change your own role.", "danger")
        return redirect(url_for("admin.dashboard"))
    execute_query("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id))
    flash("Role updated successfully.", "success")
    return redirect(url_for("admin.dashboard"))


# ── Schedule Interview ────────────────────────────────────────
@admin_bp.route("/schedule-interview", methods=["POST"])
@admin_required
def schedule_interview():
    if not _table_exists("interview_schedules"):
        execute_query("""CREATE TABLE IF NOT EXISTS interview_schedules (
            id INT AUTO_INCREMENT PRIMARY KEY,
            candidate_id INT NOT NULL,
            interviewer_id INT,
            scheduled_at DATETIME NOT NULL,
            duration_minutes INT DEFAULT 60,
            title VARCHAR(255) DEFAULT 'Mock Interview',
            status ENUM('pending','approved','rejected','completed') DEFAULT 'pending',
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE
        )""")

    candidate_id   = request.form.get("candidate_id")
    interviewer_id = request.form.get("interviewer_id") or None
    scheduled_at   = request.form.get("scheduled_at")
    title          = request.form.get("title", "Mock Interview")
    notes          = request.form.get("notes", "")

    execute_query(
        """INSERT INTO interview_schedules
           (candidate_id, interviewer_id, scheduled_at, title, notes, status)
           VALUES (%s,%s,%s,%s,%s,'pending')""",
        (candidate_id, interviewer_id, scheduled_at, title, notes)
    )
    flash("Interview scheduled successfully!", "success")
    return redirect(url_for("admin.dashboard"))


# ── Approve/Reject Schedule ───────────────────────────────────
@admin_bp.route("/schedule/<int:schedule_id>/<action>", methods=["POST"])
@admin_required
def update_schedule(schedule_id, action):
    if action in ("approved", "rejected", "completed"):
        execute_query(
            "UPDATE interview_schedules SET status=%s WHERE id=%s",
            (action, schedule_id)
        )
        # email on approve
        if action == "approved":
            try:
                from app.email_service import send_schedule_approved
                sc = execute_query("""SELECT sc.title, sc.scheduled_at, c.name as cname, c.email as cemail, i.name as iname FROM interview_schedules sc JOIN users c ON c.id=sc.candidate_id LEFT JOIN users i ON i.id=sc.interviewer_id WHERE sc.id=%s""", (schedule_id,), fetch=True)
                if sc:
                    s = sc[0]
                    send_schedule_approved(s["cname"], s["cemail"], s["title"], str(s["scheduled_at"]), s.get("iname"))
            except Exception as e:
                print(f"[Email Error] {e}")
        flash(f"Schedule {action} done!", "success")
    return redirect(url_for("admin.dashboard"))


# ── Export CSV ────────────────────────────────────────────────
@admin_bp.route("/export-users")
@admin_required
def export_users():
    users = execute_query(
        """SELECT u.name, u.email, u.role, u.created_at,
            COUNT(s.id) as interviews,
            AVG(s.total_score) as avg_score
           FROM users u
           LEFT JOIN interview_sessions s ON s.user_id = u.id
           GROUP BY u.id ORDER BY u.created_at DESC""",
        fetch=True
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Role", "Joined", "Interviews", "Avg Score"])
    for u in users:
        writer.writerow([
            u["name"], u["email"], u["role"],
            u["created_at"], u["interviews"],
            round(u["avg_score"], 1) if u["avg_score"] else 0
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=users_export.csv"}
    )


@admin_bp.route("/export-interviews")
@admin_required
def export_interviews():
    interviews = execute_query(
        """SELECT u.name, u.email, s.started_at, s.completed_at, s.total_score
           FROM interview_sessions s
           JOIN users u ON u.id = s.user_id
           ORDER BY s.started_at DESC""",
        fetch=True
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate", "Email", "Started", "Completed", "Score"])
    for i in interviews:
        writer.writerow([
            i["name"], i["email"], i["started_at"],
            i["completed_at"] or "In Progress", i["total_score"] or 0
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=interviews_export.csv"}
    )