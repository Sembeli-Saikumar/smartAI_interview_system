"""
app/resume/routes.py
Handles resume upload, listing, and deletion.
"""

import os
import uuid
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session, current_app
)
from werkzeug.utils import secure_filename

from app.models.resume import (
    save_resume,
    get_user_resumes,
    get_resume_by_id,
    delete_resume,
)
from database import execute_query

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")

ALLOWED_EXTENSIONS  = {"pdf", "docx"}
MAX_FILE_SIZE_MB    = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_folder() -> str:
    folder = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(folder, exist_ok=True)
    return folder


def extract_text(file_path: str, ext: str) -> str:
    """Extract text from PDF or DOCX."""
    try:
        if ext == "pdf":
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif ext == "docx":
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"[extract_text error] {e}")
    return ""


@resume_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if "resume" not in request.files:
            flash("No file selected.", "danger")
            return redirect(url_for("resume.upload"))

        file = request.files["resume"]

        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("resume.upload"))

        if not allowed_file(file.filename):
            flash("Only PDF and DOCX files are allowed.", "danger")
            return redirect(url_for("resume.upload"))

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE_BYTES:
            flash(f"File too large. Max {MAX_FILE_SIZE_MB} MB.", "danger")
            return redirect(url_for("resume.upload"))

        original_filename = file.filename
        ext               = original_filename.rsplit(".", 1)[1].lower()
        secure_name       = secure_filename(original_filename)
        stored_filename   = f"{uuid.uuid4().hex}_{secure_name}"

        upload_folder = get_upload_folder()
        file_path_abs = os.path.join(upload_folder, stored_filename)
        file.save(file_path_abs)

        file_path_rel = f"uploads/{stored_filename}"

        try:
            save_resume(
                user_id           = session["user_id"],
                original_filename = original_filename,
                stored_filename   = stored_filename,
                file_path         = file_path_rel,
                file_size         = file_size,
                file_type         = ext,
            )

            # ── AI Scoring ────────────────────────────────────
            try:
                from app.ai_services.resume_analyzer import parse_resume, score_resume

                text   = extract_text(file_path_abs, ext)
                parsed = parse_resume(text)
                scores = score_resume(parsed)

                skills_str    = ", ".join(parsed.get("skills", []))
                strengths_str = ", ".join(scores.get("strengths", []))
                improve_str   = ", ".join(scores.get("improvements", []))

                # Get resume id just saved
                row = execute_query(
                    "SELECT id FROM resumes WHERE user_id=%s ORDER BY uploaded_at DESC LIMIT 1",
                    (session["user_id"],), fetch=True
                )
                if row:
                    execute_query(
                        """UPDATE resumes SET
                            overall_score=%s, technical_score=%s,
                            experience_score=%s, education_score=%s,
                            skills=%s, strengths=%s, improvements=%s
                           WHERE id=%s""",
                        (
                            scores.get("overall_score", 0),
                            scores.get("technical_score", 0),
                            scores.get("experience_score", 0),
                            scores.get("education_score", 0),
                            skills_str,
                            strengths_str,
                            improve_str,
                            row[0]["id"],
                        )
                    )
                flash("Resume uploaded and AI scored successfully! ✅", "success")
            except Exception as ai_err:
                print(f"[AI scoring error] {ai_err}")
                flash("Resume uploaded! AI scoring failed — try again later.", "warning")

        except Exception as e:
            if os.path.exists(file_path_abs):
                os.remove(file_path_abs)
            flash(f"Upload failed: {str(e)}", "danger")

        return redirect(url_for("resume.list_resumes"))

    return render_template("resume/upload.html")


@resume_bp.route("/list")
@login_required
def list_resumes():
    resumes = get_user_resumes(session["user_id"])
    for r in resumes:
        size = r["file_size"]
        if size < 1024:
            r["size_display"] = f"{size} B"
        elif size < 1024 * 1024:
            r["size_display"] = f"{size / 1024:.1f} KB"
        else:
            r["size_display"] = f"{size / (1024 * 1024):.1f} MB"
    return render_template("resume/list.html", resumes=resumes)


@resume_bp.route("/delete/<int:resume_id>", methods=["POST"])
@login_required
def delete(resume_id: int):
    resume = get_resume_by_id(resume_id, session["user_id"])
    if not resume:
        flash("Resume not found or permission denied.", "danger")
        return redirect(url_for("resume.list_resumes"))

    upload_folder = get_upload_folder()
    file_path_abs = os.path.join(upload_folder, resume["stored_filename"])
    if os.path.exists(file_path_abs):
        os.remove(file_path_abs)

    if delete_resume(resume_id, session["user_id"]):
        flash("Resume deleted successfully.", "success")
    else:
        flash("Could not delete resume.", "danger")

    return redirect(url_for("resume.list_resumes"))