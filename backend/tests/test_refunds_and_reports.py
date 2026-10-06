from conftest import loaded, packet


def counter(client, headers, items=None, method="cash"):
    r = client.post("/api/orders", headers=headers, json={"items": items or [packet()], "payment_method": method})
    assert r.status_code == 201, r.text
    return r.json()


def test_seller_requests_owner_approves(client, seller, owner):
    order = counter(client, seller, [loaded()])
    r = client.post("/api/refunds", headers=seller,
                    json={"order_id": order["id"], "amount": 20, "method": "cash", "reason": "Too little sauce"})
    assert r.status_code == 201
    refund = r.json()
    assert refund["status"] == "pending"

    assert client.post(f"/api/refunds/{refund['id']}/approve", json={}, headers=seller).status_code == 403
    r = client.post(f"/api/refunds/{refund['id']}/approve", json={"note": "ok"}, headers=owner)
    assert r.json()["status"] == "approved"
    assert client.get(f"/api/orders/{order['id']}", headers=owner).json()["payment_status"] == "partially_refunded"
    assert client.post(f"/api/refunds/{refund['id']}/approve", json={}, headers=owner).status_code == 409


def test_refund_cannot_exceed_what_was_paid(client, seller):
    order = counter(client, seller)
    r = client.post("/api/refunds", headers=seller,
                    json={"order_id": order["id"], "amount": 30, "method": "cash", "reason": "Spilled"})
    assert r.status_code == 201
    r = client.post("/api/refunds", headers=seller,
                    json={"order_id": order["id"], "amount": 20, "method": "cash", "reason": "Spilled again"})
    assert r.status_code == 409
    assert "₹19" in r.json()["detail"]


def test_owner_refund_is_approved_straight_away(client, owner):
    order = counter(client, owner)
    r = client.post("/api/refunds", headers=owner,
                    json={"order_id": order["id"], "amount": 49, "method": "upi", "reason": "Wrong order"})
    assert r.json()["status"] == "approved"
    assert client.get(f"/api/orders/{order['id']}", headers=owner).json()["payment_status"] == "refunded"
    # fully refunded orders can now be cancelled
    r = client.patch(f"/api/orders/{order['id']}/status", json={"status": "cancelled"}, headers=owner)
    assert r.status_code == 200


def test_unpaid_orders_cannot_be_refunded(client, seller):
    client.post("/api/orders/online", json={"customer_name": "Meera", "customer_phone": "9876543210",
                                            "items": [packet()], "payment_method": "pay_at_cart"})
    order = client.get("/api/orders", headers=seller).json()[0]
    r = client.post("/api/refunds", headers=seller,
                    json={"order_id": order["id"], "amount": 10, "method": "cash", "reason": "test"})
    assert r.status_code == 409


def test_revenue_counts_paid_orders_minus_refunds(client, seller, owner):
    counter(client, seller, [packet(qty=2)], "cash")      # 98 cash
    paid_upi = counter(client, seller, [loaded()], "upi")  # 69 upi
    client.post("/api/orders/online", json={"customer_name": "Meera", "customer_phone": "9876543210",
                                            "items": [packet()], "payment_method": "pay_at_cart"})  # 49 unpaid
    client.post("/api/refunds", headers=owner,
                json={"order_id": paid_upi["id"], "amount": 19, "method": "upi", "reason": "Late"})

    today = client.get("/api/dashboard/today", headers=seller).json()["summary"]
    assert today["revenue"] == 98 + 69
    assert today["by_payment"] == {"cash": 98, "upi": 69}
    assert today["unpaid_orders"] == 1 and today["unpaid_amount"] == 49
    assert today["refunds"] == 19
    assert today["net_sales"] == 98 + 69 - 19
    assert today["packets"] == 4
    assert "profit" not in today  # sellers don't see profit

    owner_view = client.get("/api/dashboard/summary", headers=owner).json()
    assert owner_view["today"]["profit"] is None and owner_view["costs_set"] is False
    assert len(owner_view["series"]) == 14
    assert owner_view["series"][-1]["revenue"] == 167
    assert owner_view["top"]["topping"][0]["code"] == "onion"


def test_profit_appears_once_costs_are_set(client, owner):
    products = client.get("/api/products", headers=owner).json()
    for p, cost in zip(products, (22, 31), strict=True):
        assert client.patch(f"/api/products/{p['id']}", json={"cost": cost}, headers=owner).status_code == 200
    counter(client, owner, [packet(), loaded()])
    s = client.get("/api/dashboard/summary", headers=owner).json()["today"]
    assert s["profit"] == (49 + 69) - (22 + 31)


def test_seller_cannot_overwrite_counts_but_owner_can(client, seller, owner):
    corn = next(i for i in client.get("/api/inventory", headers=seller).json() if i["code"] == "corn")
    r = client.post(f"/api/inventory/{corn['id']}/adjust", json={"type": "count", "quantity": 5}, headers=seller)
    assert r.status_code == 403
    r = client.post(f"/api/inventory/{corn['id']}/adjust", json={"type": "count", "quantity": 5}, headers=owner)
    assert r.json()["stock"] == 5 and r.json()["tracked"] is True
    r = client.post(f"/api/inventory/{corn['id']}/adjust", json={"type": "waste", "quantity": 9}, headers=seller)
    assert r.status_code == 409


def test_activity_log_records_changes(client, owner):
    client.patch("/api/settings", json={"shop_name": "Crunch Corner"}, headers=owner)
    logs = client.get("/api/audit-logs", headers=owner).json()
    assert logs[0]["action"] == "settings.update"
    assert logs[0]["new"] == {"shop_name": "Crunch Corner"}
