import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from .config import get_settings

# OWASP's current recommendation for PBKDF2-HMAC-SHA256. Older hashes are upgraded at sign-in.
PBKDF2_ITERATIONS = 600_000
JWT_ALGORITHM = "HS256"
JWT_AUDIENCE = "crunch"


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


def needs_rehash(stored: str) -> bool:
    try:
        return int(stored.split("$")[1]) < PBKDF2_ITERATIONS
    except (IndexError, ValueError):
        return True


COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890", "87654321", "11111111",
    "00000000", "qwerty123", "qwertyuiop", "iloveyou", "abcd1234", "admin123", "administrator", "welcome1",
    "welcome123", "letmein1", "passw0rd", "p@ssw0rd", "crunch123", "crunch1234", "india123", "asdfghjkl",
    "zxcvbnm1", "1q2w3e4r", "sunshine1", "princess1", "football1", "changeme", "changeme1",
}


def password_weakness(password: str, email: str = "", name: str = "") -> str | None:
    """A plain-language reason the password is too weak, or None if it's fine."""
    if len(password) < 8:
        return "Use at least 8 characters."
    low = password.lower()
    if low in COMMON_PASSWORDS or low.rstrip("0123456789!@#$.") in {"password", "qwerty", "crunch", "admin", "welcome", "seller", "owner"}:
        return "That password is too easy to guess. Try three short words together, like mango-chips-river."
    if len(set(password)) < 4:
        return "That password repeats the same few characters. Mix it up a little."
    local = email.split("@")[0].lower()
    first = (name or "").strip().split(" ")[0].lower() if name else ""
    if (len(local) >= 4 and local in low) or (len(first) >= 4 and first in low):
        return "Don't put your name or email in your password."
    return None


def create_access_token(user_id: int, role: str, version: int = 0) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "ver": version, "typ": "access", "aud": JWT_AUDIENCE,
               "iat": now, "exp": now + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALGORITHM], audience=JWT_AUDIENCE,
                          options={"require": ["exp", "iat", "sub", "aud"]})
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == "access" else None


def sign_action(user_id: int, tool: str, args: dict, ttl_minutes: int = 10) -> str:
    """An AI-proposed action, signed so the browser can hand it back for confirmation unchanged."""
    now = datetime.now(timezone.utc)
    payload = {"typ": "action", "uid": user_id, "tool": tool, "args": args, "aud": JWT_AUDIENCE, "iat": now,
               "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(payload, get_settings().jwt_secret, algorithm=JWT_ALGORITHM)


def verify_action(token: str) -> dict | None:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALGORITHM], audience=JWT_AUDIENCE)
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == "action" else None


def new_tracking_token() -> str:
    return secrets.token_urlsafe(18)
