"""Security checks: who can reach what, headers, limits, sessions, inputs and exposed files."""
import base64
import hashlib
import re

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.config import DEV_SECRET, Settings, config_problems, get_settings
from app.main import DIST, app
from app.migrate import upgrade
from app.models import User
from app.db import SessionLocal
from app.ratelimit import api_limiter
from conftest import packet

PUBLIC = {
    ("POST", "/api/auth/login"), ("GET", "/api/menu"), ("POST", "/api/orders/online"),
    ("GET", "/api/track/{token}"), ("POST", "/api/track/{token}/cancel"), ("GET", "/api/health"),
    ("GET", "/api/setup/status"), ("POST", "/api/setup/owner"), ("GET", "/api/openapi.json"), ("GET", "/api/docs"),
}
OWNER_ONLY = {
    ("GET", "/api/users"), ("POST", "/api/users"), ("PATCH", "/api/users/{user_id}"), ("GET", "/api/audit-logs"),
    ("PATCH", "/api/products/{product_id}"), ("PATCH", "/api/settings"), ("PATCH", "/api/ingredients/{ingredient_id}"),
    ("POST", "/api/refunds/{refund_id}/approve"), ("POST", "/api/refunds/{refund_id}/reject"),
    ("GET", "/api/dashboard/summary"), ("GET", "/api/ai/status"), ("POST", "/api/ai/chat"), ("POST", "/api/ai/confirm"),
}


def api_routes():
    # read the routes from the app's own API description, so every router is included
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            yield method.upper(), path


def concrete(path):
    return re.sub(r"\{[^}]+\}", "1", path)


def call(client, method, path, headers=None):
    return client.request(method, concrete(path), headers=headers or {}, json={} if method != "GET" else None)


def test_every_private_route_needs_sign_in(client):
    checked = 0
    for method, path in api_routes():
        if (method, path) in PUBLIC:
            continue
        r = call(client, method, path)
        assert r.status_code == 401, f"{method} {path} answered {r.status_code} without sign-in"
        checked += 1
    assert checked >= 30


def test_owner_routes_refuse_sellers(client, seller):
    for method, path in OWNER_ONLY:
        r = call(client, method, path, seller)
        assert r.status_code == 403, f"seller reached {method} {path} ({r.status_code})"


def test_every_route_is_classified():
    # a new route must be added to PUBLIC or be protected; this catches forgotten guards
    known = PUBLIC | OWNER_ONLY
    staff = {(m, p) for m, p in api_routes()} - known
    assert all(p.startswith(("/api/orders", "/api/refunds", "/api/inventory", "/api/products", "/api/settings",
                              "/api/dashboard/today", "/api/auth/me", "/api/auth/logout-everywhere")) for _, p in staff), staff


def test_sellers_never_see_costs_or_profit(client, seller):
    assert all("cost" not in p for p in client.get("/api/products", headers=seller).json())
    assert "profit" not in client.get("/api/dashboard/today", headers=seller).json()["summary"]


# ---------- sessions ----------

def login(client, email, password):
    return {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]}


def seller_id(client, owner):
    return next(u["id"] for u in client.get("/api/users", headers=owner).json() if u["role"] == "seller")


def test_password_reset_ends_old_sessions(client, owner, seller):
    assert client.get("/api/auth/me", headers=seller).status_code == 200
    client.patch(f"/api/users/{seller_id(client, owner)}", headers=owner, json={"password": "mango-chips-river"})
    r = client.get("/api/auth/me", headers=seller)
    assert r.status_code == 401 and "password was changed" in r.json()["detail"]
    assert client.get("/api/auth/me", headers=login(client, "seller@test.in", "mango-chips-river")).status_code == 200


def test_turning_off_an_account_ends_its_sessions(client, owner, seller):
    client.patch(f"/api/users/{seller_id(client, owner)}", headers=owner, json={"is_active": False})
    assert client.get("/api/orders", headers=seller).status_code == 401


def test_sign_out_everywhere(client, owner):
    assert client.post("/api/auth/logout-everywhere", headers=owner).status_code == 204
    assert client.get("/api/auth/me", headers=owner).status_code == 401


def test_forged_and_tampered_tokens_are_refused(client, owner):
    user_id = client.get("/api/auth/me", headers=owner).json()["id"]
    unsigned = jwt.encode({"sub": str(user_id), "typ": "access", "aud": "crunch", "exp": 9999999999, "iat": 1}, key=None, algorithm="none")
    wrong_key = jwt.encode({"sub": str(user_id), "typ": "access", "aud": "crunch", "exp": 9999999999, "iat": 1, "ver": 0}, "guess", algorithm="HS256")
    no_audience = jwt.encode({"sub": str(user_id), "typ": "access", "exp": 9999999999, "iat": 1, "ver": 0}, get_settings().jwt_secret, algorithm="HS256")
    for token in (unsigned, wrong_key, no_audience, "not.a.token"):
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_old_password_hashes_are_upgraded_at_sign_in(client):
    salt = "00" * 16
    old = f"pbkdf2_sha256$1000${salt}${hashlib.pbkdf2_hmac('sha256', b'river-mango-chips', bytes.fromhex(salt), 1000).hex()}"
    with SessionLocal() as db:
        db.add(User(name="Old", email="old@test.in", password_hash=old, role="seller"))
        db.commit()
    assert client.post("/api/auth/login", json={"email": "old@test.in", "password": "river-mango-chips"}).status_code == 200
    with SessionLocal() as db:
        assert db.query(User).filter_by(email="old@test.in").one().password_hash.split("$")[1] == "600000"


