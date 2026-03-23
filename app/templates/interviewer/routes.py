@interviewer_bp.route("/profile", methods=["GET", "POST"])
@interviewer_required
def profile():
    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        # Profile image upload
        profile_img = request.files.get("profile_image")
        if profile_img and profile_img.filename != "":
            from werkzeug.utils import secure_filename
            import uuid
            allowed = {"png", "jpg", "jpeg", "gif", "webp"}
            ext = profile_img.filename.rsplit(".", 1)[-1].lower()
            if ext in allowed:
                img_folder = os.path.join("app", "static", "profile_pics")
                os.makedirs(img_folder, exist_ok=True)
                img_name = f"{uuid.uuid4().hex}.{ext}"
                img_path = os.path.join(img_folder, img_name)
                profile_img.save(img_path)
                db_img_path = f"profile_pics/{img_name}"
                execute_query(
                    "UPDATE users SET profile_image=%s WHERE id=%s",
                    (db_img_path, user_id)
                )
                session["profile_image"] = db_img_path
            else:
                flash("Only PNG, JPG, GIF, WEBP allowed.", "danger")
                return redirect(url_for("interviewer.profile"))

        if name:
            execute_query("UPDATE users SET name=%s WHERE id=%s", (name, user_id))
            session["user_name"] = name

        flash("Profile updated successfully!", "success")
        return redirect(url_for("interviewer.profile"))

    user = execute_query("SELECT * FROM users WHERE id=%s", (user_id,), fetch=True)
    interviews = execute_query(
        """SELECT s.id, s.completed_at, s.total_score FROM interview_sessions s
           WHERE s.user_id=%s""", (user_id,), fetch=True) or []
    total      = len(interviews)
    completed  = sum(1 for i in interviews if i["completed_at"])
    best_score = max((i["total_score"] for i in interviews if i["total_score"]), default=0)

    return render_template("interviewer/profile.html",
                           user=user[0] if user else {},
                           total=total,
                           completed=completed,
                           best_score=best_score)