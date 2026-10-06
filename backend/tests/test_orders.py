from conftest import loaded, packet


def online(client, items, phone="9876543210", method="pay_at_cart"):
    return client.post("/api/orders/online", json={"customer_name": "Meera", "customer_phone": phone,
                                                   "items": items, "payment_method": method})


def ingredient_id(client, headers, category, code):
    return next(i["id"] for i in client.get("/api/inventory", headers=headers).json()
                if i["category"] == category and i["code"] == code)


def test_menu_lists_sizes_and_ingredients(client):
    m = client.get("/api/menu").json()
    assert [p["code"] for p in m["products"]] == ["regular", "loaded"]
    assert [p["price"] for p in m["products"]] == [49, 69]
    assert len(m["ingredients"]["topping"]) == 5
    assert m["shop"]["is_open"] is True


def test_online_order_is_priced_by_the_server_and_numbered(client):
    r = online(client, [packet(qty=2), loaded()])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total"] == 49 * 2 + 69
    assert body["number"] == 1
    assert online(client, [packet()], phone="9876500000").json()["number"] == 2

    t = client.get(f"/api/track/{body['tracking_token']}").json()
    assert t["status"] == "placed"
    assert t["payment_status"] == "unpaid"
    assert t["can_cancel"] is True
    assert t["items"][1]["selections"]["cheese"] is True


def test_queue_position(client):
    first = online(client, [packet()]).json()
    second = online(client, [packet()], phone="9876500001").json()
    assert client.get(f"/api/track/{first['tracking_token']}").json()["ahead"] == 0
    assert client.get(f"/api/track/{second['tracking_token']}").json()["ahead"] == 1


def test_menu_limits_are_enforced(client):
    r = online(client, [packet(toppings=("onion", "corn", "tomato"))])
    assert r.status_code == 400
    assert "up to 2 toppings" in r.json()["detail"]
    r = online(client, [packet(base="nachos")])
    assert r.status_code == 400
    r = online(client, [loaded(sauces=("garlic", "periperi", "tandoori"))])
    assert "up to 2 sauces" in r.json()["detail"]


def test_bad_phone_is_rejected(client):
    r = online(client, [packet()], phone="12345")
    assert r.status_code == 422


def test_closed_cart_refuses_online_orders(client, seller):
    assert client.post("/api/settings/open", json={"is_open": False}, headers=seller).status_code == 200
    r = online(client, [packet()])
    assert r.status_code == 409


def test_upi_needs_a_upi_id(client, owner):
    assert online(client, [packet()], method="upi").status_code == 400
    client.patch("/api/settings", json={"upi_id": "crunch@okaxis"}, headers=owner)
    r = online(client, [packet()], method="upi")
    assert r.status_code == 201
    t = client.get(f"/api/track/{r.json()['tracking_token']}").json()
    assert t["upi_link"].startswith("upi://pay?pa=crunch%40okaxis")
    assert "am=49" in t["upi_link"]


def test_stock_runs_out_and_comes_back_on_cancel(client, seller):
    potato = ingredient_id(client, seller, "base", "potato")
    client.post(f"/api/inventory/{potato}/adjust", json={"type": "in", "quantity": 2}, headers=seller)
    first = online(client, [packet(qty=2)])
    assert first.status_code == 201
    r = online(client, [packet()], phone="9876500002")
    assert r.status_code == 409
    assert "Potato chips" in r.json()["detail"]
    assert client.get("/api/menu").json()["ingredients"]["base"][0]["available"] is False

    assert client.post(f"/api/track/{first.json()['tracking_token']}/cancel").status_code == 200
    assert online(client, [packet()], phone="9876500003").status_code == 201


def test_loaded_uses_a_bigger_base_portion(client, seller):
    masala = ingredient_id(client, seller, "base", "masala")
    client.post(f"/api/inventory/{masala}/adjust", json={"type": "in", "quantity": 2}, headers=seller)
    assert online(client, [loaded(base="masala")]).status_code == 201
    stock = next(i for i in client.get("/api/inventory", headers=seller).json() if i["id"] == masala)
    assert stock["stock"] == 0.5


def test_status_flow(client, seller):
    order = client.post("/api/orders", headers=seller, json={"items": [packet()], "payment_method": "cash"}).json()
    assert order["status"] == "preparing"
    assert order["payment_status"] == "paid"
    for s in ("ready", "completed"):
        r = client.patch(f"/api/orders/{order['id']}/status", json={"status": s}, headers=seller)
        assert r.status_code == 200 and r.json()["status"] == s
    r = client.patch(f"/api/orders/{order['id']}/status", json={"status": "preparing"}, headers=seller)
    assert r.status_code == 409


def test_paid_orders_cannot_be_cancelled(client, seller):
    order = client.post("/api/orders", headers=seller, json={"items": [packet()], "payment_method": "upi"}).json()
    r = client.patch(f"/api/orders/{order['id']}/status", json={"status": "cancelled"}, headers=seller)
    assert r.status_code == 409
    assert "Refund" in r.json()["detail"]


def test_customer_cannot_cancel_once_started(client, seller):
    token = online(client, [packet()]).json()["tracking_token"]
    order = client.get("/api/orders", headers=seller).json()[0]
    client.patch(f"/api/orders/{order['id']}/status", json={"status": "preparing"}, headers=seller)
    assert client.post(f"/api/track/{token}/cancel").status_code == 409


def test_mark_paid(client, seller):
    online(client, [packet()])
    order = client.get("/api/orders", headers=seller).json()[0]
    r = client.post(f"/api/orders/{order['id']}/pay", json={"method": "cash"}, headers=seller)
    assert r.json()["payment_status"] == "paid"
    assert client.post(f"/api/orders/{order['id']}/pay", json={"method": "cash"}, headers=seller).status_code == 409


def test_active_queue_filter(client, seller):
    online(client, [packet()])
    done = client.post("/api/orders", headers=seller, json={"items": [packet()], "payment_method": "cash"}).json()
    client.patch(f"/api/orders/{done['id']}/status", json={"status": "completed"}, headers=seller)
    active = client.get("/api/orders?active=true", headers=seller).json()
    assert [o["status"] for o in active] == ["placed"]


def test_online_order_rate_limit(client):
    for i in range(5):
        assert online(client, [packet()]).status_code == 201
    assert online(client, [packet()]).status_code == 429