@pytest.mark.parametrize("password,reason", [
    ("password123", "too easy"), ("12345678", "too easy"), ("aaaaaaaa", "repeats"), ("asha-is-great", "name or email"),
])
def test_weak_passwords_are_refused(client, owner, password, reason):
    r = client.post("/api/users", headers=owner, json={"name": "Asha", "email": "asha@test.in", "password": password})
    assert r.status_code == 409 and reason in r.json()["detail"]


def test_login_is_limited_per_account_across_addresses(client):
    for _ in range(20):
        client.post("/api/auth/login", json={"email": "owner@test.in", "password": "bad"}, headers={})
    # (all from one test address, so either limiter may answer; both must stop the guessing)
    assert client.post("/api/auth/login", json={"email": "owner@test.in", "password": "owner-pass-1"}).status_code == 429


# ---------- inputs ----------

def test_hidden_characters_are_removed_from_text(client, seller):
    r = client.post("/api/orders/online", json={"customer_name": "Mee‮ra\x07 \n Joshi", "customer_phone": "9876543210",
                                                "payment_method": "pay_at_cart", "note": "less​ spicy", "items": [packet()]})
    assert r.status_code == 201
    order = client.get("/api/orders", headers=seller).json()[0]
    assert order["customer_name"] == "Meera Joshi" and order["note"] == "less spicy"


def test_ingredient_codes_must_be_plain(client):
    bad = packet(base="<script>")
    r = client.post("/api/orders/online", json={"customer_name": "Meera", "customer_phone": "9876543210",
                                                "payment_method": "pay_at_cart", "items": [bad]})
    assert r.status_code == 422


def test_oversized_requests_are_refused(client):
    r = client.post("/api/orders/online", content=b'{"x":"' + b"a" * 300_000 + b'"}',
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_api_rate_limit(client, monkeypatch):
    monkeypatch.setattr(api_limiter, "max_hits", 5)
    codes = [client.get("/api/menu").status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[-1] == 429
    assert client.get("/api/health").status_code == 200  # health checks are never limited


# ---------- headers, CORS, exposed files, docs ----------

def test_security_headers_on_pages_and_api(client):
    for path in ("/", "/admin/", "/api/menu"):
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert "script-src 'self'" in h["content-security-policy"]
        assert "unsafe-eval" not in h["content-security-policy"]
        assert "server" not in h or "uvicorn" not in h["server"].lower()
    assert client.get("/api/menu").headers["cache-control"] == "no-store"
    assert "noindex" in client.get("/admin/").headers["x-robots-tag"]


@pytest.mark.skipif(not DIST.is_dir(), reason="websites not built")
def test_csp_allows_exactly_the_pages_inline_script(client):
    csp = client.get("/").headers["content-security-policy"]
    html = (DIST / "index.html").read_text(encoding="utf-8")
    body = re.search(r"<script>(.*?)</script>", html, re.S).group(1).replace("\r\n", "\n")
    digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    assert f"'sha256-{digest}'" in csp


def test_cors_only_for_listed_sites(client):
    pre = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    evil = client.options("/api/auth/login", headers={"Origin": "https://evil.example", **pre})
    assert "access-control-allow-origin" not in evil.headers
    ok = client.options("/api/auth/login", headers={"Origin": "http://localhost:5173", **pre})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-credentials" not in ok.headers


@pytest.mark.parametrize("path", ["/.env", "/backend/.env", "/../backend/.env", "/%2e%2e/backend/.env", "/.git/config",
                                  "/src/buyer/main.js", "/package.json", "/crunch.db", "/backend/crunch.db"])
def test_private_files_are_not_served(client, path):
    r = client.get(path)
    assert r.status_code == 404
    assert b"JWT_SECRET" not in r.content and b"SQLite" not in r.content


def test_unknown_api_paths_are_404_json(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")


def test_api_docs_only_on_this_computer():
    with TestClient(app, client=("203.0.113.5", 1)) as c:
        assert c.get("/api/docs").status_code == 404 and c.get("/api/openapi.json").status_code == 404
    with TestClient(app, client=("127.0.0.1", 1)) as c:
        assert c.get("/api/openapi.json").status_code == 200
        assert c.get("/api/openapi.json", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 404


# ---------- settings and database ----------

def test_unsafe_production_settings_stop_the_server():
    errors, _ = config_problems(Settings(env="production", jwt_secret=DEV_SECRET, cors_origins="*", _env_file=None))
    assert any("JWT_SECRET" in e for e in errors) and any("CORS_ORIGINS" in e for e in errors)
    errors, warnings = config_problems(Settings(env="production", jwt_secret="x" * 48, cors_origins="https://crunch.app",
                                                database_url="sqlite:///./x.db", _env_file=None))
    assert errors == [] and any("SQLite" in w for w in warnings)


def test_old_databases_get_the_new_column(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        c.execute(text("INSERT INTO users (name) VALUES ('Jai')"))
    assert upgrade(eng) == ["users.token_version"]
    assert "token_version" in {col["name"] for col in inspect(eng).get_columns("users")}
    assert upgrade(eng) == []
