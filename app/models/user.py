# app/models/user.py
# All database operations for the users table.
# Import these functions in auth/routes.py instead of writing raw SQL there.

from database import execute_query


def create_user(name: str, email: str, hashed_password: str, role: str = "candidate") -> int:
    """
    Insert a new user into the users table.
    Returns the auto-generated ID of the newly created user.
    """
    new_id = execute_query(
        "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
        params=(name, email, hashed_password, role),
        fetch=False
    )
    return new_id


def get_user_by_email(email: str):
    """
    Fetch a user row by email address.
    Returns a dict with user data, or None if no user found.
    """
    results = execute_query(
        "SELECT id, name, email, password, role FROM users WHERE email = %s",
        params=(email,),
        fetch=True
    )
    return results[0] if results else None


def email_exists(email: str) -> bool:
    """
    Check if an email address is already registered.
    Returns True if email exists, False otherwise.
    Used during registration to prevent duplicate accounts.
    """
    results = execute_query(
        "SELECT id FROM users WHERE email = %s",
        params=(email,),
        fetch=True
    )
    return len(results) > 0