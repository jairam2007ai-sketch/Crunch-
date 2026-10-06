"""Tools the business assistant can call. Every number it reports comes from one of these.

Read tools run straight away. Action tools (refunds, approvals, opening/closing the cart)
only *prepare* a change; the owner confirms it in the dashboard before it runs.
"""
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Order, Refund, User
from ..services import orders as order_svc
from ..services import reports
from ..timeutil import inr, parse_date, to_local, today_local


@dataclass
class Tool:
    name: str
    description: str
    params: dict = field(default_factory=dict)
    required: list = field(default_factory=list)
    run: Callable | None = None          # read tools
    prepare: Callable | None = None      # action tools: validate and describe
    execute: Callable | None = None      # action tools: do it, after confirmation

    @property
    def is_action(self) -> bool:
        return self.execute is not None

    def schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": {"type": "object", "properties": self.params, "required": self.required}}}


def _days(days) -> int:
    try:
        return max(1, min(90, int(days)))
    except (TypeError, ValueError):
        return 7


def _range(days: int):
    end = today_local()
    return end - timedelta(days=days - 1), end


def _money(summary: dict) -> dict:
    """Add ₹ strings next to the raw numbers so models quote them correctly."""
    out = dict(summary)
    for k in ("revenue", "refunds", "net_sales", "unpaid_amount", "avg_order", "cost", "profit"):
        if out.get(k) is not None:
            out[k + "_text"] = inr(out[k])
    return out


def _date_or_error(value: str | None):
    if not value:
        return today_local(), None
    try:
        return parse_date(value), None
    except ValueError:
        return None, {"error": "Dates must look like 2026-10-06."}


# ---------- read tools ----------

def get_today_sales(db: Session, user: User) -> dict:
    d = today_local()
    return {"date": d.isoformat(), **_money(reports.summarize(db, d, d))}


def get_sales_by_date(db: Session, user: User, date: str) -> dict:
    d, err = _date_or_error(date)
    if err:
        return err
    return {"date": d.isoformat(), **_money(reports.summarize(db, d, d))}


def get_sales_by_product(db: Session, user: User, days: int = 7) -> dict:
    first, last = _range(_days(days))
    s = reports.summarize(db, first, last)
    return {"from": first.isoformat(), "to": last.isoformat(),
            "by_product": {k: {**v, "revenue_text": inr(v["revenue"])} for k, v in s["by_product"].items()}}


def get_sales_by_payment(db: Session, user: User, days: int = 7) -> dict:
    first, last = _range(_days(days))
    s = reports.summarize(db, first, last)
    return {"from": first.isoformat(), "to": last.isoformat(),
            "cash": inr(s["by_payment"].get("cash", 0)), "upi": inr(s["by_payment"].get("upi", 0)),
            "cash_amount": s["by_payment"].get("cash", 0), "upi_amount": s["by_payment"].get("upi", 0),
            "unpaid_orders": s["unpaid_orders"], "unpaid_amount": inr(s["unpaid_amount"])}


def get_refund_summary(db: Session, user: User, days: int = 7) -> dict:
    first, last = _range(_days(days))
    s = reports.summarize(db, first, last)
    pending = db.scalars(select(Refund).where(Refund.status == "pending").order_by(Refund.created_at)).all()
    return {"from": first.isoformat(), "to": last.isoformat(), "approved_total": inr(s["refunds"]),
            "approved_count": s["refund_count"],
            "pending": [{"refund_id": r.id, "order_number": r.order.daily_number, "order_date": r.order.business_date,
                         "amount": inr(r.amount), "reason": r.reason} for r in pending]}


def get_inventory_status(db: Session, user: User) -> dict:
    items = reports.inventory_status(db)
    tracked = [i for i in items if i["tracked"]]
    return {"tracked_items": len(tracked),
            "low_or_out": [{"name": i["name"], "stock_portions": i["stock"], "low_at": i["low_at"]}
                           for i in items if i["low"] or (i["tracked"] and i["out"])],
            "turned_off": [i["name"] for i in items if not i["active"]],
            "note": "Stock is only counted for items someone has recorded a delivery or count for."}


