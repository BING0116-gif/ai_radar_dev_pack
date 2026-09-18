"""API tests for the subscription settings endpoints (CARD-004)."""

UNIFIED_KEYS = {"code", "message", "data"}


def _subscription_payload(**overrides):
    payload = {
        "max_items": 5,
        "topics": ["AI Coding", "MCP"],
        "keywords": ["Claude"],
        "excluded_keywords": ["spam", "spam"],
        "language": "zh-CN",
        "notification_channel": "email",
        "enabled": True,
        "timezone": "Asia/Shanghai",
    }
    payload.update(overrides)
    return payload


def test_new_user_can_save_subscription(client):
    resp = client.put("/api/subscription", json=_subscription_payload(max_items=8))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["max_items"] == 8
    assert body["data"]["topics"] == ["AI Coding", "MCP"]


def test_update_then_read_is_consistent(client):
    client.put("/api/subscription", json=_subscription_payload(topics=["A"]))
    resp = client.put("/api/subscription", json=_subscription_payload(topics=["A", "B"], max_items=12))
    assert resp.json()["data"]["topics"] == ["A", "B"]
    assert resp.json()["data"]["max_items"] == 12

    read = client.get("/api/subscription")
    data = read.json()["data"]
    assert data["topics"] == ["A", "B"]
    assert data["max_items"] == 12


def test_topics_stripped_and_deduplicated(client):
    resp = client.put(
        "/api/subscription",
        json=_subscription_payload(topics=["  Alpha  ", "beta", "alpha"]),
    )
    assert resp.json()["data"]["topics"] == ["Alpha", "beta", "alpha"]  # case preserved


def test_excluded_keywords_deduped_and_stripped(client):
    resp = client.put(
        "/api/subscription",
        json=_subscription_payload(excluded_keywords=[" spam ", "spam", "  ", ""]),
    )
    assert resp.json()["data"]["excluded_keywords"] == ["spam"]


def test_defaults_applied(client):
    resp = client.get("/api/subscription")
    data = resp.json()["data"]
    assert data["timezone"] == "Asia/Shanghai"
    assert data["language"] == "zh-CN"
    assert data["max_items"] == 5


def test_invalid_max_items_returns_unified_error(client):
    resp = client.put("/api/subscription", json=_subscription_payload(max_items=21))
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 42200
    assert "data" in body
    assert UNIFIED_KEYS == set(body.keys())


def test_zero_and_too_small_max_items_rejected(client):
    for bad in (0, -1):
        resp = client.put("/api/subscription", json=_subscription_payload(max_items=bad))
        assert resp.status_code == 422
        assert resp.json()["code"] == 42200


def test_response_format_is_unified(client):
    resp = client.get("/api/subscription")
    assert UNIFIED_KEYS == set(resp.json().keys())


def test_role_is_persisted(client):
    resp = client.put("/api/subscription", json=_subscription_payload(role="AI Researcher"))
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "AI Researcher"
    read = client.get("/api/subscription")
    assert read.json()["data"]["role"] == "AI Researcher"