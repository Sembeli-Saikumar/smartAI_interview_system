# app/interviewer/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from database import execute_query
from datetime import datetime
import os

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


def get_dashboard_data(user_id):
    interviews = execute_query(
        """SELECT s.id, s.started_at, s.completed_at, s.total_score,
               u.name AS candidate_name, u.email AS candidate_email,
               COUNT(a.id) AS answer_count
           FROM interview_sessions s
           JOIN users u ON u.id = s.user_id
           LEFT JOIN interview_answers a ON a.session_id = s.id
           WHERE s.user_id = %s
           GROUP BY s.id ORDER BY s.started_at DESC""",
        (user_id,), fetch=True,
    ) or []

    resumes = execute_query(
        """SELECT id, original_filename, file_path, file_size, file_type,
                  uploaded_at, overall_score, technical_score, experience_score,
                  education_score, skills, strengths, improvements
           FROM resumes WHERE user_id=%s ORDER BY uploaded_at DESC""",
        (user_id,), fetch=True
    ) or []

    for r in resumes:
        size = r["file_size"] or 0
        if size < 1024:         r["size_display"] = f"{size} B"
        elif size < 1024*1024:  r["size_display"] = f"{size/1024:.1f} KB"
        else:                   r["size_display"] = f"{size/(1024*1024):.1f} MB"

    total     = len(interviews)
    completed = sum(1 for i in interviews if i["completed_at"])
    ongoing   = total - completed
    scores    = [i["total_score"] for i in interviews if i["total_score"]]
    best_score = max(scores, default=0)
    avg_score  = round(sum(scores) / len(scores), 1) if scores else 0

    # AI Insights
    # Most difficult question (lowest avg score)
    hardest_q = execute_query(
        """SELECT question, AVG(score) as avg_score
           FROM interview_answers
           WHERE session_id IN (
               SELECT id FROM interview_sessions WHERE user_id=%s
           ) AND score IS NOT NULL AND question IS NOT NULL
           GROUP BY question ORDER BY avg_score ASC LIMIT 1""",
        (user_id,), fetch=True
    )
    hardest_question = hardest_q[0]["question"][:40] if hardest_q else "No data yet"

    # Most common weak skill (from resume improvements)
    weak_skills_raw = execute_query(
        "SELECT improvements FROM resumes WHERE user_id=%s AND improvements IS NOT NULL AND improvements != ''",
        (user_id,), fetch=True
    ) or []
    skill_freq = {}
    for row in weak_skills_raw:
        for sk in (row["improvements"] or "").split(","):
            sk = sk.strip()
            if sk:
                skill_freq[sk] = skill_freq.get(sk, 0) + 1
    weak_skill = max(skill_freq, key=skill_freq.get) if skill_freq else "No data yet"
    weak_skill = weak_skill[:28] if len(weak_skill) > 28 else weak_skill

    return dict(interviews=interviews, resumes=resumes, total=total,
                completed=completed, ongoing=ongoing,
                best_score=best_score, avg_score=avg_score,
                hardest_question=hardest_question, weak_skill=weak_skill)


@interviewer_bp.route("/dashboard")
@interviewer_required
def dashboard():
    data = get_dashboard_data(session["user_id"])
    return render_template("interviewer/dashboard.html", **data)


@interviewer_bp.route("/upload")
@interviewer_required
def upload_page():
    return render_template("interviewer/upload.html")


