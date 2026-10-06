from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import audit, client_ip, get_current_user
from ..models import User
from ..ratelimit import login_limiter
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
_DUMMY_HASH = hash_password("timing-equaliser")


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not login_limiter.hit(f"{client_ip(request)}:{email}"):
        raise HTTPException(429, "Too many sign-in attempts. Wait 5 minutes and try again.")
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(401, "That email or password is wrong.")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "That email or password is wrong.")
    if not user.is_active:
        raise HTTPException(403, "This account has been turned off. Ask the owner to turn it back on.")
    audit(db, user, "auth.login", "user", user.id)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
