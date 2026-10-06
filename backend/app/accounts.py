"""Sellers and owners never share a sign-in: each needs their own email and a different password.

The owner's account opens the admin site, which can do everything; seller accounts only open
the seller site. Keeping the passwords apart means a seller can never guess their way in as owner.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User
from .security import verify_password


def email_problem(db: Session, email: str) -> str | None:
    u = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not u:
        return None
    if u.role == "owner":
        return "That email is the owner's sign-in. Every seller needs their own email."
    return f"That email already belongs to {u.name}'s seller account. Each person needs their own email."


def password_problem(db: Session, password: str, role: str, exclude_id: int | None = None) -> str | None:
    other = "owner" if role == "seller" else "seller"
    for u in db.scalars(select(User).where(User.role == other)):
        if u.id != exclude_id and verify_password(password, u.password_hash):
            if role == "seller":
                return "A seller can't use the owner's password. Choose a different one."
            return "The owner's password can't be the same as a seller's. Choose a different one."
    return None
