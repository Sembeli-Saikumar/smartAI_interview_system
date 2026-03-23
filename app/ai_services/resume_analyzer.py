# app/ai_services/resume_analyzer.py
import os
import json
from groq import Groq
from dotenv import load_dotenv
from app.ai_services.prompt_templates import RESUME_PARSE_PROMPT, RESUME_SCORE_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

def parse_resume(text: str) -> dict:
    try:
        prompt = RESUME_PARSE_PROMPT.format(text=text[:3000])
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2,
        )
        return json.loads(_clean_json(response.choices[0].message.content))
    except Exception as e:
        print(f"[resume_analyzer.parse_resume error] {e}")
        return {"name":"","skills":[],"experience_years":0,"education":"","job_titles":[],"summary":""}

def score_resume(parsed: dict) -> dict:
    try:
        prompt = RESUME_SCORE_PROMPT.format(
            skills           = ", ".join(parsed.get("skills", [])),
            experience_years = parsed.get("experience_years", 0),
            education        = parsed.get("education", "Not specified"),
            job_titles       = ", ".join(parsed.get("job_titles", [])),
            summary          = parsed.get("summary", ""),
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2,
        )
        return json.loads(_clean_json(response.choices[0].message.content))
    except Exception as e:
        print(f"[resume_analyzer.score_resume error] {e}")
        return {"technical_score":0,"experience_score":0,"education_score":0,"overall_score":0,"strengths":[],"improvements":[]}