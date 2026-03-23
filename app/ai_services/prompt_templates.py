# app/ai_services/prompt_templates.py

RESUME_PARSE_PROMPT = """
You are a resume parser. Extract information from this resume and return ONLY valid JSON.
Resume:
{text}
Return this exact JSON format:
{{
  "name": "candidate name or empty string",
  "skills": ["skill1", "skill2", "skill3"],
  "experience_years": 0,
  "education": "highest degree or empty string",
  "job_titles": ["title1", "title2"],
  "summary": "2 line professional summary"
}}
Return ONLY the JSON, no other text.
"""

RESUME_SCORE_PROMPT = """
You are an expert HR evaluator. Score this candidate's resume profile.
Profile:
- Skills: {skills}
- Experience: {experience_years} years
- Education: {education}
- Job Titles: {job_titles}
- Summary: {summary}
Return ONLY valid JSON with scores out of 100:
{{
  "technical_score": 75,
  "experience_score": 60,
  "education_score": 80,
  "overall_score": 72,
  "strengths": ["strength1", "strength2"],
  "improvements": ["area1", "area2"]
}}
Return ONLY the JSON, no other text.
"""

ANSWER_SCORE_PROMPT = """
You are an expert interviewer. Score this interview answer strictly and fairly.
Question: {question}
Answer: {answer}
Return ONLY valid JSON:
{{
  "score": 75,
  "feedback": "2-3 sentence constructive feedback mentioning what was good and what can be improved"
}}
Return ONLY the JSON, no other text.
"""

QUESTION_GENERATE_PROMPT = """
You are an expert technical interviewer. Generate exactly 5 interview questions for a candidate based on their resume profile.

Candidate Profile:
- Skills: {skills}
- Experience: {experience_years} years
- Education: {education}
- Job Titles: {job_titles}

Rules:
- 2 questions must be technical (based on their specific skills)
- 1 question must be behavioral
- 1 question must be situational/problem-solving
- 1 question must be HR/career goals
- Questions must be specific to their skills, NOT generic
- Do NOT repeat common questions like "tell me about yourself"

Return ONLY valid JSON:
{{
  "questions": [
    "Question 1 here",
    "Question 2 here",
    "Question 3 here",
    "Question 4 here",
    "Question 5 here"
  ]
}}
Return ONLY the JSON, no other text.
"""