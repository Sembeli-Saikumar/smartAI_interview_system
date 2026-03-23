# app/ai_services/answer_evaluator.py
import os
import json
from groq import Groq
from dotenv import load_dotenv
from app.ai_services.prompt_templates import ANSWER_SCORE_PROMPT

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

def evaluate_answer(question: str, answer: str) -> dict:
    if not answer or len(answer.strip()) < 5:
        return {"score": 0, "feedback": "No answer was provided."}
    try:
        prompt = ANSWER_SCORE_PROMPT.format(question=question, answer=answer)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        return json.loads(_clean_json(response.choices[0].message.content))
    except Exception as e:
        print(f"[answer_evaluator error] {e}")
        return {"score": 0, "feedback": "Could not generate feedback."}