def get_top_products(db: Session, user: User, days: int = 7) -> dict:
    first, last = _range(_days(days))
    top = reports.top_ingredients(db, first, last)
    return {"from": first.isoformat(), "to": last.isoformat(),
            **{cat: rows[:5] for cat, rows in top.items()}}


def compare_sales_period(db: Session, user: User, days: int = 7) -> dict:
    c = reports.compare_periods(db, _days(days))
    return {"days": c["days"], "this_period": _money(c["this_period"]), "previous_period": _money(c["previous_period"]),
            "revenue_change_pct": c["revenue_change_pct"], "orders_change_pct": c["orders_change_pct"]}


def get_profit_summary(db: Session, user: User, days: int = 7) -> dict:
    first, last = _range(_days(days))
    s = reports.summarize(db, first, last)
    if s["profit"] is None:
        return {"from": first.isoformat(), "to": last.isoformat(), "profit": None,
                "reason": "Cost per packet isn't set for every size. Set it in Menu & prices.",
                "net_sales": inr(s["net_sales"])}
    return {"from": first.isoformat(), "to": last.isoformat(), "net_sales": inr(s["net_sales"]),
            "cost": inr(s["cost"]), "profit": inr(s["profit"]),
            "margin_pct": round(s["profit"] / s["net_sales"] * 100, 1) if s["net_sales"] else None}


def get_daily_report(db: Session, user: User, date: str | None = None) -> dict:
    d, err = _date_or_error(date)
    if err:
        return err
    s = reports.summarize(db, d, d)
    top = reports.top_ingredients(db, d, d)
    reg = s["by_product"].get("regular", {"packets": 0})["packets"]
    load = s["by_product"].get("loaded", {"packets": 0})["packets"]
    lines = [
        f"Crunch report for {d.strftime('%a %d %b %Y')}",
        f"Orders: {s['orders']} ({s['packets']} packets: {reg} Regular, {load} Loaded)",
        f"Sales collected: {inr(s['revenue'])} (cash {inr(s['by_payment'].get('cash', 0))}, UPI {inr(s['by_payment'].get('upi', 0))})",
        f"Refunds: {inr(s['refunds'])} · Net: {inr(s['net_sales'])}",
    ]
    if s["unpaid_orders"]:
        lines.append(f"Still unpaid: {s['unpaid_orders']} orders, {inr(s['unpaid_amount'])}")
    if s["profit"] is not None:
        lines.append(f"Estimated profit: {inr(s['profit'])}")
    if top["topping"]:
        lines.append("Top topping: " + top["topping"][0]["name"])
    return {"date": d.isoformat(), "report": "\n".join(lines)}


def find_order(db: Session, user: User, order_number: int, date: str | None = None) -> dict:
    d, err = _date_or_error(date)
    if err:
        return err
    o = db.scalar(select(Order).where(Order.business_date == d.isoformat(), Order.daily_number == int(order_number)))
    if not o:
        return {"error": f"No order {order_number} on {d.isoformat()}."}
    out = order_svc.order_out(o)
    out["placed_at_local"] = to_local(o.created_at).strftime("%I:%M %p")
    out["total_text"] = inr(o.total_amount)
    return out


# ---------- action tools (need the owner's confirmation) ----------

def _order_for(db: Session, order_number, date):
    d, err = _date_or_error(date)
    if err:
        raise HTTPException(400, err["error"])
    o = db.scalar(select(Order).where(Order.business_date == d.isoformat(), Order.daily_number == int(order_number)))
    if not o:
        raise HTTPException(404, f"No order {order_number} on {d.isoformat()}.")
    return o


def prepare_refund(db, user, order_number, amount, reason, date=None, method="upi"):
    o = _order_for(db, order_number, date)
    amount = int(amount)
    left = order_svc.refundable(db, o)
    if o.payment_status == "unpaid":
        raise HTTPException(409, f"Order {o.daily_number} hasn't been paid.")
    if amount < 1 or amount > left:
        raise HTTPException(409, f"Order {o.daily_number} can be refunded up to {inr(left)}.")
    method = method if method in ("cash", "upi") else "upi"
    return {"summary": f"Refund {inr(amount)} by {method.upper()} on order {o.daily_number} ({o.business_date}). Reason: {reason}"}


