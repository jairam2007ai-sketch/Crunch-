"""Owner tools: prices, team accounts, shop settings and the activity log."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..accounts import email_problem, password_problem
from ..db import get_db
from ..deps import audit, require_owner, require_staff
from ..models import AuditLog, Product, User
from ..schemas import ProductUpdateIn, SettingsIn, UserCreateIn, UserOut, UserUpdateIn
from ..security import hash_password, password_weakness
from ..services.orders import get_settings_row, user_names
from ..timeutil import iso_utc

router = APIRouter(prefix="/api", tags=["admin"])


def product_out(p: Product, with_cost: bool) -> dict:
    d = {"id": p.id, "code": p.code, "name": p.name, "description": p.description, "price": p.price,
         "toppings": p.toppings_allowed, "sauces": p.sauces_allowed, "seasonings": p.seasonings_allowed,
         "cheese": p.includes_cheese, "is_active": p.is_active}
    if with_cost:
        d["cost"] = p.cost
    return d


@router.get("/products")
def list_products(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return [product_out(p, user.role == "owner") for p in db.scalars(select(Product).order_by(Product.sort))]


@router.patch("/products/{product_id}")
def update_product(product_id: int, body: ProductUpdateIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found.")
    changes = body.model_dump(exclude_none=True)
    old = {k: getattr(p, k) for k in changes}
    for k, v in changes.items():
        setattr(p, k, v)
    audit(db, user, "product.update", "product", p.id, old=old, new=changes)
    db.commit()
    return product_out(p, True)


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return db.scalars(select(User).order_by(User.role, User.name)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreateIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    problem = (password_weakness(body.password, body.email, body.name) or email_problem(db, body.email)
               or password_problem(db, body.password, body.role))
    if problem:
        raise HTTPException(409, problem)
    new = User(name=body.name.strip(), email=body.email, password_hash=hash_password(body.password), role=body.role)
    db.add(new)
    db.flush()
    audit(db, user, "user.create", "user", new.id, new={"name": new.name, "email": new.email, "role": new.role})
    db.commit()
    return new


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdateIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found.")
    if body.is_active is False and target.id == user.id:
        raise HTTPException(409, "You can't turn off your own account.")
    if body.is_active is False and target.role == "owner":
        owners = db.scalar(select(func.count(User.id)).where(User.role == "owner", User.is_active.is_(True)))
        if owners <= 1:
            raise HTTPException(409, "There must always be at least one active owner.")
    new = {}
    if body.name is not None:
        target.name = body.name.strip()
        new["name"] = target.name
    if body.is_active is not None:
        if target.is_active and not body.is_active:
            target.token_version = (target.token_version or 0) + 1  # signs them out everywhere
        target.is_active = body.is_active
        new["is_active"] = body.is_active
    if body.password is not None:
        problem = (password_weakness(body.password, target.email, target.name)
                   or password_problem(db, body.password, target.role, exclude_id=target.id))
        if problem:
            raise HTTPException(409, problem)
        target.password_hash = hash_password(body.password)
        target.token_version = (target.token_version or 0) + 1  # old sessions stop working
        new["password"] = "reset"
    audit(db, user, "user.update", "user", target.id, new=new)
    db.commit()
    return target


def settings_out(s) -> dict:
    return {"shop_name": s.shop_name, "is_open": s.is_open, "upi_id": s.upi_id, "upi_name": s.upi_name,
            "pickup_note": s.pickup_note, "daily_target_min": s.daily_target_min, "daily_target_max": s.daily_target_max}


@router.get("/settings")
def get_shop_settings(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return settings_out(get_settings_row(db))


@router.patch("/settings")
def update_settings(body: SettingsIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    s = get_settings_row(db)
    changes = body.model_dump(exclude_none=True)
    lo = changes.get("daily_target_min", s.daily_target_min)
    hi = changes.get("daily_target_max", s.daily_target_max)
    if lo > hi:
        raise HTTPException(400, "The daily target's low end must be below its high end.")
    old = {k: getattr(s, k) for k in changes}
    for k, v in changes.items():
        setattr(s, k, v)
    audit(db, user, "settings.update", "settings", 1, old=old, new=changes)
    db.commit()
    return settings_out(s)


class OpenIn(BaseModel):
    is_open: bool


@router.post("/settings/open")
def set_open(body: OpenIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    """The person at the cart can open or close online ordering."""
    s = get_settings_row(db)
    if s.is_open != body.is_open:
        audit(db, user, "shop.open" if body.is_open else "shop.close", "settings", 1)
        s.is_open = body.is_open
        db.commit()
    return settings_out(s)


@router.get("/audit-logs")
def audit_logs(before_id: int | None = None, action: str | None = None, limit: int = Query(default=100, le=300),
               db: Session = Depends(get_db), user: User = Depends(require_owner)):
    q = select(AuditLog)
    if before_id:
        q = q.where(AuditLog.id < before_id)
    if action:
        q = q.where(AuditLog.action.startswith(action, autoescape=True))
    names = user_names(db)
    return [{"id": a.id, "user": names.get(a.user_id) if a.user_id else None, "action": a.action,
             "entity_type": a.entity_type, "entity_id": a.entity_id, "old": a.old_value, "new": a.new_value,
             "created_at": iso_utc(a.created_at)} for a in db.scalars(q.order_by(AuditLog.id.desc()).limit(limit))]
