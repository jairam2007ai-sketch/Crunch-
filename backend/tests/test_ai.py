import httpx

from app.ai import agent
from app.config import get_settings
from conftest import loaded, packet


def ask(client, headers, text):
    r = client.post("/api/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]})
    assert r.status_code == 200, r.text
    return r.json()


def test_basic_mode_answers_today_sales_from_real_numbers(client, owner):
    client.post("/api/orders", headers=owner, json={"items": [packet(), loaded()], "payment_method": "upi"})
    out = ask(client, owner, "What were today's sales?")
    assert out["mode"] == "basic"
    assert out["tools_used"][0]["tool"] == "get_today_sales"
    assert "₹118" in out["reply"]


def test_basic_mode_low_stock_and_help(client, owner):
    assert "isn't being counted" in ask(client, owner, "any low stock?")["reply"]
    assert "I can answer" in ask(client, owner, "tell me a joke")["reply"]


def test_refund_approval_needs_confirmation_once(client, owner, seller):
    order = client.post("/api/orders", headers=seller, json={"items": [packet()], "payment_method": "cash"}).json()
    client.post("/api/refunds", headers=seller,
                json={"order_id": order["id"], "amount": 49, "method": "cash", "reason": "Dropped it"})
    out = ask(client, owner, "approve the refund")
    assert len(out["pending_actions"]) == 1
    action = out["pending_actions"][0]
    assert "₹49" in action["summary"]
    # nothing happens until the owner confirms
    assert client.get("/api/refunds?status=pending", headers=owner).json()

    r = client.post("/api/ai/confirm", headers=owner, json={"action_token": action["action_token"]})
    assert r.status_code == 200, r.text
    assert client.get("/api/refunds?status=pending", headers=owner).json() == []
    assert client.post("/api/ai/confirm", headers=owner, json={"action_token": action["action_token"]}).status_code == 409


def test_tampered_action_is_rejected(client, owner):
    r = client.post("/api/ai/confirm", headers=owner, json={"action_token": "not-a-real-token"})
    assert r.status_code == 400


def test_close_online_ordering_via_assistant(client, owner):
    out = ask(client, owner, "close online orders")
    token = out["pending_actions"][0]["action_token"]
    client.post("/api/ai/confirm", headers=owner, json={"action_token": token})
    assert client.get("/api/menu").json()["shop"]["is_open"] is False


def test_model_mode_runs_tools(client, owner, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "ollama")
    client.post("/api/orders", headers=owner, json={"items": [packet()], "payment_method": "cash"})
    seen = []

    def fake_model(endpoint, messages, tools):
        seen.append(messages)
        if len(seen) == 1:
            return {"content": "", "tool_calls": [{"id": "c1", "type": "function",
                                                   "function": {"name": "get_today_sales", "arguments": "{}"}}]}
        tool_msg = messages[-1]
        assert tool_msg["role"] == "tool" and "₹49" in tool_msg["content"]
        return {"content": "You sold ₹49 today."}

    monkeypatch.setattr(agent, "call_model", fake_model)
    out = ask(client, owner, "sales today?")
    assert out["mode"] == "model" and out["model"] == "llama3.1"
    assert out["reply"] == "You sold ₹49 today."
    assert out["tools_used"] == [{"tool": "get_today_sales", "args": {}}]


def test_model_failure_falls_back_to_basic(client, owner, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_provider", "ollama")

    def broken(*a, **k):
        raise httpx.ConnectError("no ollama running")

    monkeypatch.setattr(agent, "call_model", broken)
    out = ask(client, owner, "today's sales")
    assert out["mode"] == "basic_fallback"
    assert out["reply"].startswith("(The AI model didn't answer")
