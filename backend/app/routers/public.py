"""Buyer-facing endpoints. No sign-in: customers order with a name and phone number."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import client_ip
from ..models import Ingredient, Order, Product
from ..ratelimit import RateLimiter
from ..schemas import OnlineOrderIn
from ..services.orders import (ACTIVE_STATUSES, change_status, create_order, get_settings_row, ingredient_ok,
                               order_out, upi_link, validate_items)
from ..timeutil import iso_utc

router = APIRouter(prefix="/api", tags=["buyer"])
_s = get_settings()
online_limiter = RateLimiter(_s.online_orders_per_window, _s.online_order_window_seconds)


@router.get("/menu")
def menu(db: Session = Depends(get_db)):
    s = get_settings_row(db)
    products = db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.sort)).all()
    groups: dict[str, list] = {"base": [], "topping": [], "sauce": [], "seasoning": [], "extra": []}
    for i in db.scalars(select(Ingredient).order_by(Ingredient.sort)):
        if i.category in groups and i.is_active:
            groups[i.category].append({"code": i.code, "name": i.name, "note": i.note, "color": i.color,
                                       "available": ingredient_ok(i)})
    return {
        "shop": {"name": s.shop_name, "is_open": s.is_open, "pickup_note": s.pickup_note,
                 "accepts_upi": bool(s.upi_id)},
        "products": [{"code": p.code, "name": p.name, "description": p.description, "price": p.price,
                      "toppings": p.toppings_allowed, "sauces": p.sauces_allowed,
                      "seasonings": p.seasonings_allowed, "cheese": p.includes_cheese} for p in products],
        "ingredients": groups,
    }


@router.post("/orders/online", status_code=201)
def place_online_order(body: OnlineOrderIn, request: Request, db: Session = Depends(get_db)):
    s = get_settings_row(db)
    if not s.is_open:
        raise HTTPException(409, "The cart isn't taking online orders right now. Please come by in person.")
    if body.payment_method == "upi" and not s.upi_id:
        raise HTTPException(400, "UPI isn't set up yet. Choose pay at the cart.")
    if not online_limiter.hit(f"ip:{client_ip(request)}") or not online_limiter.hit(f"ph:{body.customer_phone}"):
        raise HTTPException(429, "You've placed several orders just now. Please wait a few minutes.")
    lines, need = validate_items(db, body.items)
    order = create_order(db, lines, need, source="online", status="placed", payment_method=body.payment_method,
                         paid=False, user=None, customer_name=body.customer_name,
                         customer_phone=body.customer_phone, note=body.note)
    return {"number": order.daily_number, "tracking_token": order.tracking_token, "total": order.total_amount}


def _find(db: Session, token: str) -> Order:
    order = db.scalar(select(Order).where(Order.tracking_token == token))
    if not order:
        raise HTTPException(404, "We couldn't find that order. Check the link you were given.")
    return order


@router.get("/track/{token}")
def track(token: str, db: Session = Depends(get_db)):
    order = _find(db, token)
    s = get_settings_row(db)
    ahead = 0
    if order.status in ("placed", "preparing"):
        ahead = db.scalar(select(func.count(Order.id)).where(
            Order.business_date == order.business_date, Order.status.in_(("placed", "preparing")),
            Order.created_at < order.created_at)) or 0
    data = order_out(order)
    return {
        "number": order.daily_number, "business_date": order.business_date, "status": order.status,
        "customer_name": order.customer_name, "total_amount": order.total_amount,
        "payment_method": order.payment_method, "payment_status": order.payment_status,
        "created_at": iso_utc(order.created_at), "items": data["items"], "ahead": ahead,
        "can_cancel": order.status == "placed" and order.payment_status == "unpaid",
        "upi_link": upi_link(s, order) if order.payment_method == "upi" else None,
        "upi_id": s.upi_id if order.payment_method == "upi" else "",
        "upi_name": s.upi_name or s.shop_name,
        "pickup_note": s.pickup_note, "active": order.status in ACTIVE_STATUSES,
    }


@router.post("/track/{token}/cancel")
def cancel_by_customer(token: str, db: Session = Depends(get_db)):
    order = _find(db, token)
    if order.status != "placed" or order.payment_status != "unpaid":
        raise HTTPException(409, "We've already started on this order. Please speak to us at the cart.")
    change_status(db, order, "cancelled", None, "Cancelled by customer")
    return {"status": order.status}
