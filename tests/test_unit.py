"""Fast unit tests — no network."""
from app import store
from app.security import check_internal_secret, verify_meta_signature
from app.whatsapp import parse_inbound


def test_meta_signature_roundtrip():
    import hashlib
    import hmac

    secret = "abc123"
    body = b'{"hello":"world"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_meta_signature(secret, body, sig) is True
    assert verify_meta_signature(secret, body, "sha256=deadbeef") is False
    assert verify_meta_signature(secret, body, None) is False
    # No secret configured → dev passthrough.
    assert verify_meta_signature("", body, None) is True


def test_internal_secret():
    assert check_internal_secret("s3cr3t", "s3cr3t") is True
    assert check_internal_secret("s3cr3t", "wrong") is False
    assert check_internal_secret("", "anything") is False
    assert check_internal_secret("s3cr3t", None) is False


def test_parse_text():
    value = {"messages": [{"from": "905551112233", "id": "wamid.AA", "type": "text", "text": {"body": "merhaba"}}]}
    m = parse_inbound(value)
    assert m["phone"] == "905551112233" and m["wamid"] == "wamid.AA"
    assert m["type"] == "text" and m["text"] == "merhaba" and m["selection_id"] is None
    assert m["media_id"] is None and m["mime_type"] is None


def test_parse_image():
    value = {"messages": [{"from": "90555", "id": "wamid.IMG", "type": "image",
                            "image": {"id": "MEDIA42", "mime_type": "image/jpeg", "caption": "şunu düzenle"}}]}
    m = parse_inbound(value)
    assert m["type"] == "image" and m["media_id"] == "MEDIA42"
    assert m["mime_type"] == "image/jpeg" and m["text"] == "şunu düzenle"


def test_parse_button_reply():
    value = {"messages": [{"from": "905551112233", "id": "wamid.BB", "type": "interactive",
                            "interactive": {"type": "button_reply", "button_reply": {"id": "nav:gen", "title": "Üret"}}}]}
    m = parse_inbound(value)
    assert m["selection_id"] == "nav:gen" and m["type"] == "interactive"


def test_parse_status_event_is_none():
    assert parse_inbound({"statuses": [{"id": "x", "status": "delivered"}]}) is None


def test_store_dedupe_and_session(tmp_path):
    store.init(str(tmp_path / "s.sqlite3"))
    assert store.mark_seen("wamid.1") is True
    assert store.mark_seen("wamid.1") is False  # duplicate
    store.set_session("90555", "IDLE", {"jwt": "t", "user": {"name": "A"}})
    s = store.get_session("90555")
    assert s["state"] == "IDLE" and s["context"]["jwt"] == "t"
    store.add_pending("gen_1", "90555", "jwt1")
    assert any(r["gen_id"] == "gen_1" for r in store.list_pending())
    store.complete_pending("gen_1")
    assert not any(r["gen_id"] == "gen_1" for r in store.list_pending())
