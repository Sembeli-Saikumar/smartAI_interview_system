"""
app/models/resume.py
Handles all database operations for resumes.
"""

from database import execute_query
from datetime import datetime


def save_resume(user_id: int, original_filename: str, stored_filename: str,
                file_path: str, file_size: int, file_type: str) -> int:
    """Save resume metadata to the database."""
    return execute_query(
        """
        INSERT INTO resumes
            (user_id, original_filename, stored_filename,
             file_path, file_size, file_type, uploaded_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_id,
            original_filename,
            stored_filename,
            file_path,
            file_size,
            file_type,
            datetime.utcnow(),
        ),
    )


def get_user_resumes(user_id: int) -> list:
    """Fetch all resumes uploaded by a specific user."""
    return execute_query(
        """
        SELECT id, original_filename, stored_filename,
               file_path, file_size, file_type, uploaded_at,
               overall_score, technical_score, experience_score,
               education_score, skills, strengths, improvements
        FROM resumes
        WHERE user_id = %s
        ORDER BY uploaded_at DESC
        """,
        (user_id,),
        fetch=True,
    )


def get_resume_by_id(resume_id: int, user_id: int):
    """Fetch a single resume by ID — only if it belongs to the given user."""
    results = execute_query(
        """
        SELECT id, original_filename, stored_filename,
               file_path, file_size, file_type, uploaded_at
        FROM resumes
        WHERE id = %s AND user_id = %s
        """,
        (resume_id, user_id),
        fetch=True,
    )
    return results[0] if results else None


def delete_resume(resume_id: int, user_id: int) -> bool:
    """Delete a resume record from DB (ownership verified)."""
    execute_query(
        "DELETE FROM resumes WHERE id = %s AND user_id = %s",
        (resume_id, user_id),
    )
    return True
