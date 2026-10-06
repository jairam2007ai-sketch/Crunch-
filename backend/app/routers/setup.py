"""First-run setup from the browser: create the owner account when the database has no users.

Only works on the computer running the server, never through a tunnel or proxy, and never
in production (there the owner comes from OWNER_EMAIL / OWNER_PASSWORD), so nobody else
can claim a fresh install.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import audit, client_ip, is_local_request
from ..models import User
from ..ratelimit import setup_limiter
from ..schemas import UserCreateIn, UserOut
from ..security import hash_password, password_weakness

router = APIRouter(prefix="/api/setup", tags=["setup"])


def _allowed_here(request: Request) -> bool:
    return not get_settings().is_production and is_local_request(request)


def _has_users(db: Session) -> bool:
    return db.scalar(select(User.id).limit(1)) is not None


@router.get("/status")
def setup_status(request: Request, db: Session = Depends(get_db)):
    needs = not _has_users(db)
    return {"needs_owner": needs, "can_setup_here": needs and _allowed_here(request)}


@router.post("/owner", response_model=UserOut, status_code=201)
def create_first_owner(body: UserCreateIn, request: Request, db: Session = Depends(get_db)):
    if not setup_limiter.hit(client_ip(request)):
        raise HTTPException(429, "Too many tries. Wait a few minutes.")
    if not _allowed_here(request):
        raise HTTPException(403, "First-time setup only works on the computer running the server. "
                                 "On a hosted server, set OWNER_EMAIL and OWNER_PASSWORD instead.")
    if _has_users(db):
        raise HTTPException(409, "An account already exists. Sign in instead.")
    if problem := password_weakness(body.password, body.email, body.name):
        raise HTTPException(400, problem)
    owner = User(name=body.name, email=body.email, password_hash=hash_password(body.password), role="owner")
    db.add(owner)
    db.flush()
    audit(db, owner, "user.create", "user", owner.id, new={"name": owner.name, "email": owner.email, "role": "owner", "via": "first-run setup"})
    db.commit()
    return owner
