import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from .config import get_settings

PBKDF2_ITERATIONS = 390_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters)).hex()
        return hmac.compare_digest(check, digest)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "typ": "access", "iat": now,
               "exp": now + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == "access" else None


def sign_action(user_id: int, tool: str, args: dict, ttl_minutes: int = 10) -> str:
    """An AI-proposed action, signed so the browser can hand it back for confirmation unchanged."""
    now = datetime.now(timezone.utc)
    payload = {"typ": "action", "uid": user_id, "tool": tool, "args": args, "iat": now,
               "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")


def verify_action(token: str) -> dict | None:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == "action" else None


def new_tracking_token() -> str:
    return secrets.token_urlsafe(18)
