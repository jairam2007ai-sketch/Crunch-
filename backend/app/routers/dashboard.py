from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_owner, require_staff
from ..models import Refund, User
from ..services.orders import get_settings_row
from ..services.reports import costs_are_set, daily_series, hourly, inventory_status, summarize, top_ingredients
from ..timeutil import today_local

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
OWNER_ONLY = ("cost", "profit")


@router.get("/today")
def today(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    d = today_local()
    s = summarize(db, d, d)
    if user.role != "owner":
        for k in OWNER_ONLY:
            s.pop(k, None)
    settings = get_settings_row(db)
    return {"date": d.isoformat(), "summary": s,
            "target": {"min": settings.daily_target_min, "max": settings.daily_target_max},
            "is_open": settings.is_open}


@router.get("/summary")
def summary(days: int = Query(default=14, ge=7, le=90), db: Session = Depends(get_db), user: User = Depends(require_owner)):
    d = today_local()
    settings = get_settings_row(db)
    week_first = d - timedelta(days=6)
    return {
        "date": d.isoformat(),
        "today": summarize(db, d, d),
        "yesterday": summarize(db, d - timedelta(days=1), d - timedelta(days=1)),
        "last_7_days": summarize(db, week_first, d),
        "series": daily_series(db, days),
        "hourly": hourly(db, d),
        "top": top_ingredients(db, week_first, d),
        "low_stock": [i for i in inventory_status(db) if i["low"] or (i["tracked"] and i["out"])],
        "pending_refunds": db.scalar(select(func.count(Refund.id)).where(Refund.status == "pending")) or 0,
        "target": {"min": settings.daily_target_min, "max": settings.daily_target_max},
        "costs_set": costs_are_set(db),
        "is_open": settings.is_open,
    }