def execute_refund(db, user, order_number, amount, reason, date=None, method="upi"):
    o = _order_for(db, order_number, date)
    method = method if method in ("cash", "upi") else "upi"
    r = order_svc.request_refund(db, o, int(amount), method, str(reason)[:200] or "Refund", user)
    return {"message": f"Refund of {inr(r.amount)} on order {o.daily_number} is {r.status}."}


def _pending_refund(db, refund_id) -> Refund:
    r = db.get(Refund, int(refund_id))
    if not r:
        raise HTTPException(404, f"There's no refund {refund_id}.")
    if r.status != "pending":
        raise HTTPException(409, f"Refund {refund_id} was already {r.status}.")
    return r


def prepare_approve(db, user, refund_id):
    r = _pending_refund(db, refund_id)
    return {"summary": f"Approve the {inr(r.amount)} refund on order {r.order.daily_number} ({r.order.business_date}). Reason given: {r.reason}"}


def execute_approve(db, user, refund_id):
    r = order_svc.decide_refund(db, _pending_refund(db, refund_id), True, "Approved in assistant", user)
    return {"message": f"Approved {inr(r.amount)} refund on order {r.order.daily_number}."}


def prepare_open(db, user, open):
    s = order_svc.get_settings_row(db)
    want = bool(open)
    if s.is_open == want:
        raise HTTPException(409, "Online ordering is already " + ("open." if want else "closed."))
    return {"summary": ("Open" if want else "Close") + " the cart for online orders."}


def execute_open(db, user, open):
    s = order_svc.get_settings_row(db)
    s.is_open = bool(open)
    db.commit()
    return {"message": "Online ordering is now " + ("open." if s.is_open else "closed.")}


DAYS = {"days": {"type": "integer", "description": "How many days back to include, counting today. Default 7.", "minimum": 1, "maximum": 90}}
DATE = {"date": {"type": "string", "description": "Shop-local date as YYYY-MM-DD"}}

TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("get_today_sales", "Today's orders, packets, sales collected, refunds, unpaid orders, cash/UPI split and profit (if costs are set).", run=get_today_sales),
    Tool("get_sales_by_date", "The same sales summary for one past date.", DATE, ["date"], run=get_sales_by_date),
    Tool("get_sales_by_product", "Packets and sales for Regular vs Loaded over recent days.", DAYS, run=get_sales_by_product),
    Tool("get_sales_by_payment", "Cash vs UPI collected, and unpaid orders, over recent days.", DAYS, run=get_sales_by_payment),
    Tool("get_refund_summary", "Approved refunds over recent days and every refund still waiting for approval (with refund_id).", DAYS, run=get_refund_summary),
    Tool("get_inventory_status", "Which ingredients are low, out of stock or turned off.", run=get_inventory_status),
    Tool("get_top_products", "Most chosen bases, toppings, sauces and seasonings over recent days.", DAYS, run=get_top_products),
    Tool("compare_sales_period", "Compare the last N days with the N days before (sales, orders, percent change).", DAYS, run=compare_sales_period),
    Tool("get_profit_summary", "Net sales, estimated cost and profit over recent days. Profit is null when costs aren't set.", DAYS, run=get_profit_summary),
    Tool("get_daily_report", "A short written end-of-day report for a date (default today).", DATE, run=get_daily_report),
    Tool("find_order", "Look up one order by its number on a date (default today).",
         {"order_number": {"type": "integer"}, **DATE}, ["order_number"], run=find_order),
    Tool("create_refund_request", "ACTION: refund money on a paid order. Needs the owner's confirmation before it happens.",
         {"order_number": {"type": "integer"}, "amount": {"type": "integer", "description": "Rupees"},
          "reason": {"type": "string"}, "method": {"type": "string", "enum": ["cash", "upi"]}, **DATE},
         ["order_number", "amount", "reason"], prepare=prepare_refund, execute=execute_refund),
    Tool("approve_refund", "ACTION: approve a pending refund by refund_id. Needs the owner's confirmation.",
         {"refund_id": {"type": "integer"}}, ["refund_id"], prepare=prepare_approve, execute=execute_approve),
    Tool("set_online_ordering", "ACTION: open or close the cart for online orders. Needs the owner's confirmation.",
         {"open": {"type": "boolean"}}, ["open"], prepare=prepare_open, execute=execute_open),
]}
