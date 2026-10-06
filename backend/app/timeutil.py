"""Shop-local dates. The cart's "today" is the shop's calendar day, not UTC's."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import get_settings


def shop_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().shop_timezone)


def now_local() -> datetime:
    return datetime.now(shop_tz())


def today_local() -> date:
    return now_local().date()


def business_date_str(d: date | None = None) -> str:
    return (d or today_local()).isoformat()


def local_day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    """Start and end of a shop-local day, as naive UTC for querying."""
    tz = shop_tz()
    start = datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    return start, end


def range_bounds_utc(first: date, last: date) -> tuple[datetime, datetime]:
    return local_day_bounds_utc(first)[0], local_day_bounds_utc(last)[1]


def to_local(dt_utc_naive: datetime) -> datetime:
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(shop_tz())


def iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def inr(amount: float | int) -> str:
    """Indian digit grouping: 123456 -> ₹1,23,456."""
    n = int(round(amount))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{sign}₹{s}"
