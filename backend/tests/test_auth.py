def test_login_and_me(client, owner):
    r = client.get("/api/auth/me", headers=owner)
    assert r.status_code == 200
    assert r.json()["role"] == "owner"


def test_wrong_password_is_rejected(client):
    r = client.post("/api/auth/login", json={"email": "owner@test.in", "password": "nope"})
    assert r.status_code == 401
    assert "wrong" in r.json()["detail"]


def test_no_token_is_rejected(client):
    assert client.get("/api/orders").status_code == 401


def test_seller_cannot_use_owner_endpoints(client, seller):
    assert client.get("/api/users", headers=seller).status_code == 403
    assert client.get("/api/dashboard/summary", headers=seller).status_code == 403
    assert client.patch("/api/products/1", json={"price": 1}, headers=seller).status_code == 403
    assert client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "hi"}]}, headers=seller).status_code == 403


def test_turned_off_account_cannot_sign_in(client, owner):
    users = client.get("/api/users", headers=owner).json()
    ravi = next(u for u in users if u["email"] == "seller@test.in")
    assert client.patch(f"/api/users/{ravi['id']}", json={"is_active": False}, headers=owner).status_code == 200
    r = client.post("/api/auth/login", json={"email": "seller@test.in", "password": "seller-pass-1"})
    assert r.status_code == 403


def test_owner_cannot_turn_off_themselves(client, owner):
    me = client.get("/api/auth/me", headers=owner).json()
    r = client.patch(f"/api/users/{me['id']}", json={"is_active": False}, headers=owner)
    assert r.status_code == 409


def test_login_rate_limit(client):
    for _ in range(8):
        client.post("/api/auth/login", json={"email": "owner@test.in", "password": "bad"})
    r = client.post("/api/auth/login", json={"email": "owner@test.in", "password": "owner-pass-1"})
    assert r.status_code == 429


def test_seller_cannot_reuse_the_owners_email_or_password(client, owner):
    r = client.post("/api/users", headers=owner, json={"name": "Asha", "email": "OWNER@test.in", "password": "mango-chips-river"})
    assert r.status_code == 409 and "owner's sign-in" in r.json()["detail"]
    r = client.post("/api/users", headers=owner, json={"name": "Asha", "email": "asha@test.in", "password": "owner-pass-1"})
    assert r.status_code == 409 and "owner's password" in r.json()["detail"]
    # resetting a seller's password to the owner's is refused too
    ravi = next(u for u in client.get("/api/users", headers=owner).json() if u["email"] == "seller@test.in")
    r = client.patch(f"/api/users/{ravi['id']}", headers=owner, json={"password": "owner-pass-1"})
    assert r.status_code == 409
    # and the owner can't take a seller's password
    me = client.get("/api/auth/me", headers=owner).json()
    r = client.patch(f"/api/users/{me['id']}", headers=owner, json={"password": "seller-pass-1"})
    assert r.status_code == 409 and "seller's" in r.json()["detail"]


def test_owner_creates_seller_who_can_sign_in(client, owner):
    r = client.post("/api/users", headers=owner,
                    json={"name": "Asha", "email": "Asha@Test.in", "password": "mango-chips-river"})
    assert r.status_code == 201
    assert r.json()["email"] == "asha@test.in"
    r = client.post("/api/auth/login", json={"email": "asha@test.in", "password": "mango-chips-river"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "seller"
