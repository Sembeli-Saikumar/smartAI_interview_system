# app/interview/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request
from database import execute_query
from datetime import datetime
import random
import json

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")

# ── Fallback Question Bank ────────────────────────────────────
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
    all_q = []
    all_q.append(random.choice(QUESTION_BANK["behavioral"]))
    all_q.append(random.choice(QUESTION_BANK["technical"]))
    all_q.append(random.choice(QUESTION_BANK["hr"]))
    remaining = []
    for v in QUESTION_BANK.values():
        remaining.extend(v)
    random.shuffle(remaining)
    for q in remaining:
        if q not in all_q:
            all_q.append(q)
        if len(all_q) >= n:
            break
    random.shuffle(all_q)
    return all_q[:n]


def get_ai_questions_from_resume(user_id: int) -> list:
    """Fetch latest resume skills and generate AI questions."""
    try:
        # Get latest resume with skills
        resume = execute_query(
            """SELECT skills, experience_score, education_score,
                      overall_score, improvements
               FROM resumes
               WHERE user_id=%s AND skills IS NOT NULL AND skills != ''
               ORDER BY uploaded_at DESC LIMIT 1""",
            (user_id,), fetch=True
        )

        if not resume:
            print("[AI Questions] No resume found — using fallback")
            return get_fallback_questions()

        r = resume[0]
        skills        = r.get("skills", "")
        experience    = "1-2" if r.get("experience_score", 0) < 50 else "3-5"
        education     = "Bachelor's degree"
        job_titles    = "Software Developer"

        from app.ai_services.prompt_templates import QUESTION_GENERATE_PROMPT
        from groq import Groq
        import os
        from dotenv import load_dotenv
        load_dotenv()

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = QUESTION_GENERATE_PROMPT.format(
            skills           = skills,
            experience_years = experience,
            education        = education,
            job_titles       = job_titles,
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.7,
        )

        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)
        questions = data.get("questions", [])

        if len(questions) >= 5:
            print(f"[AI Questions] Generated {len(questions)} resume-based questions!")
            return questions[:5]
        else:
            return get_fallback_questions()

    except Exception as e:
        print(f"[AI Questions error] {e}")
        return get_fallback_questions()


@interview_bp.route("/start")
def start_interview():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    session.pop("interview_session_id", None)
    session.pop("question_index", None)
    session.pop("questions", None)
    return render_template("interview/start.html")


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
            score    = ai_result.get("score", 0)
            feedback = ai_result.get("feedback", "")
        except Exception:
            score, feedback = 0, ""

        execute_query(
            "INSERT INTO interview_answers (session_id, question, answer, score, feedback) VALUES (%s,%s,%s,%s,%s)",
            (session_id, current_q, answer, score, feedback),
        )

        q_index += 1
        session["question_index"] = q_index

        if q_index >= len(questions):
            avg = execute_query(
                "SELECT AVG(score) as avg FROM interview_answers WHERE session_id=%s",
                (session_id,), fetch=True
            )
            total_score = round(avg[0]["avg"], 1) if avg and avg[0]["avg"] else 0
            execute_query(
                "UPDATE interview_sessions SET total_score=%s WHERE id=%s",
                (total_score, session_id),
            )
            return redirect(url_for("interview.result"))

        return redirect(url_for("interview.question"))

    # GET
    q_index   = session.get("question_index", 0)
    questions = session.get("questions", [])

    if "interview_session_id" not in session:
        # ── Generate AI questions from resume ────────────────
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
        session["question_index"]       = 0
        q_index = 0

    if q_index >= len(questions):
        return redirect(url_for("interview.result"))

    return render_template(
        "interview/question.html",
        question        = questions[q_index],
        question_number = q_index + 1,
        total_questions = len(questions),
    )


@interview_bp.route("/result")
def result():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    session_id = session.get("interview_session_id")
    if not session_id:
        return redirect(url_for("interview.start_interview"))

    execute_query(
        "UPDATE interview_sessions SET completed_at=%s WHERE id=%s",
        (datetime.now(), session_id),
    )

    answers = execute_query(
        "SELECT question, answer, score, feedback FROM interview_answers WHERE session_id=%s ORDER BY id",
        (session_id,), fetch=True,
    )

    score_row = execute_query(
        "SELECT total_score FROM interview_sessions WHERE id=%s",
        (session_id,), fetch=True
    )
    total_score = score_row[0]["total_score"] if score_row and score_row[0]["total_score"] else 0

    session.pop("interview_session_id", None)
    session.pop("question_index", None)
    session.pop("questions", None)

    return render_template(
        "interview/result.html",
        session_id  = session_id,
        answers     = answers or [],
        total_score = total_score,
    )