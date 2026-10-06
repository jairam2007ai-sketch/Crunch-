from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import audit, client_ip, get_current_user
from ..models import User
from ..ratelimit import login_account_limiter, login_ip_limiter, login_limiter
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, needs_rehash, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
_DUMMY_HASH = hash_password("timing-equaliser")
TOO_MANY = "Too many sign-in attempts. Wait a few minutes and try again."


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    ip = client_ip(request)
    # three layers: one person guessing, one network trying many accounts, many networks on one account
    if not (login_limiter.hit(f"{ip}:{email}") and login_ip_limiter.hit(ip) and login_account_limiter.hit(email)):
        raise HTTPException(429, TOO_MANY)
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        verify_password(body.password, _DUMMY_HASH)  # same timing whether or not the email exists
        raise HTTPException(401, "That email or password is wrong.")
    if not verify_password(body.password, user.password_hash):
        audit(db, user, "auth.failed", "user", user.id, new={"ip": ip})
        db.commit()
        raise HTTPException(401, "That email or password is wrong.")
    if not user.is_active:
        raise HTTPException(403, "This account has been turned off. Ask the owner to turn it back on.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    audit(db, user, "auth.login", "user", user.id, new={"ip": ip})
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role, user.token_version or 0),
                    user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout-everywhere", status_code=204)
def logout_everywhere(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Ends every session of this account, on every device."""
    user.token_version = (user.token_version or 0) + 1
    audit(db, user, "auth.logout_all", "user", user.id)
    db.commit()
