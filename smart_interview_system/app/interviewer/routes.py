from flask import Blueprint, render_template, session, redirect, url_for, flash
from database import execute_query

interviewer_bp = Blueprint("interviewer", __name__, url_prefix="/interviewer")

def interviewer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("user_role") not in ("interviewer", "admin"):
            flash("Interviewer access only.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

@interviewer_bp.route("/dashboard")
@interviewer_required
def dashboard():
    interviews = execute_query(
        """SELECT s.id, s.started_at, s.completed_at, s.total_score,
               u.name AS candidate_name, u.email AS candidate_email,
               COUNT(a.id) AS answer_count
        FROM interview_sessions s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN interview_answers a ON a.session_id = s.id
        GROUP BY s.id
        ORDER BY s.started_at DESC""",
        fetch=True,
    )
    total     = len(interviews) if interviews else 0
    completed = sum(1 for i in interviews if i["completed_at"]) if interviews else 0
    ongoing   = total - completed
    return render_template("interviewer/dashboard.html", interviews=interviews or [], total=total, completed=completed, ongoing=ongoing)

@interviewer_bp.route("/session/<int:session_id>")
@interviewer_required
def view_session(session_id):
    answers = execute_query(
        """SELECT a.question, a.answer, a.score, a.feedback, u.name AS candidate_name
        FROM interview_answers a
        JOIN interview_sessions s ON s.id = a.session_id
        JOIN users u ON u.id = s.user_id
        WHERE a.session_id = %s ORDER BY a.id""",
        (session_id,), fetch=True,
    )
    return render_template("interviewer/session.html", answers=answers or [], session_id=session_id)
