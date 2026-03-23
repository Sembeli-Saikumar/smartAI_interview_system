# app/interview/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, Response, jsonify
from database import execute_query
from datetime import datetime
import random, json, io, os

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")

# ── Question Bank ──────────────────────────────────────────────
QUESTION_BANK = {
    "behavioral": [
        "Tell me about yourself and your background.",
        "Describe a challenging project you worked on and how you handled it.",
        "Tell me about a time you worked in a team. What was your role?",
        "How do you handle stress and pressure at work?",
        "Describe a time you made a mistake and how you fixed it.",
    ],
    "technical": [
        "Explain the difference between SQL and NoSQL databases.",
        "What is Object-Oriented Programming? Explain with an example.",
        "What is the difference between a stack and a queue?",
        "Explain what REST API is and how it works.",
        "What is version control and why is it important?",
    ],
    "hr": [
        "Where do you see yourself in 5 years?",
        "What are your greatest strengths?",
        "What is your biggest weakness and how are you working on it?",
        "Why should we hire you?",
        "Are you comfortable working in a team environment?",
    ],
}

def get_fallback_questions(n=5):
    all_q = [
        random.choice(QUESTION_BANK["behavioral"]),
        random.choice(QUESTION_BANK["technical"]),
        random.choice(QUESTION_BANK["hr"]),
    ]
    remaining = [q for v in QUESTION_BANK.values() for q in v if q not in all_q]
    random.shuffle(remaining)
    all_q.extend(remaining[:n - len(all_q)])
    random.shuffle(all_q)
    return all_q[:n]

