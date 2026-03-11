# app/admin/routes.py
# Admin panel — only accessible by role='admin'

from flask import (
    Blueprint, render_template, session,
    redirect, url_for, flash
)
from app.models.admin import (
    get_total_stats,
    get_all_users,
    get_all_resumes,
    get_all_interviews,
    delete_user,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Admin guard ───────────────────────────────────────────────
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
    stats      = get_total_stats()
    users      = get_all_users()
    resumes    = get_all_resumes()
    interviews = get_all_interviews()

    # Human readable file size for resumes
    for r in resumes:
        size = r["file_size"]
        if size < 1024:
            r["size_display"] = f"{size} B"
        elif size < 1024 * 1024:
            r["size_display"] = f"{size/1024:.1f} KB"
        else:
            r["size_display"] = f"{size/(1024*1024):.1f} MB"

    return render_template(
        "admin/dashboard.html",
        stats      = stats,
        users      = users,
        resumes    = resumes,
        interviews = interviews,
    )


# ── Delete User ───────────────────────────────────────────────
@admin_bp.route("/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def remove_user(user_id: int):
    # Prevent admin from deleting themselves
    if user_id == session["user_id"]:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.dashboard"))

    delete_user(user_id)
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.dashboard"))