@interviewer_bp.route("/upload-resume", methods=["POST"])
@interviewer_required
def upload_resume():
    from werkzeug.utils import secure_filename
    import uuid

    file = request.files.get("resume")
    if not file or file.filename == "":
        flash("Please select a file.", "danger")
        return redirect(url_for("interviewer.upload_page"))

    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files allowed.", "danger")
        return redirect(url_for("interviewer.upload_page"))

    filename    = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    folder      = os.path.join("app", "static", "uploads")
    os.makedirs(folder, exist_ok=True)
    save_path   = os.path.join(folder, unique_name)
    file.save(save_path)

    file_size = os.path.getsize(save_path)
    file_path = f"uploads/{unique_name}"

    execute_query(
        """INSERT INTO resumes (user_id, original_filename, stored_filename,
           file_path, file_size, file_type, uploaded_at)
           VALUES (%s,%s,%s,%s,%s,'pdf',%s)""",
        (session["user_id"], filename, unique_name, file_path, file_size, datetime.now())
    )

    row = execute_query(
        "SELECT id FROM resumes WHERE user_id=%s ORDER BY uploaded_at DESC LIMIT 1",
        (session["user_id"],), fetch=True
    )
    resume_id = row[0]["id"] if row else None

    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(save_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        if text.strip() and resume_id:
            from app.ai_services.resume_analyzer import parse_resume, score_resume
            parsed = parse_resume(text)
            scores = score_resume(parsed)
            execute_query(
                """UPDATE resumes SET overall_score=%s, technical_score=%s,
                   experience_score=%s, education_score=%s, skills=%s,
                   strengths=%s, improvements=%s WHERE id=%s""",
                (scores.get("overall_score"), scores.get("technical_score"),
                 scores.get("experience_score"), scores.get("education_score"),
                 ", ".join(parsed.get("skills", [])),
                 ", ".join(scores.get("strengths", [])),
                 ", ".join(scores.get("improvements", [])),
                 resume_id)
            )
            flash(f"✅ Resume uploaded! AI Score: {scores.get('overall_score')}%", "success")
        else:
            flash("Resume uploaded! Could not extract text for AI scoring.", "warning")
    except Exception as e:
        print(f"[Resume AI Error] {e}")
        flash("Resume uploaded! AI scoring failed.", "warning")

    return redirect(url_for("interviewer.dashboard"))


@interviewer_bp.route("/delete-resume/<int:resume_id>", methods=["POST"])
@interviewer_required
def delete_resume(resume_id):
    execute_query("DELETE FROM resumes WHERE id=%s AND user_id=%s",
                  (resume_id, session["user_id"]))
    flash("Resume deleted.", "success")
    return redirect(url_for("interviewer.dashboard"))


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
    ) or []

    sess = execute_query(
        """SELECT s.id, s.started_at, s.completed_at, s.total_score,
               u.name, u.email
           FROM interview_sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.id=%s""",
        (session_id,), fetch=True
    )
    sess_info = sess[0] if sess else {}
    return render_template("interviewer/session.html",
                           answers=answers, session_id=session_id,
                           sess_info=sess_info)


@interviewer_bp.route("/profile", methods=["GET", "POST"])
@interviewer_required
def profile():
    user_id = session["user_id"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            execute_query("UPDATE users SET name=%s WHERE id=%s", (name, user_id))
            session["user_name"] = name
            flash("Profile updated!", "success")
        return redirect(url_for("interviewer.profile"))

    user = execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch=True)
    data = get_dashboard_data(user_id)
    return render_template("interviewer/profile.html",
                           user=user[0] if user else {}, **data)# app/interviewer/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from database import execute_query
from datetime import datetime
import os

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


def get_dashboard_data(user_id):
    interviews = execute_query(
        """SELECT s.id, s.started_at, s.completed_at, s.total_score,
               u.name AS candidate_name, u.email AS candidate_email,
               COUNT(a.id) AS answer_count
           FROM interview_sessions s
           JOIN users u ON u.id = s.user_id
           LEFT JOIN interview_answers a ON a.session_id = s.id
           WHERE s.user_id = %s
           GROUP BY s.id ORDER BY s.started_at DESC""",
        (user_id,), fetch=True,
    ) or []

    resumes = execute_query(
        """SELECT id, original_filename, file_path, file_size, file_type,
                  uploaded_at, overall_score, technical_score, experience_score,
                  education_score, skills, strengths, improvements
           FROM resumes WHERE user_id=%s ORDER BY uploaded_at DESC""",
        (user_id,), fetch=True
    ) or []

    for r in resumes:
        size = r["file_size"] or 0
        if size < 1024:         r["size_display"] = f"{size} B"
        elif size < 1024*1024:  r["size_display"] = f"{size/1024:.1f} KB"
        else:                   r["size_display"] = f"{size/(1024*1024):.1f} MB"

    total     = len(interviews)
    completed = sum(1 for i in interviews if i["completed_at"])
    ongoing   = total - completed
    scores    = [i["total_score"] for i in interviews if i["total_score"]]
    best_score = max(scores, default=0)
    avg_score  = round(sum(scores) / len(scores), 1) if scores else 0

    # AI Insights
    # Most difficult question (lowest avg score)
    hardest_q = execute_query(
        """SELECT question, AVG(score) as avg_score
           FROM interview_answers
           WHERE session_id IN (
               SELECT id FROM interview_sessions WHERE user_id=%s
           ) AND score IS NOT NULL AND question IS NOT NULL
           GROUP BY question ORDER BY avg_score ASC LIMIT 1""",
        (user_id,), fetch=True
    )
    hardest_question = hardest_q[0]["question"][:40] if hardest_q else "No data yet"

    # Most common weak skill (from resume improvements)
    weak_skills_raw = execute_query(
        "SELECT improvements FROM resumes WHERE user_id=%s AND improvements IS NOT NULL AND improvements != ''",
        (user_id,), fetch=True
    ) or []
    skill_freq = {}
    for row in weak_skills_raw:
        for sk in (row["improvements"] or "").split(","):
            sk = sk.strip()
            if sk:
                skill_freq[sk] = skill_freq.get(sk, 0) + 1
    weak_skill = max(skill_freq, key=skill_freq.get) if skill_freq else "No data yet"
    weak_skill = weak_skill[:28] if len(weak_skill) > 28 else weak_skill

    return dict(interviews=interviews, resumes=resumes, total=total,
                completed=completed, ongoing=ongoing,
                best_score=best_score, avg_score=avg_score,
                hardest_question=hardest_question, weak_skill=weak_skill)


