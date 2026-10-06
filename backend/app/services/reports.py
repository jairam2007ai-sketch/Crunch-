"""Numbers for the dashboards and the AI assistant.

Revenue counts paid orders only. Unpaid "pay at cart" orders show up as pending money.
Refunds count on the day they were approved.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ingredient, Order, Product, Refund
from ..timeutil import range_bounds_utc, to_local, today_local


def _orders(db: Session, first: date, last: date) -> list[Order]:
    return list(db.scalars(select(Order).where(Order.business_date >= first.isoformat(),
                                               Order.business_date <= last.isoformat())))


def _approved_refunds(db: Session, first: date, last: date) -> list[Refund]:
    start, end = range_bounds_utc(first, last)
    return list(db.scalars(select(Refund).where(Refund.status == "approved", Refund.decided_at >= start,
                                                Refund.decided_at < end)))


def costs_are_set(db: Session) -> bool:
    products = list(db.scalars(select(Product).where(Product.is_active.is_(True))))
    return bool(products) and all((p.cost or 0) > 0 for p in products)


def summarize(db: Session, first: date, last: date, orders: list[Order] | None = None) -> dict:
    orders = orders if orders is not None else _orders(db, first, last)
    live = [o for o in orders if o.status != "cancelled"]
    paid = [o for o in live if o.payment_status != "unpaid"]
    refunds = _approved_refunds(db, first, last)

    revenue = sum(o.total_amount for o in paid)
    refunded = sum(r.amount for r in refunds)
    by_product: dict[str, dict] = defaultdict(lambda: {"packets": 0, "revenue": 0})
    for o in live:
        for i in o.items:
            by_product[i.product_code]["packets"] += i.quantity
            if o.payment_status != "unpaid":
                by_product[i.product_code]["revenue"] += i.total
    by_payment = {"cash": 0, "upi": 0}
    for o in paid:
        for p in o.payments:
            by_payment[p.method] = by_payment.get(p.method, 0) + p.amount
    cost_known = costs_are_set(db) and all(i.unit_cost > 0 for o in paid for i in o.items)
    cost = sum(i.unit_cost * i.quantity for o in paid for i in o.items)

    return {
        "from": first.isoformat(), "to": last.isoformat(),
        "orders": len(live),
        "packets": sum(i.quantity for o in live for i in o.items),
        "revenue": revenue,
        "refunds": refunded,
        "refund_count": len(refunds),
        "net_sales": revenue - refunded,
        "unpaid_orders": sum(1 for o in live if o.payment_status == "unpaid"),
        "unpaid_amount": sum(o.total_amount for o in live if o.payment_status == "unpaid"),
        "cancelled": sum(1 for o in orders if o.status == "cancelled"),
        "online_orders": sum(1 for o in live if o.source == "online"),
        "counter_orders": sum(1 for o in live if o.source == "counter"),
        "by_product": dict(by_product),
        "by_payment": by_payment,
        "avg_order": round(revenue / len(paid)) if paid else 0,
        "cost": cost if cost_known else None,
        "profit": (revenue - refunded - cost) if cost_known else None,
    }


def daily_series(db: Session, days: int, end: date | None = None) -> list[dict]:
    end = end or today_local()
    first = end - timedelta(days=days - 1)
    rows = {(first + timedelta(d)).isoformat(): {"date": (first + timedelta(d)).isoformat(), "orders": 0,
                                                 "packets": 0, "revenue": 0} for d in range(days)}
    for o in _orders(db, first, end):
        if o.status == "cancelled":
            continue
        r = rows[o.business_date]
        r["orders"] += 1
        r["packets"] += sum(i.quantity for i in o.items)
        if o.payment_status != "unpaid":
            r["revenue"] += o.total_amount
    return list(rows.values())


def hourly(db: Session, d: date) -> list[dict]:
    buckets = defaultdict(lambda: {"orders": 0, "revenue": 0})
    for o in _orders(db, d, d):
        if o.status == "cancelled":
            continue
        h = to_local(o.created_at).hour
        buckets[h]["orders"] += 1
        if o.payment_status != "unpaid":
            buckets[h]["revenue"] += o.total_amount
    return [{"hour": h, **buckets[h]} for h in range(24)]


def top_ingredients(db: Session, first: date, last: date) -> dict:
    names = {(i.category, i.code): i.name for i in db.scalars(select(Ingredient))}
    counts: dict[str, Counter] = {"base": Counter(), "topping": Counter(), "sauce": Counter(), "seasoning": Counter()}
    for o in _orders(db, first, last):
        if o.status == "cancelled":
            continue
        for i in o.items:
            s = i.selections or {}
            if s.get("base"):
                counts["base"][s["base"]] += i.quantity
            for field, cat in (("toppings", "topping"), ("sauces", "sauce"), ("seasonings", "seasoning")):
                for code in s.get(field, []):
                    counts[cat][code] += i.quantity
    return {cat: [{"code": c, "name": names.get((cat, c), c), "count": n} for c, n in counter.most_common()]
            for cat, counter in counts.items()}


def inventory_status(db: Session) -> list[dict]:
    out = []
    for i in db.scalars(select(Ingredient).order_by(Ingredient.sort)):
        out.append({
            "id": i.id, "category": i.category, "code": i.code, "name": i.name, "stock": round(i.stock_qty, 2),
            "tracked": i.track_stock, "active": i.is_active, "low_at": i.low_stock_at,
            "low": i.track_stock and i.stock_qty <= i.low_stock_at,
            "out": (i.track_stock and i.stock_qty <= 0) or not i.is_active,
        })
    return out


def compare_periods(db: Session, days: int) -> dict:
    end = today_local()
    this_first = end - timedelta(days=days - 1)
    prev_last = this_first - timedelta(days=1)
    prev_first = prev_last - timedelta(days=days - 1)
    now = summarize(db, this_first, end)
    before = summarize(db, prev_first, prev_last)

    def change(a, b):
        return None if not b else round((a - b) / b * 100, 1)

    return {"days": days, "this_period": now, "previous_period": before,
            "revenue_change_pct": change(now["revenue"], before["revenue"]),
            "orders_change_pct": change(now["orders"], before["orders"])}
