from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import Base, engine
from app.main import app
from app.ratelimit import login_limiter


def test_first_owner_is_created_from_settings(monkeypatch):
    Base.metadata.drop_all(engine)
    login_limiter.reset()
    s = get_settings()
    monkeypatch.setattr(s, "owner_email", "First@Shop.in")
    monkeypatch.setattr(s, "owner_password", "first-pass-1")
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"email": "first@shop.in", "password": "first-pass-1"})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "owner"
        # the menu is seeded on first start too
        assert len(c.get("/api/menu").json()["products"]) == 2


def test_health(client):
    assert client.get("/api/health").json() == {"ok": True}