@interviewer_bp.route("/dashboard")
@interviewer_required
def dashboard():
    data = get_dashboard_data(session["user_id"])
    return render_template("interviewer/dashboard.html", **data)


@interviewer_bp.route("/upload")
@interviewer_required
def upload_page():
    return render_template("interviewer/upload.html")


@interviewer_bp.route("/upload-resume", methods=["POST"])
@interviewer_required
def upload_resume():
    from werkzeug.utils import secure_filename
    import uuid

    file = request.files.get("resume")
    if not file or file.filename == "":
        flash("Please select a file.", "danger")
        return redirect(url_for("interviewer.upload_page"))

    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files allowed.", "danger")
        return redirect(url_for("interviewer.upload_page"))

    filename    = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    folder      = os.path.join("app", "static", "uploads")
    os.makedirs(folder, exist_ok=True)
    save_path   = os.path.join(folder, unique_name)
    file.save(save_path)

    file_size = os.path.getsize(save_path)
    file_path = f"uploads/{unique_name}"

    execute_query(
        """INSERT INTO resumes (user_id, original_filename, stored_filename,
           file_path, file_size, file_type, uploaded_at)
           VALUES (%s,%s,%s,%s,%s,'pdf',%s)""",
        (session["user_id"], filename, unique_name, file_path, file_size, datetime.now())
    )

    row = execute_query(
        "SELECT id FROM resumes WHERE user_id=%s ORDER BY uploaded_at DESC LIMIT 1",
        (session["user_id"],), fetch=True
    )
    resume_id = row[0]["id"] if row else None

    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(save_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        if text.strip() and resume_id:
            from app.ai_services.resume_analyzer import parse_resume, score_resume
            parsed = parse_resume(text)
            scores = score_resume(parsed)
            execute_query(
                """UPDATE resumes SET overall_score=%s, technical_score=%s,
                   experience_score=%s, education_score=%s, skills=%s,
                   strengths=%s, improvements=%s WHERE id=%s""",
                (scores.get("overall_score"), scores.get("technical_score"),
                 scores.get("experience_score"), scores.get("education_score"),
                 ", ".join(parsed.get("skills", [])),
                 ", ".join(scores.get("strengths", [])),
                 ", ".join(scores.get("improvements", [])),
                 resume_id)
            )
            flash(f"✅ Resume uploaded! AI Score: {scores.get('overall_score')}%", "success")
        else:
            flash("Resume uploaded! Could not extract text for AI scoring.", "warning")
    except Exception as e:
        print(f"[Resume AI Error] {e}")
        flash("Resume uploaded! AI scoring failed.", "warning")

    return redirect(url_for("interviewer.dashboard"))


@interviewer_bp.route("/delete-resume/<int:resume_id>", methods=["POST"])
@interviewer_required
def delete_resume(resume_id):
    execute_query("DELETE FROM resumes WHERE id=%s AND user_id=%s",
                  (resume_id, session["user_id"]))
    flash("Resume deleted.", "success")
    return redirect(url_for("interviewer.dashboard"))


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
    ) or []

    sess = execute_query(
        """SELECT s.id, s.started_at, s.completed_at, s.total_score,
               u.name, u.email
           FROM interview_sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.id=%s""",
        (session_id,), fetch=True
    )
    sess_info = sess[0] if sess else {}
    return render_template("interviewer/session.html",
                           answers=answers, session_id=session_id,
                           sess_info=sess_info)


@interviewer_bp.route("/profile", methods=["GET", "POST"])
@interviewer_required
def profile():
    user_id = session["user_id"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            execute_query("UPDATE users SET name=%s WHERE id=%s", (name, user_id))
            session["user_name"] = name
            flash("Profile updated!", "success")
        return redirect(url_for("interviewer.profile"))

    user = execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch=True)
    data = get_dashboard_data(user_id)
    return render_template("interviewer/profile.html",
                           user=user[0] if user else {}, **data)