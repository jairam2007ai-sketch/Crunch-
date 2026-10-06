"""First-run setup from the browser: create the owner account when the database has no users.

Only works on the computer running the server (and never in production, where the owner
comes from OWNER_EMAIL / OWNER_PASSWORD), so nobody else can claim a fresh install.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import audit
from ..models import User
from ..schemas import UserCreateIn, UserOut
from ..security import hash_password

router = APIRouter(prefix="/api/setup", tags=["setup"])
LOCAL = ("127.0.0.1", "::1", "localhost")
# Anything that arrived through a tunnel, proxy or CDN carries one of these; a browser on this computer never does.
PROXY_HEADERS = ("x-forwarded-for", "x-real-ip", "forwarded", "cf-connecting-ip", "true-client-ip", "x-forwarded-host")


def _allowed_here(request: Request) -> bool:
    host = request.client.host if request.client else ""
    if any(h in request.headers for h in PROXY_HEADERS):
        return False
    return not get_settings().is_production and host in LOCAL


def _has_users(db: Session) -> bool:
    return db.scalar(select(User.id).limit(1)) is not None


@router.get("/status")
def setup_status(request: Request, db: Session = Depends(get_db)):
    needs = not _has_users(db)
    return {"needs_owner": needs, "can_setup_here": needs and _allowed_here(request)}


@router.post("/owner", response_model=UserOut, status_code=201)
def create_first_owner(body: UserCreateIn, request: Request, db: Session = Depends(get_db)):
    if _has_users(db):
        raise HTTPException(409, "An account already exists. Sign in instead.")
    if not _allowed_here(request):
        raise HTTPException(403, "First-time setup only works on the computer running the server. "
                                 "On a hosted server, set OWNER_EMAIL and OWNER_PASSWORD instead.")
    owner = User(name=body.name.strip(), email=body.email, password_hash=hash_password(body.password), role="owner")
    db.add(owner)
    db.flush()
    audit(db, owner, "user.create", "user", owner.id, new={"name": owner.name, "email": owner.email, "role": "owner", "via": "first-run setup"})
    db.commit()
    return owner
