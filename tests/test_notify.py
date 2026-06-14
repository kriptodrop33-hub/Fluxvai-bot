"""Tests for the backend → bot /internal/notify push channel."""
from fastapi.testclient import TestClient

from app import store
from app.main import app
from tests.conftest import FakeWA

SECRET = "test-bot-secret-123"


def test_notify_credits_loaded_moves_to_idle():
    with TestClient(app) as client:
        fake = FakeWA()
        app.state.wa = fake  # override the real Graph client
        phone = "905770001111"
        # Pretend the user was waiting on payment.
        store.set_session(phone, "BUY_AWAIT_PAYMENT", {"jwt": "t", "user": {"name": "X", "credits": 100}})
        store.touch_last_inbound(phone)  # inside the 24h window

        r = client.post(
            "/internal/notify",
            headers={"X-Bot-Secret": SECRET},
            json={"phone": phone, "kind": "credits_loaded", "amount": 500, "new_balance": 600},
        )
        assert r.status_code == 200
        assert store.get_session(phone)["state"] == "IDLE"
        assert any("500" in m["body"] and "600" in m["body"] for m in fake.sent)


def test_notify_rejects_bad_secret():
    with TestClient(app) as client:
        app.state.wa = FakeWA()
        r = client.post(
            "/internal/notify",
            headers={"X-Bot-Secret": "wrong"},
            json={"phone": "900", "kind": "generic", "text": "hi"},
        )
        assert r.status_code == 401


def test_webhook_get_verification():
    with TestClient(app) as client:
        # correct verify token (conftest leaves default 'change-me-verify')
        from app.config import get_settings
        token = get_settings().wa_verify_token
        r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": "12345"})
        assert r.status_code == 200 and r.text == "12345"
        r2 = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "x"})
        assert r2.status_code == 403