def get_ai_questions_from_resume(user_id):
    try:
        resume = execute_query(
            """SELECT skills, experience_score, education_score, overall_score, improvements
               FROM resumes WHERE user_id=%s AND skills IS NOT NULL AND skills != ''
               ORDER BY uploaded_at DESC LIMIT 1""",
            (user_id,), fetch=True
        )
        if not resume:
            return get_fallback_questions()
        r = resume[0]
        from app.ai_services.prompt_templates import QUESTION_GENERATE_PROMPT
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = QUESTION_GENERATE_PROMPT.format(
            skills=r.get("skills", ""),
            experience_years="1-2" if r.get("experience_score", 0) < 50 else "3-5",
            education="Bachelor's degree",
            job_titles="Software Developer",
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800, temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        data = json.loads(text.strip())
        questions = data.get("questions", [])
        return questions[:5] if len(questions) >= 5 else get_fallback_questions()
    except Exception as e:
        print(f"[AI Questions error] {e}")
        return get_fallback_questions()


# ── Start ──────────────────────────────────────────────────────
@interview_bp.route("/start")
def start_interview():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    session.pop("interview_session_id", None)
    session.pop("question_index", None)
    session.pop("questions", None)
    return render_template("interview/start.html")


# ── Question ───────────────────────────────────────────────────
@interview_bp.route("/question", methods=["GET", "POST"])
def question():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        answer     = request.form.get("answer", "").strip()
        session_id = session.get("interview_session_id")
        q_index    = session.get("question_index", 0)
        questions  = session.get("questions", [])
        current_q  = questions[q_index] if questions else ""

        try:
            from app.ai_services.answer_evaluator import evaluate_answer
            ai_result = evaluate_answer(current_q, answer)
            score            = ai_result.get("score", 0)
            feedback         = ai_result.get("feedback", "")
            strengths        = json.dumps(ai_result.get("strengths", []))
            weaknesses       = json.dumps(ai_result.get("weaknesses", []))
            suggested_answer = ai_result.get("suggested_answer", "")
            grade            = ai_result.get("grade", "F")
        except Exception as e:
            print(f"[Eval error] {e}")
            score, feedback, strengths, weaknesses, suggested_answer, grade = 0, "", "[]", "[]", "", "F"

        execute_query(
            """INSERT INTO interview_answers
               (session_id, question, answer, score, feedback, strengths, weaknesses, suggested_answer, grade)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (session_id, current_q, answer, score, feedback,
             strengths, weaknesses, suggested_answer, grade),
        )

        q_index += 1
        session["question_index"] = q_index

        if q_index >= len(questions):
            avg = execute_query(
                "SELECT AVG(score) as avg FROM interview_answers WHERE session_id=%s",
                (session_id,), fetch=True
            )
            total_score = round(float(avg[0]["avg"]), 1) if avg and avg[0]["avg"] else 0
            execute_query(
                "UPDATE interview_sessions SET total_score=%s, completed_at=%s WHERE id=%s",
                (total_score, datetime.now(), session_id),
            )
            return redirect(url_for("interview.result"))

        return redirect(url_for("interview.question"))

    # GET
    q_index   = session.get("question_index", 0)
    questions = session.get("questions", [])

    if "interview_session_id" not in session:
        questions = get_ai_questions_from_resume(session["user_id"])
        session["questions"] = questions
        execute_query(
            "INSERT INTO interview_sessions (user_id, started_at) VALUES (%s,%s)",
            (session["user_id"], datetime.now()),
        )
        row = execute_query(
            "SELECT id FROM interview_sessions WHERE user_id=%s ORDER BY started_at DESC LIMIT 1",
            (session["user_id"],), fetch=True,
        )
        session["interview_session_id"] = row[0]["id"]
        session["question_index"] = 0
        q_index = 0

    if q_index >= len(questions):
        return redirect(url_for("interview.result"))

    return render_template(
        "interview/question.html",
        question=questions[q_index],
        question_number=q_index + 1,
        total_questions=len(questions),
    )


# ── Result ─────────────────────────────────────────────────────
@interview_bp.route("/result")
def result():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    session_id = session.get("interview_session_id")
    if not session_id:
        return redirect(url_for("interview.start_interview"))

    execute_query(
        "UPDATE interview_sessions SET completed_at=%s WHERE id=%s AND completed_at IS NULL",
        (datetime.now(), session_id),
    )

    answers = execute_query(
        """SELECT question, answer, score, feedback,
                  strengths, weaknesses, suggested_answer, grade
           FROM interview_answers WHERE session_id=%s ORDER BY id""",
        (session_id,), fetch=True,
    ) or []

    for a in answers:
        try: a["strengths_list"]  = json.loads(a.get("strengths")  or "[]")
        except: a["strengths_list"]  = []
        try: a["weaknesses_list"] = json.loads(a.get("weaknesses") or "[]")
        except: a["weaknesses_list"] = []

    score_row   = execute_query(
        "SELECT total_score FROM interview_sessions WHERE id=%s",
        (session_id,), fetch=True
    )
    total_score = float(score_row[0]["total_score"]) if score_row and score_row[0]["total_score"] else 0

    if total_score >= 85: overall_grade = "A"
    elif total_score >= 70: overall_grade = "B"
    elif total_score >= 55: overall_grade = "C"
    elif total_score >= 40: overall_grade = "D"
    else: overall_grade = "F"

    # Strength / weakness counts for chart
    total_strengths  = sum(len(a["strengths_list"])  for a in answers)
    total_weaknesses = sum(len(a["weaknesses_list"]) for a in answers)

    # Send email in background (non-blocking)
    try:
        user = execute_query("SELECT name, email FROM users WHERE id=%s",
                             (session["user_id"],), fetch=True)
        if user:
            _send_result_email_async(
                user[0]["name"], user[0]["email"],
                session_id, total_score, overall_grade, answers
            )
    except Exception as e:
        print(f"[Email background error] {e}")

    session.pop("interview_session_id", None)
    session.pop("question_index", None)
    session.pop("questions", None)

    return render_template(
        "interview/result.html",
        session_id       = session_id,
        answers          = answers,
        total_score      = total_score,
        overall_grade    = overall_grade,
        total_strengths  = total_strengths,
        total_weaknesses = total_weaknesses,
    )


# ── PDF Download (inline, no redirect) ─────────────────────────
@interview_bp.route("/result/<int:session_id>/pdf")
def download_pdf(session_id):
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    answers = execute_query(
        """SELECT question, answer, score, feedback,
                  strengths, weaknesses, suggested_answer, grade
           FROM interview_answers WHERE session_id=%s ORDER BY id""",
        (session_id,), fetch=True,
    ) or []

    sess = execute_query(
        """SELECT s.total_score, s.started_at, s.completed_at, u.name, u.email
           FROM interview_sessions s JOIN users u ON u.id=s.user_id
           WHERE s.id=%s""",
        (session_id,), fetch=True
    )
    if not sess:
        return "Session not found", 404

    s = sess[0]
    for a in answers:
        try: a["strengths_list"]  = json.loads(a.get("strengths")  or "[]")
        except: a["strengths_list"]  = []
        try: a["weaknesses_list"] = json.loads(a.get("weaknesses") or "[]")
        except: a["weaknesses_list"] = []

    try:
        from app.pdf_generator import generate_interview_pdf
        session_data = {
            "session_id": session_id,
            "name":       s["name"],
            "email":      s["email"],
            "started_at": s["started_at"],
            "total_score":float(s["total_score"] or 0),
        }
        pdf_bytes = generate_interview_pdf(session_data, answers)
    except Exception as e:
        print(f"[PDF Error] {e}")
        import traceback; traceback.print_exc()
        return f"PDF generation failed: {e}", 500

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=interview_report_{session_id}.pdf",
            "Content-Type": "application/pdf",
        }
    )


# ── Snapshot (proctoring) ──────────────────────────────────────
@interview_bp.route("/snapshot", methods=["POST"])
def snapshot():
    if "user_id" not in session:
        return jsonify({"status": "unauthorized"}), 401
    try:
        import base64
        data     = request.get_json()
        img_data = data.get("image", "").split(",")[-1]
        q_num    = data.get("question_number", 0)
        sess_id  = session.get("interview_session_id", "unknown")
        snap_dir = os.path.join("app", "static", "uploads", "snapshots", str(sess_id))
        os.makedirs(snap_dir, exist_ok=True)
        fname = f"q{q_num}_{datetime.now().strftime('%H%M%S')}.jpg"
        with open(os.path.join(snap_dir, fname), "wb") as f:
            f.write(base64.b64decode(img_data))
        return jsonify({"status": "ok", "file": fname})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


# ── Leaderboard ────────────────────────────────────────────────
@interview_bp.route("/leaderboard")
def leaderboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    data = execute_query(
        """SELECT u.name, u.email,
            COUNT(s.id) as total_interviews,
            MAX(s.total_score) as best_score,
            ROUND(AVG(s.total_score), 1) as avg_score
           FROM users u
           JOIN interview_sessions s ON s.user_id = u.id
           WHERE s.completed_at IS NOT NULL AND s.total_score IS NOT NULL
           GROUP BY u.id ORDER BY avg_score DESC LIMIT 20""",
        fetch=True
    ) or []
    return render_template("interview/leaderboard.html", leaderboard=data)


# ── HELPERS ────────────────────────────────────────────────────
def _score_to_grade(score):
    if score >= 85: return "A"
    elif score >= 70: return "B"
    elif score >= 55: return "C"
    elif score >= 40: return "D"
    else: return "F"


def _generate_pdf(s, session_id, total_score, grade, answers):
    """Generate PDF using fpdf2. Returns bytes."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            # Blue header bar
            self.set_fill_color(37, 99, 235)
            self.rect(0, 0, 210, 38, 'F')
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 18)
            self.set_xy(10, 8)
            self.cell(0, 8, "Smart Interview System", ln=True, align="C")
            self.set_font("Helvetica", "", 10)
            self.cell(0, 6, "AI-Powered Interview Performance Report", ln=True, align="C")
            self.ln(4)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(148, 163, 184)
            self.cell(0, 6,
                f"Generated by Smart Interview System  |  {datetime.now().strftime('%d %b %Y %H:%M')}  |  Session #{session_id}",
                align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.set_text_color(15, 23, 42)

    # Candidate info
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(12, 44)
    pdf.cell(0, 7, f"Candidate: {s['name']}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Email: {s['email']}", ln=True)
    pdf.cell(0, 6, f"Date: {s['started_at'].strftime('%d %B %Y, %I:%M %p') if s['started_at'] else 'N/A'}", ln=True)

    # Score box (top-right)
    sc_r, sc_g, sc_b = (16,185,129) if total_score>=70 else (245,158,11) if total_score>=40 else (239,68,68)
    pdf.set_fill_color(sc_r, sc_g, sc_b)
    pdf.set_text_color(255,255,255)
    pdf.set_xy(148, 44)
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(50, 14, f"{round(total_score)}%", fill=True, align="C", ln=True)
    pdf.set_xy(148, 58)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(50, 8, f"Grade: {grade}", fill=True, align="C")

    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(12, pdf.get_y() + 6)

    # Divider
    pdf.set_draw_color(226, 232, 240)
    y = pdf.get_y() + 2
    pdf.line(12, y, 198, y)
    pdf.ln(5)

    # Q&A breakdown
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(239, 246, 255)
    pdf.cell(0, 8, "  Question & Answer Breakdown", fill=True, ln=True)
    pdf.ln(2)

    for idx, a in enumerate(answers):
        sc   = float(a.get("score") or 0)
        g    = a.get("grade") or _score_to_grade(sc)
        sr,sg,sb = (16,185,129) if sc>=70 else (245,158,11) if sc>=40 else (239,68,68)

        # Question
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(37, 99, 235)
        q_txt = f"Q{idx+1}: {a.get('question','')}"
        pdf.multi_cell(170, 6, q_txt)

        # Score badge
        pdf.set_fill_color(sr, sg, sb)
        pdf.set_text_color(255,255,255)
        pdf.set_font("Helvetica", "B", 9)
        yy = pdf.get_y() - 6
        pdf.set_xy(178, yy)
        pdf.cell(20, 6, f"{round(sc)}/100", fill=True, align="C")

        pdf.set_xy(12, pdf.get_y())
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 9)
        ans = a.get("answer") or "No answer"
        pdf.multi_cell(186, 5, f"Answer: {ans[:280]}{'...' if len(ans)>280 else ''}")

        if a.get("feedback"):
            pdf.set_text_color(30, 64, 175)
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(186, 5, f"AI Feedback: {a['feedback'][:250]}")

        if a.get("strengths_list"):
            pdf.set_text_color(22, 163, 74)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(0, 4, f"Strengths: {', '.join(a['strengths_list'][:3])}", ln=True)

        if a.get("weaknesses_list"):
            pdf.set_text_color(220, 38, 38)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(0, 4, f"Improve: {', '.join(a['weaknesses_list'][:3])}", ln=True)

        pdf.set_draw_color(241, 245, 249)
        pdf.set_text_color(15, 23, 42)
        pdf.line(12, pdf.get_y() + 1, 198, pdf.get_y() + 1)
        pdf.ln(4)

        if pdf.get_y() > 265:
            pdf.add_page()

    return bytes(pdf.output())


def _send_result_email_async(name, email, session_id, total_score, grade, answers):
    """Send PDF report via email using SMTP."""
    import threading
    def _send():
        try:
            import smtplib, base64
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders
            from dotenv import load_dotenv
            load_dotenv()

            MAIL_EMAIL    = os.getenv("MAIL_EMAIL")
            MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

            if not MAIL_EMAIL or not MAIL_PASSWORD:
                print("[Email] MAIL_EMAIL or MAIL_PASSWORD not set")
                return

            # Fetch session info
            sess = execute_query(
                "SELECT started_at FROM interview_sessions WHERE id=%s",
                (session_id,), fetch=True
            )
            # Generate PDF using professional generator
            from app.pdf_generator import generate_interview_pdf
            s_mock = {
                "session_id":  session_id,
                "name":        name,
                "email":       email,
                "started_at":  datetime.now(),
                "total_score": total_score,
            }
            pdf_bytes = generate_interview_pdf(s_mock, answers)

            # Build email
            msg = MIMEMultipart()
            msg["From"]    = f"Smart Interview System <{MAIL_EMAIL}>"
            msg["To"]      = email
            msg["Subject"] = f"Your Interview Report — Score: {round(total_score)}% (Grade {grade})"

            score_color = "#10B981" if total_score>=70 else "#F59E0B" if total_score>=40 else "#EF4444"
            msg_text = f"""
Hi {name},

Congratulations on completing your AI-powered mock interview!

📊 Your Results:
• Total Score: {round(total_score)}%
• Grade: {grade}
• Questions Answered: {len(answers)}

Your detailed PDF report is attached to this email.
It includes per-question scores, AI feedback, strengths, and improvement suggestions.

{"🎉 Excellent performance! You're interview-ready." if total_score>=70 else "💪 Good effort! Review the feedback to improve further."}

Best of luck in your interviews!

Smart Interview System
"""
            msg.attach(MIMEText(msg_text, "plain"))

            # Attach PDF
            part = MIMEBase("application", "octet-stream")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                            f"attachment; filename=interview_report_{session_id}.pdf")
            msg.attach(part)

            # Send
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
                srv.login(MAIL_EMAIL, MAIL_PASSWORD)
                srv.sendmail(MAIL_EMAIL, email, msg.as_string())

            print(f"[Email] Report sent to {email}")
        except Exception as e:
            print(f"[Email error] {e}")

    threading.Thread(target=_send, daemon=True).start()