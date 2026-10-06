"""Order rules shared by the buyer site, the seller POS and the AI assistant.

Prices always come from the database, never from the browser.
"""
from collections import defaultdict
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import audit
from ..models import Ingredient, InventoryTransaction, Order, OrderItem, Payment, Product, Refund, ShopSettings, User, utcnow
from ..schemas import SelectionIn
from ..security import new_tracking_token
from ..timeutil import business_date_str, inr, iso_utc

GROUPS = {"toppings": ("topping", "toppings_allowed"), "sauces": ("sauce", "sauces_allowed"),
          "seasonings": ("seasoning", "seasonings_allowed")}
GROUP_WORD = {"toppings": ("topping", "toppings"), "sauces": ("sauce", "sauces"), "seasonings": ("seasoning", "seasonings")}

ACTIVE_STATUSES = ("placed", "preparing", "ready")
TRANSITIONS = {
    "placed": {"preparing", "ready", "completed", "cancelled"},
    "preparing": {"placed", "ready", "completed", "cancelled"},
    "ready": {"preparing", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def get_settings_row(db: Session) -> ShopSettings:
    s = db.get(ShopSettings, 1)
    if not s:
        s = ShopSettings(id=1)
        db.add(s)
        db.flush()
    return s


def ingredient_ok(ing: Ingredient, need: float = 1.0) -> bool:
    return ing.is_active and (not ing.track_stock or ing.stock_qty + 1e-9 >= need)


def validate_items(db: Session, items: list[SelectionIn]) -> tuple[list[dict], dict[int, float]]:
    """Check every packet against the menu; return priced lines and the portions they use."""
    products = {p.code: p for p in db.scalars(select(Product))}
    ingredients = {(i.category, i.code): i for i in db.scalars(select(Ingredient))}
    cheese = ingredients.get(("extra", "cheese"))
    packet = ingredients.get(("packaging", "packet"))
    need: dict[int, float] = defaultdict(float)
    lines = []

    for n, it in enumerate(items, start=1):
        label = f"Packet {n}" if len(items) > 1 else "Your packet"
        p = products.get(it.product_code)
        if not p or not p.is_active:
            raise HTTPException(400, f"{label}: that size isn't on the menu right now.")
        base = ingredients.get(("base", it.base))
        if not base or not base.is_active:
            raise HTTPException(400, f"{label}: choose a chips base.")
        sel: dict = {"base": base.code}
        for field, (cat, limit_attr) in GROUPS.items():
            codes = list(dict.fromkeys(getattr(it, field)))
            limit = getattr(p, limit_attr)
            if len(codes) > limit:
                one, many = GROUP_WORD[field]
                raise HTTPException(400, f"{label}: {p.name} comes with up to {limit} {one if limit == 1 else many}.")
            for code in codes:
                ing = ingredients.get((cat, code))
                if not ing or not ing.is_active:
                    raise HTTPException(400, f"{label}: {code} isn't available today.")
            sel[field] = codes
        sel["cheese"] = bool(p.includes_cheese)
        if p.includes_cheese and cheese and not cheese.is_active:
            raise HTTPException(409, f"{p.name} isn't available right now because we're out of cheese.")

        q = it.quantity
        need[base.id] += p.base_portions * q
        for field, (cat, _) in GROUPS.items():
            for code in sel[field]:
                need[ingredients[(cat, code)].id] += q
        if p.includes_cheese and cheese:
            need[cheese.id] += q
        if packet:
            need[packet.id] += q
        lines.append({"product": p, "quantity": q, "selections": sel})

    by_id = {i.id: i for i in ingredients.values()}
    short = [by_id[i].name for i, qty in need.items() if by_id[i].track_stock and by_id[i].stock_qty + 1e-9 < qty]
    if short:
        raise HTTPException(409, "Sold out right now: " + ", ".join(short) + ". Please pick something else.")
    return lines, dict(need)


def create_order(db: Session, lines: list[dict], need: dict[int, float], *, source: str, status: str,
                 payment_method: str, paid: bool, user: User | None, customer_name: str = "",
                 customer_phone: str = "", note: str = "", reference: str = "") -> Order:
    bdate = business_date_str()
    total = sum(l["product"].price * l["quantity"] for l in lines)
    order = None
    for _ in range(4):  # two tills creating "order 15" at once: retry with the next number
        number = (db.scalar(select(func.max(Order.daily_number)).where(Order.business_date == bdate)) or 0) + 1
        order = Order(business_date=bdate, daily_number=number, source=source, status=status,
                      customer_name=customer_name, customer_phone=customer_phone, note=note,
                      total_amount=total, payment_method=payment_method,
                      payment_status="paid" if paid else "unpaid", tracking_token=new_tracking_token(),
                      created_by=user.id if user else None)
        for l in lines:
            p = l["product"]
            order.items.append(OrderItem(product_id=p.id, product_code=p.code, product_name=p.name,
                                         quantity=l["quantity"], unit_price=p.price, unit_cost=p.cost or 0,
                                         total=p.price * l["quantity"], selections=l["selections"]))
        db.add(order)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            order = None
    if order is None:
        raise HTTPException(503, "The till is busy. Please try again.")

    for ing_id, qty in need.items():
        ing = db.get(Ingredient, ing_id)
        if ing and ing.track_stock:
            ing.stock_qty = round(ing.stock_qty - qty, 3)
            db.add(InventoryTransaction(ingredient_id=ing.id, type="out", quantity=-qty, balance_after=ing.stock_qty,
                                        order_id=order.id, created_by=user.id if user else None))
    if paid:
        db.add(Payment(order_id=order.id, method=payment_method, amount=total, reference=reference,
                       recorded_by=user.id if user else None))
    audit(db, user, "order.create", "order", order.id,
          new={"number": order.daily_number, "date": bdate, "total": total, "source": source})
    db.commit()
    db.refresh(order)
    return order


def restore_stock(db: Session, order: Order, user: User | None) -> None:
    outs = db.scalars(select(InventoryTransaction).where(InventoryTransaction.order_id == order.id,
                                                         InventoryTransaction.type == "out")).all()
    for t in outs:
        ing = db.get(Ingredient, t.ingredient_id)
        if ing and ing.track_stock:
            ing.stock_qty = round(ing.stock_qty - t.quantity, 3)
            db.add(InventoryTransaction(ingredient_id=ing.id, type="return", quantity=-t.quantity,
                                        balance_after=ing.stock_qty, order_id=order.id,
                                        note=f"Order {order.daily_number} cancelled",
                                        created_by=user.id if user else None))


def change_status(db: Session, order: Order, new_status: str, user: User | None, reason: str = "") -> Order:
    old = order.status
    if new_status == old:
        return order
    if new_status not in TRANSITIONS.get(old, set()):
        raise HTTPException(409, f"Order {order.daily_number} is {old}; it can't be moved to {new_status}.")
    if new_status == "cancelled":
        if order.payment_status in ("paid", "partially_refunded"):
            raise HTTPException(409, "This order has been paid. Refund the payment before cancelling it.")
        restore_stock(db, order, user)
        order.cancel_reason = reason[:200]
    if new_status == "completed":
        order.completed_at = utcnow()
    order.status = new_status
    audit(db, user, "order.status", "order", order.id, old={"status": old}, new={"status": new_status, "reason": reason})
    db.commit()
    db.refresh(order)
    return order


def _lock(db: Session, order: Order) -> Order:
    """Re-read the order with a row lock (Postgres) so concurrent clicks are handled one at a time."""
    return db.scalar(select(Order).where(Order.id == order.id).with_for_update()) or order


def record_payment(db: Session, order: Order, method: str, reference: str, user: User) -> Order:
    order = _lock(db, order)
    if order.status == "cancelled":
        raise HTTPException(409, "This order was cancelled.")
    if order.payment_status != "unpaid":
        raise HTTPException(409, "This order is already paid.")
    db.add(Payment(order_id=order.id, method=method, amount=order.total_amount, reference=reference, recorded_by=user.id))
    order.payment_status = "paid"
    order.payment_method = method
    audit(db, user, "order.paid", "order", order.id, new={"method": method, "amount": order.total_amount})
    db.commit()
    db.refresh(order)
    return order


def paid_amount(order: Order) -> int:
    return sum(p.amount for p in order.payments)


def refundable(db: Session, order: Order) -> int:
    pending = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(
        Refund.order_id == order.id, Refund.status == "pending")) or 0
    return max(0, paid_amount(order) - order.refunded_amount - pending)


def request_refund(db: Session, order: Order, amount: int, method: str, reason: str, user: User) -> Refund:
    order = _lock(db, order)
    if order.payment_status == "unpaid":
        raise HTTPException(409, "This order hasn't been paid, so there's nothing to refund.")
    left = refundable(db, order)
    if amount > left:
        raise HTTPException(409, f"You can refund at most {inr(left)} on this order.")
    refund = Refund(order_id=order.id, amount=amount, method=method, reason=reason.strip(), requested_by=user.id)
    db.add(refund)
    db.flush()
    audit(db, user, "refund.request", "refund", refund.id,
          new={"order": order.daily_number, "date": order.business_date, "amount": amount, "reason": reason})
    db.commit()
    if user.role == "owner":  # the owner is the approver; no point asking themselves
        return decide_refund(db, refund, True, "Created by owner", user)
    db.refresh(refund)
    return refund


def decide_refund(db: Session, refund: Refund, approve: bool, note: str, user: User) -> Refund:
    order = _lock(db, refund.order)
    db.refresh(refund)
    if refund.status != "pending":
        raise HTTPException(409, f"This refund was already {refund.status}.")
    if approve:
        left = paid_amount(order) - order.refunded_amount
        if refund.amount > left:
            raise HTTPException(409, f"Only {inr(left)} is left to refund on this order.")
        order.refunded_amount += refund.amount
        order.payment_status = "refunded" if order.refunded_amount >= paid_amount(order) else "partially_refunded"
    refund.status = "approved" if approve else "rejected"
    refund.decided_by = user.id
    refund.decided_at = utcnow()
    refund.decision_note = note[:200]
    audit(db, user, "refund.approve" if approve else "refund.reject", "refund", refund.id,
          new={"amount": refund.amount, "order": order.daily_number, "note": note})
    db.commit()
    db.refresh(refund)
    return refund


def upi_link(settings: ShopSettings, order: Order) -> str | None:
    if not settings.upi_id or order.payment_status != "unpaid" or order.status == "cancelled":
        return None
    name = settings.upi_name or settings.shop_name
    note = f"Crunch order {order.daily_number}"
    return (f"upi://pay?pa={quote(settings.upi_id)}&pn={quote(name)}&am={order.total_amount}"
            f"&cu=INR&tn={quote(note)}")


def order_out(order: Order, names: dict[int, str] | None = None) -> dict:
    return {
        "id": order.id, "number": order.daily_number, "business_date": order.business_date,
        "source": order.source, "status": order.status, "customer_name": order.customer_name,
        "customer_phone": order.customer_phone, "note": order.note, "total_amount": order.total_amount,
        "payment_method": order.payment_method, "payment_status": order.payment_status,
        "refunded_amount": order.refunded_amount, "cancel_reason": order.cancel_reason,
        "created_at": iso_utc(order.created_at), "updated_at": iso_utc(order.updated_at),
        "created_by_name": (names or {}).get(order.created_by) if order.created_by else None,
        "items": [{"id": i.id, "product_code": i.product_code, "product_name": i.product_name,
                   "quantity": i.quantity, "unit_price": i.unit_price, "total": i.total,
                   "selections": i.selections} for i in order.items],
    }


def user_names(db: Session) -> dict[int, str]:
    return {u.id: u.name for u in db.scalars(select(User))}
