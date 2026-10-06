"""Command-line setup.

    python -m app.cli create-owner --email you@example.com --name "Your Name"
    python -m app.cli create-seller --email helper@example.com --name "Helper"
    python -m app.cli demo-data --days 14 --yes      (sample orders for trying the dashboards)
"""
import argparse
import getpass
import random
import secrets
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .accounts import email_problem, password_problem
from .db import Base, SessionLocal, engine
from .migrate import upgrade
from .models import Ingredient, Order, OrderItem, Payment, Product, User
from .security import hash_password, new_tracking_token, password_weakness
from .seed import ensure_seed
from .timeutil import shop_tz, today_local


def _init():
    Base.metadata.create_all(engine)
    upgrade(engine)
    db = SessionLocal()
    ensure_seed(db)
    return db


def create_user(role: str, email: str, name: str, password: str | None) -> None:
    db = _init()
    email = email.strip().lower()
    if problem := email_problem(db, email):
        sys.exit(problem)
    if not password:
        password = getpass.getpass("Password (8+ characters): ")
        if password != getpass.getpass("Type it again: "):
            sys.exit("The passwords didn't match.")
    if problem := password_weakness(password, email, name):
        sys.exit(problem)
    if problem := password_problem(db, password, role):
        sys.exit(problem)
    db.add(User(name=name, email=email, password_hash=hash_password(password), role=role))
    db.commit()
    print(f"Created {role} account for {name} <{email}>.")


def setup() -> None:
    """First run (start.bat): a .env with a random secret, the database, and the owner's account."""
    env, example = Path(".env"), Path(".env.example")
    if not env.exists() and example.exists():
        text = example.read_text(encoding="utf-8").replace(
            "JWT_SECRET=dev-only-change-me", f"JWT_SECRET={secrets.token_urlsafe(48)}")
        env.write_text(text, encoding="utf-8")
        print("  Created backend/.env with a new secret key.")
    db = _init()
    if not db.scalar(select(User.id).limit(1)):
        print("  First time here: the admin site will ask you to create your owner account.")


def demo_data(days: int) -> None:
    """Fake orders spread over recent days, marked 'Demo' so they're easy to spot."""
    db = _init()
    rng = random.Random(7)
    products = {p.code: p for p in db.scalars(select(Product))}
    ing = {}
    for i in db.scalars(select(Ingredient)):
        ing.setdefault(i.category, []).append(i.code)
    seller = db.scalar(select(User).where(User.role == "seller")) or db.scalar(select(User))
    tz = shop_tz()
    weights = {"base": [5, 4, 3, 2], "topping": [6, 5, 5, 2, 3], "sauce": [4, 5, 3], "seasoning": [3, 2, 3, 2, 6]}
    made = 0
    for back in range(days - 1, -1, -1):
        day = today_local() - timedelta(days=back)
        if db.scalar(select(Order.id).where(Order.business_date == day.isoformat()).limit(1)):
            continue
        count = rng.randint(14, 34) if back else rng.randint(6, 14)
        for n in range(1, count + 1):
            hour = rng.choice([12, 13, 16, 17, 17, 18, 18, 19, 19, 19, 20, 20, 21])
            local = datetime.combine(day, time(hour, rng.randint(0, 59)), tzinfo=tz)
            if local > datetime.now(tz):
                local = datetime.now(tz) - timedelta(minutes=rng.randint(1, 50))
            created = local.astimezone(timezone.utc).replace(tzinfo=None)
            p = products["loaded" if rng.random() < 0.42 else "regular"]
            qty = 2 if rng.random() < 0.12 else 1

            def pick(cat, k):
                out = []
                while len(out) < k:
                    c = rng.choices(ing[cat], weights=weights[cat])[0]
                    if c not in out:
                        out.append(c)
                return out

            sel = {"base": pick("base", 1)[0], "toppings": pick("topping", p.toppings_allowed),
                   "sauces": pick("sauce", p.sauces_allowed), "seasonings": pick("seasoning", p.seasonings_allowed),
                   "cheese": p.includes_cheese}
            online = rng.random() < 0.3
            method = "upi" if rng.random() < 0.62 else "cash"
            status = "completed" if back or n < count - 2 else rng.choice(["placed", "preparing", "ready"])
            total = p.price * qty
            o = Order(business_date=day.isoformat(), daily_number=n, source="online" if online else "counter",
                      status=status, customer_name="Demo customer" if online else "", total_amount=total,
                      customer_phone="9000000000" if online else "",
                      payment_method=method, payment_status="paid", tracking_token=new_tracking_token(),
                      created_by=None if online else (seller.id if seller else None), created_at=created,
                      updated_at=created, completed_at=created if status == "completed" else None, note="Demo")
            o.items.append(OrderItem(product_id=p.id, product_code=p.code, product_name=p.name, quantity=qty,
                                     unit_price=p.price, unit_cost=p.cost, total=total, selections=sel))
            o.payments.append(Payment(method=method, amount=total, created_at=created))
            db.add(o)
            made += 1
    db.commit()
    print(f"Added {made} demo orders.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="First-run setup: .env, database and the owner account")
    for cmd in ("create-owner", "create-seller"):
        sp = sub.add_parser(cmd)
        sp.add_argument("--email", required=True)
        sp.add_argument("--name", required=True)
        sp.add_argument("--password", help="Leave out to type it privately")
    dp = sub.add_parser("demo-data", help="Add sample orders (never use on your real database)")
    dp.add_argument("--days", type=int, default=14)
    dp.add_argument("--yes", action="store_true", help="Confirm you want fake orders in this database")
    args = ap.parse_args(argv)

    if args.cmd == "setup":
        setup()
    elif args.cmd in ("create-owner", "create-seller"):
        create_user("owner" if args.cmd == "create-owner" else "seller", args.email, args.name, args.password)
    elif args.cmd == "demo-data":
        if not args.yes:
            sys.exit("This adds fake orders. Run again with --yes if this is a test database.")
        demo_data(max(1, min(60, args.days)))


if __name__ == "__main__":
    main()
