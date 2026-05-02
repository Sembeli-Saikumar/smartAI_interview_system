# app/ai_services/question_generator.py
"""
AI-powered question generator that creates personalized interview questions
based on skills extracted from a candidate's resume.
"""
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Comprehensive skill list for detection ──────────────────────────
KNOWN_SKILLS = [
    # Frontend
    "HTML", "CSS", "JavaScript", "TypeScript", "React", "Angular", "Vue.js",
    "Next.js", "Svelte", "jQuery", "Bootstrap", "Tailwind CSS", "SASS", "LESS",
    "Webpack", "Vite", "Redux", "GraphQL",
    # Backend
    "Python", "Java", "C++", "C#", "Go", "Rust", "Ruby", "PHP", "Perl",
    "Node.js", "Express.js", "Django", "Flask", "Spring Boot", "FastAPI",
    "ASP.NET", "Laravel", "Rails",
    # Data / ML
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
    "Pandas", "NumPy", "TensorFlow", "PyTorch", "Scikit-learn", "Keras",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Data Science", "Data Analysis", "Power BI", "Tableau",
    # DevOps / Cloud
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "CI/CD", "Jenkins",
    "Terraform", "Ansible", "Linux", "Nginx", "Apache",
    "Git", "GitHub", "GitLab",
    # Mobile
    "Android", "iOS", "Flutter", "React Native", "Swift", "Kotlin",
    # Other
    "REST API", "Microservices", "Agile", "Scrum", "JIRA",
    "Figma", "Adobe XD", "UI/UX",
    "Blockchain", "Solidity", "Web3",
    "Selenium", "Cypress", "Jest", "PyTest",
    "R", "MATLAB", "Excel", "VBA",
]


def _clean_json(text: str) -> str:
    """Strip markdown fences from LLM JSON output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"[PDF Extract Error] {e}")
        return ""


def extract_skills(resume_text: str) -> list:
    """
    Extract skills from resume text using pattern matching.
    Returns a deduplicated, sorted list of detected skill names.
    """
    if not resume_text:
        return []

    text_upper = resume_text.upper()
    found = []

    for skill in KNOWN_SKILLS:
        # Use word-boundary-aware search
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, resume_text, re.IGNORECASE):
            found.append(skill)

    return sorted(set(found))


QUESTION_GEN_PROMPT = """You are a senior technical interviewer. Generate personalized interview questions based on the candidate's skills.

Candidate Skills: {skills}

For EACH skill listed, generate exactly 3 questions at different difficulty levels:
- 1 Basic (fundamentals, definitions, simple use-cases)
- 1 Intermediate (practical application, problem-solving)
- 1 Advanced (architecture, optimization, edge cases, system design)

IMPORTANT RULES:
- Questions MUST be specific to each skill, NOT generic
- Do NOT ask "tell me about yourself" or generic HR questions
- Make questions practical and scenario-based where possible
- Each question should test real knowledge

Return ONLY valid JSON in this exact format:
{{
  "skill_questions": {{
    "SkillName": {{
      "basic": "Basic level question here?",
      "intermediate": "Intermediate level question here?",
      "advanced": "Advanced level question here?"
    }}
  }}
}}

Generate questions ONLY for these skills: {skills}
Return ONLY the JSON, no other text.
"""


def generate_questions_for_skills(skills: list) -> dict:
    """
    Use Groq LLM to generate 3 questions per skill (basic/intermediate/advanced).
    Returns dict: { "skill_name": { "basic": "...", "intermediate": "...", "advanced": "..." } }
    """
    if not skills:
        return {}

    # Limit to 8 skills max for reasonable API usage
    skills_subset = skills[:8]
    skills_str = ", ".join(skills_subset)

    try:
        prompt = QUESTION_GEN_PROMPT.format(skills=skills_str)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=0.4,
        )
        raw = response.choices[0].message.content
        data = json.loads(_clean_json(raw))
        return data.get("skill_questions", data)
    except Exception as e:
        print(f"[Question Generator Error] {e}")
        # Fallback: generate template-based questions
        return _fallback_questions(skills_subset)


def _fallback_questions(skills: list) -> dict:
    """Generate simple template-based questions if LLM fails."""
    result = {}
    for skill in skills:
        result[skill] = {
            "basic": f"What is {skill} and what are its core features?",
            "intermediate": f"Describe a project where you used {skill} to solve a real problem.",
            "advanced": f"How would you optimize a large-scale application built with {skill}?",
        }
    return result
