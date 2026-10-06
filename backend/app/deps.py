from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import AuditLog, User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)

LOCAL_HOSTS = ("127.0.0.1", "::1", "localhost")
# Anything that came through a tunnel, proxy or CDN carries one of these; a browser on this computer never does.
PROXY_HEADERS = ("x-forwarded-for", "x-real-ip", "forwarded", "cf-connecting-ip", "true-client-ip", "x-forwarded-host")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    data = decode_access_token(creds.credentials)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.")
    try:
        user = db.get(User, int(data["sub"]))
    except (TypeError, ValueError):
        user = None
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account is no longer active.")
    if data.get("ver", 0) != (user.token_version or 0):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your password was changed, so please sign in again.")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("owner", "seller"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff only.")
    return user


def require_owner(user: User = Depends(get_current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can do this.")
    return user


def client_ip(request: Request) -> str:
    # The server (uvicorn) has already taken the real address from trusted proxies only,
    # so a visitor can't fake it by sending their own X-Forwarded-For header.
    return request.client.host if request.client else "unknown"


def is_local_request(request: Request) -> bool:
    """True only for a browser on the computer running the server, never via a tunnel or proxy."""
    host = request.client.host if request.client else ""
    return host in LOCAL_HOSTS and not any(h in request.headers for h in PROXY_HEADERS)


def audit(db: Session, user: User | None, action: str, entity_type: str, entity_id="", old=None, new=None) -> None:
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity_type=entity_type,
                    entity_id=str(entity_id), old_value=old, new_value=new))
