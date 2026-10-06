"""Sellers ask for refunds; the owner approves or rejects them."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_owner, require_staff
from ..models import Order, Refund, User
from ..schemas import DecisionIn, RefundIn
from ..services.orders import decide_refund, refundable, request_refund, user_names
from ..timeutil import iso_utc

router = APIRouter(prefix="/api/refunds", tags=["refunds"])


def refund_out(r: Refund, names: dict[int, str]) -> dict:
    return {
        "id": r.id, "order_id": r.order_id, "order_number": r.order.daily_number,
        "order_date": r.order.business_date, "order_total": r.order.total_amount,
        "amount": r.amount, "method": r.method, "reason": r.reason, "status": r.status,
        "decision_note": r.decision_note, "requested_by": names.get(r.requested_by),
        "decided_by": names.get(r.decided_by), "created_at": iso_utc(r.created_at), "decided_at": iso_utc(r.decided_at),
    }


@router.post("", status_code=201)
def create_refund(body: RefundIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(404, "Order not found.")
    refund = request_refund(db, order, body.amount, body.method, body.reason, user)
    return refund_out(refund, user_names(db))


@router.get("")
def list_refunds(status: str | None = None, limit: int = Query(default=100, le=500),
                 db: Session = Depends(get_db), user: User = Depends(require_staff)):
    q = select(Refund)
    if status:
        q = q.where(Refund.status == status)
    names = user_names(db)
    return [refund_out(r, names) for r in db.scalars(q.order_by(Refund.created_at.desc()).limit(limit))]


@router.get("/refundable/{order_id}")
def how_much(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found.")
    return {"order_id": order.id, "refundable": refundable(db, order)}


def _pending(db: Session, refund_id: int) -> Refund:
    r = db.get(Refund, refund_id)
    if not r:
        raise HTTPException(404, "Refund not found.")
    return r


@router.post("/{refund_id}/approve")
def approve(refund_id: int, body: DecisionIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return refund_out(decide_refund(db, _pending(db, refund_id), True, body.note, user), user_names(db))


@router.post("/{refund_id}/reject")
def reject(refund_id: int, body: DecisionIn, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return refund_out(decide_refund(db, _pending(db, refund_id), False, body.note, user), user_names(db))
