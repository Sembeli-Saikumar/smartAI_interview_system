# app/models/admin.py
# All database queries for admin dashboard

from database import execute_query


def get_total_stats() -> dict:
    """Total users, resumes, interviews count."""
    users      = execute_query("SELECT COUNT(*) as count FROM users",      fetch=True)
    resumes    = execute_query("SELECT COUNT(*) as count FROM resumes",    fetch=True)
    interviews = execute_query("SELECT COUNT(*) as count FROM interview_sessions", fetch=True)
    completed  = execute_query(
        "SELECT COUNT(*) as count FROM interview_sessions WHERE completed_at IS NOT NULL",
        fetch=True
    )
    return {
        "total_users"      : users[0]["count"]      if users      else 0,
        "total_resumes"    : resumes[0]["count"]    if resumes    else 0,
        "total_interviews" : interviews[0]["count"] if interviews else 0,
        "completed_interviews": completed[0]["count"] if completed else 0,
    }


def get_all_users() -> list:
    """Fetch all users ordered by registration date."""
    return execute_query(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.role,
            u.created_at,
            COUNT(DISTINCT r.id)  AS resume_count,
            COUNT(DISTINCT s.id)  AS interview_count
        FROM users u
        LEFT JOIN resumes             r ON r.user_id = u.id
        LEFT JOIN interview_sessions  s ON s.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """,
        fetch=True,
    )


def get_all_resumes() -> list:
    """Fetch all resumes with owner name."""
    return execute_query(
        """
        SELECT
            r.id,
            r.original_filename,
            r.file_type,
            r.file_size,
            r.uploaded_at,
            u.name  AS user_name,
            u.email AS user_email
        FROM resumes r
        JOIN users u ON u.id = r.user_id
        ORDER BY r.uploaded_at DESC
        """,
        fetch=True,
    )


def get_all_interviews() -> list:
    """Fetch all interview sessions with user name."""
    return execute_query(
        """
        SELECT
            s.id,
            s.started_at,
            s.completed_at,
            s.total_score,
            u.name  AS user_name,
            u.email AS user_email,
            COUNT(a.id) AS answer_count
        FROM interview_sessions s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN interview_answers a ON a.session_id = s.id
        GROUP BY s.id
        ORDER BY s.started_at DESC
        """,
        fetch=True,
    )


def delete_user(user_id: int) -> bool:
    """Delete a user and all related data (cascade)."""
    execute_query("DELETE FROM users WHERE id = %s", (user_id,))
    return True