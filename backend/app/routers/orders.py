"""Staff order endpoints: the seller POS, the order queue and the owner's order list."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_staff
from ..models import Order, User
from ..schemas import CounterOrderIn, PayIn, StatusIn
from ..services.orders import (ACTIVE_STATUSES, change_status, create_order, order_out, record_payment, user_names,
                               validate_items)
from ..timeutil import business_date_str, parse_date

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", status_code=201)
def create_counter_order(body: CounterOrderIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    lines, need = validate_items(db, body.items)
    order = create_order(db, lines, need, source="counter", status="preparing", payment_method=body.payment_method,
                         paid=body.paid, user=user, customer_name=body.customer_name.strip(), note=body.note,
                         reference=body.upi_reference)
    return order_out(order, {user.id: user.name})


@router.get("")
def list_orders(
    date: str | None = None,
    status: str | None = Query(default=None, description="Comma-separated statuses"),
    source: str | None = None,
    active: bool = False,
    number: int | None = None,
    limit: int = Query(default=200, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    q = select(Order)
    if active:
        q = q.where(Order.status.in_(ACTIVE_STATUSES))
    else:
        try:
            day = parse_date(date).isoformat() if date else business_date_str()
        except ValueError:
            raise HTTPException(400, "Dates look like 2026-10-06.")
        q = q.where(Order.business_date == day)
    if status:
        q = q.where(Order.status.in_([s.strip() for s in status.split(",") if s.strip()]))
    if source in ("counter", "online"):
        q = q.where(Order.source == source)
    if number is not None:
        q = q.where(Order.daily_number == number)
    orders = db.scalars(q.order_by(Order.created_at.desc()).limit(limit)).all()
    names = user_names(db)
    return [order_out(o, names) for o in orders]


def _get(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found.")
    return order


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return order_out(_get(db, order_id), user_names(db))


@router.patch("/{order_id}/status")
def set_status(order_id: int, body: StatusIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    order = change_status(db, _get(db, order_id), body.status, user, body.reason)
    return order_out(order, user_names(db))


@router.post("/{order_id}/pay")
def pay(order_id: int, body: PayIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    order = record_payment(db, _get(db, order_id), body.method, body.reference, user)
    return order_out(order, user_names(db))
