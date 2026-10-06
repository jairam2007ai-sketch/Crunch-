import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AI_PROVIDER"] = "basic"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-use-0123456789"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.ratelimit import reset_all  # noqa: E402
from app.routers.public import online_limiter  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.seed import ensure_seed  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    reset_all()
    online_limiter.reset()
    with SessionLocal() as db:
        ensure_seed(db)
        db.add_all([
            User(name="Owner", email="owner@test.in", password_hash=hash_password("owner-pass-1"), role="owner"),
            User(name="Ravi", email="seller@test.in", password_hash=hash_password("seller-pass-1"), role="seller"),
        ])
        db.commit()
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def owner(client):
    return _login(client, "owner@test.in", "owner-pass-1")


@pytest.fixture()
def seller(client):
    return _login(client, "seller@test.in", "seller-pass-1")


def packet(size="regular", base="potato", toppings=("onion", "corn"), sauces=("garlic",), seasonings=("chaat",), qty=1):
    return {"product_code": size, "quantity": qty, "base": base, "toppings": list(toppings),
            "sauces": list(sauces), "seasonings": list(seasonings)}


def loaded(**kw):
    kw.setdefault("toppings", ("onion", "corn", "tomato"))
    kw.setdefault("sauces", ("garlic", "periperi"))
    kw.setdefault("seasonings", ("chaat", "oregano"))
    return packet(size="loaded", **kw)
