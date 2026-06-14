"""Telegram adapter unit tests + an end-to-end flow over the generic bridge."""
import uuid

import httpx
import pytest

from app import fsm, store
from app.config import get_settings
from app.fluxvai_client import FluxVAI
from app.telegram import parse_update
from tests.conftest import FakeWA

BASE = get_settings().fluxvai_base_url


# ── parser unit tests (no network) ────────────────────────────────────
def test_parse_text():
    u = {"update_id": 7, "message": {"chat": {"id": 123}, "text": "merhaba"}}
    m = parse_update(u)
    assert m["phone"] == "123" and m["text"] == "merhaba" and m["type"] == "text" and m["selection_id"] is None


def test_parse_callback():
    u = {"update_id": 8, "callback_query": {"id": "cb1", "data": "nav:gen", "message": {"chat": {"id": 55}}}}
    m = parse_update(u)
    assert m["phone"] == "55" and m["selection_id"] == "nav:gen" and m["_callback_id"] == "cb1"


def test_parse_photo():
    u = {"update_id": 9, "message": {"chat": {"id": 7}, "photo": [{"file_id": "small"}, {"file_id": "big"}], "caption": "düzenle"}}
    m = parse_update(u)
    assert m["type"] == "image" and m["media_id"] == "big" and m["text"] == "düzenle"


def test_parse_ignores_other():
    assert parse_update({"update_id": 10, "my_chat_member": {}}) is None


# ── end-to-end flow over the generic (channel) bridge ─────────────────
def _inb(chat, *, text=None, sel=None, media_id=None, mime_type=None):
    mtype = "image" if media_id else ("interactive" if sel else "text")
    return {"phone": str(chat), "wamid": f"tg.{uuid.uuid4().hex[:8]}", "type": mtype,
            "text": text, "selection_id": sel, "media_id": media_id, "mime_type": mime_type}


@pytest.fixture(scope="module", autouse=True)
def _init_store():
    store.init(get_settings().bot_db_path)


@pytest.fixture
async def backend():
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:
        try:
            await c.get("/api/credits/packages")
        except Exception:
            pytest.skip("FluxVAI backend not reachable on :8001")
        yield c


async def test_telegram_link_and_fast_create(backend):
    chat = str(uuid.uuid4().int % 10**9)
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient(), channel="telegram")
    try:
        # new account + shared link code
        email = f"tg_{uuid.uuid4().hex[:8]}@fluxvai.test"
        reg = await backend.post("/api/auth/register", json={"email": email, "password": "pw123456", "name": "TG"})
        token = reg.json()["token"]
        code = (await backend.post("/api/whatsapp/link-code", headers={"Authorization": f"Bearer {token}"})).json()["code"]

        await fsm.handle_inbound(wa, fx, _inb(chat, text="/start"))      # → LANG_SELECT
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="lang:tr"))      # → resolve(telegram) 404 → AWAITING_CODE
        await fsm.handle_inbound(wa, fx, _inb(chat, text=code))          # → bind (generic) → ONBOARDING
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="onb:skip"))     # → IDLE
        assert store.get_session(chat)["state"] == "IDLE"

        # resolve now works via the generic bridge (channel=telegram)
        data = await fx.resolve(chat)
        assert data["user"]["email"] == email

        # fast create
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="nav:gen"))
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="type:image"))
        assert store.get_session(chat)["state"] == "GEN_PROMPT"
        await fsm.handle_inbound(wa, fx, _inb(chat, text="neon şehir posteri"))
        assert store.get_session(chat)["state"] == "GEN_CONFIRM"
        assert "4" in [m.get("body", "") for m in wa.sent][-1]  # image cost
    finally:
        await fx.client.aclose()


async def test_telegram_rich_menu(backend):
    chat = str(uuid.uuid4().int % 10**9)
    wa, fx = FakeWA(channel="telegram"), FluxVAI(httpx.AsyncClient(), channel="telegram")
    try:
        email = f"tg_{uuid.uuid4().hex[:8]}@fluxvai.test"
        reg = await backend.post("/api/auth/register", json={"email": email, "password": "pw123456", "name": "TG"})
        token = reg.json()["token"]
        code = (await backend.post("/api/whatsapp/link-code", headers={"Authorization": f"Bearer {token}"})).json()["code"]
        await fsm.handle_inbound(wa, fx, _inb(chat, text="/start"))
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="lang:tr"))
        await fsm.handle_inbound(wa, fx, _inb(chat, text=code))
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="onb:skip"))
        # rich Telegram menu: many buttons incl. direct type shortcuts
        menus = [m for m in wa.sent if m["kind"] == "buttons"]
        btns = menus[-1]["buttons"]
        assert len(btns) >= 10
        assert any(b[0] == "type:video" for b in btns) and any(b[0] == "nav:history" for b in btns)
        # tapping a type shortcut from the menu jumps straight into the prompt step
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="type:image"))
        assert store.get_session(chat)["state"] == "GEN_PROMPT"
    finally:
        await fx.client.aclose()


async def test_telegram_image_edit_to_confirm(backend):
    chat = str(uuid.uuid4().int % 10**9)
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient(), channel="telegram")
    try:
        email = f"tg_{uuid.uuid4().hex[:8]}@fluxvai.test"
        reg = await backend.post("/api/auth/register", json={"email": email, "password": "pw123456", "name": "TG"})
        token = reg.json()["token"]
        code = (await backend.post("/api/whatsapp/link-code", headers={"Authorization": f"Bearer {token}"})).json()["code"]
        await fsm.handle_inbound(wa, fx, _inb(chat, text="/start"))
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="lang:tr"))
        await fsm.handle_inbound(wa, fx, _inb(chat, text=code))
        await fsm.handle_inbound(wa, fx, _inb(chat, sel="onb:skip"))

        await fsm.handle_inbound(wa, fx, _inb(chat, sel="nav:edit"))
        assert store.get_session(chat)["state"] == "GEN_IMG_AWAIT_PHOTO"
        # FakeWA.download_media returns a 1x1 PNG; fx.upload hits the generic /internal/link/upload
        await fsm.handle_inbound(wa, fx, _inb(chat, media_id="FILE1", mime_type="image/png", text="arka planı gece yap"))
        st = store.get_session(chat)
        assert st["state"] == "GEN_CONFIRM"
        assert st["context"]["gen"].get("source_media_url", "").startswith("http")
    finally:
        await fx.client.aclose()
