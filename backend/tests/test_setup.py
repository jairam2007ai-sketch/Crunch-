import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.main import app
from app.ratelimit import reset_all
from app.seed import ensure_seed

OWNER = {"name": "Jai", "email": "jai@shop.in", "password": "first-pass-1", "role": "owner"}


def fresh():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    reset_all()
    with SessionLocal() as db:
        ensure_seed(db)


def test_owner_created_from_the_same_computer():
    fresh()
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        assert c.get("/api/setup/status").json() == {"needs_owner": True, "can_setup_here": True}
        assert c.post("/api/setup/owner", json=OWNER).status_code == 201
        assert c.post("/api/auth/login", json={"email": "jai@shop.in", "password": "first-pass-1"}).status_code == 200
        assert c.get("/api/setup/status").json()["needs_owner"] is False
        # a second "first owner" is refused
        assert c.post("/api/setup/owner", json={**OWNER, "email": "x@shop.in"}).status_code == 409


def test_setup_refused_from_another_computer():
    fresh()
    with TestClient(app, client=("203.0.113.9", 50000)) as c:
        assert c.get("/api/setup/status").json() == {"needs_owner": True, "can_setup_here": False}
        assert c.post("/api/setup/owner", json=OWNER).status_code == 403


def test_setup_refused_through_a_tunnel_or_proxy():
    fresh()
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        for header in ({"X-Forwarded-For": "127.0.0.1"}, {"Cf-Connecting-Ip": "198.51.100.4"}):
            assert c.get("/api/setup/status", headers=header).json()["can_setup_here"] is False
            assert c.post("/api/setup/owner", json=OWNER, headers=header).status_code == 403


def test_setup_refused_in_production(monkeypatch):
    fresh()
    s = get_settings()
    monkeypatch.setattr(s, "env", "production")
    monkeypatch.setattr(s, "allow_sqlite_in_production", True)
    # with no owner configured, production won't even start (nobody could ever sign in)
    with pytest.raises(RuntimeError, match="No owner account"):
        with TestClient(app, client=("127.0.0.1", 50000)):
            pass
    # with the owner from settings, the browser form stays shut, even on the server itself
    monkeypatch.setattr(s, "owner_email", "jai@shop.in")
    monkeypatch.setattr(s, "owner_password", "mango-chips-river")
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        assert c.get("/api/setup/status").json()["can_setup_here"] is False
        assert c.post("/api/setup/owner", json=OWNER).status_code == 403
