"""End-to-end FSM integration tests against a LIVE FluxVAI backend (:8001)."""
import asyncio
import base64
import uuid

import httpx
import pytest

from app import fsm, store
from app.config import get_settings
from app.fluxvai_client import FluxVAI
from tests.conftest import FakeWA

BASE = get_settings().fluxvai_base_url
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


def _inb(phone, *, text=None, sel=None, media_id=None, mime_type=None, wamid=None):
    mtype = "image" if media_id else ("interactive" if sel else "text")
    return {"phone": phone, "wamid": wamid or f"wamid.{uuid.uuid4().hex[:8]}",
            "type": mtype, "text": text, "selection_id": sel, "media_id": media_id, "mime_type": mime_type}


def _phone():
    return "9053" + f"{uuid.uuid4().int % 10**8:08d}"


def _bodies(wa):
    return [m.get("body", "") for m in wa.sent]


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


async def _new_user_code(backend):
    email = f"t_{uuid.uuid4().hex[:10]}@fluxvai.test"
    reg = await backend.post("/api/auth/register", json={"email": email, "password": "pw123456", "name": "Tester"})
    token = reg.json()["token"]
    lc = await backend.post("/api/whatsapp/link-code", headers={"Authorization": f"Bearer {token}"})
    return email, token, lc.json()["code"]


async def _link(wa, fx, backend, phone, use_case="skip", lang="tr"):
    _, token, code = await _new_user_code(backend)
    await fsm.handle_inbound(wa, fx, _inb(phone, text="başla"))          # → LANG_SELECT
    await fsm.handle_inbound(wa, fx, _inb(phone, sel=f"lang:{lang}"))    # → AWAITING_CODE
    await fsm.handle_inbound(wa, fx, _inb(phone, text=code))             # → ONBOARDING
    await fsm.handle_inbound(wa, fx, _inb(phone, sel=f"onb:{use_case}")) # → IDLE
    return token


async def test_language_first_then_link(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await fsm.handle_inbound(wa, fx, _inb(phone, text="selam"))
        assert store.get_session(phone)["state"] == "LANG_SELECT"
        assert any("language" in b.lower() or "dil" in b.lower() for b in _bodies(wa))

        _, _, code = await _new_user_code(backend)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="lang:tr"))
        assert any("6 haneli" in b for b in _bodies(wa))

        await fsm.handle_inbound(wa, fx, _inb(phone, text=code))
        assert store.get_session(phone)["state"] == "ONBOARDING"

        await fsm.handle_inbound(wa, fx, _inb(phone, sel="onb:creator"))
        assert store.get_session(phone)["state"] == "IDLE"
        assert any("merhaba" in b.lower() or "bakiye" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


async def test_english_language(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone, lang="en")
        assert store.get_session(phone)["context"]["lang"] == "en"
        assert any("welcome" in b.lower() or "create" in b.lower() for b in _bodies(wa))
        # language persists after a menu round-trip
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:balance"))
        assert any("balance" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


async def test_fast_create(backend):
    """Fast path: type → prompt → confirm (defaults applied, no platform/style/duration steps)."""
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:gen"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="type:video"))
        assert store.get_session(phone)["state"] == "GEN_PROMPT"  # straight to prompt
        await fsm.handle_inbound(wa, fx, _inb(phone, text="gün batımı drone çekimi"))
        assert store.get_session(phone)["state"] == "GEN_CONFIRM"  # straight to confirm
        gen = store.get_session(phone)["context"]["gen"]
        assert gen["platform"] == "Universal" and gen["style"] == "cinematic" and gen["duration"] == 30
        cost = await fx.cost_estimate({"type": "video", "duration": 30})  # real backend cost
        assert str(cost) in _bodies(wa)[-1]
    finally:
        await fx.client.aclose()


async def test_templates_via_keyword(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:gen"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="type:video"))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="şablon"))  # ask for templates
        assert store.get_session(phone)["state"] == "GEN_TEMPLATE"
        tmpl_id = next(r[0] for r in wa.sent[-1]["rows"] if r[0] != "tmpl:scratch")
        await fsm.handle_inbound(wa, fx, _inb(phone, sel=tmpl_id))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="tamam"))  # keep template prompt → confirm
        st = store.get_session(phone)
        assert st["state"] == "GEN_CONFIRM"
        assert st["context"]["gen"].get("template_id") == tmpl_id.split(":", 1)[1]
    finally:
        await fx.client.aclose()


async def test_detail_path(backend):
    """'⚙️ Detay' from confirm lets the user tweak platform/style/duration."""
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:gen"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="type:video"))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="bir tanıtım videosu"))
        assert store.get_session(phone)["state"] == "GEN_CONFIRM"
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="confirm:detail"))
        assert store.get_session(phone)["state"] == "GEN_PLATFORM"
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="plat:TikTok"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="style:realistic"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="dur:30"))
        st = store.get_session(phone)
        assert st["state"] == "GEN_CONFIRM"
        assert st["context"]["gen"]["platform"] == "TikTok" and st["context"]["gen"]["style"] == "realistic"
    finally:
        await fx.client.aclose()


async def test_custom_prompt_save(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:prompts"))
        assert store.get_session(phone)["state"] == "PROMPTS_MENU"
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="prompt:new"))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="Ürün Reklamı"))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="Minimal stüdyo, ürün 360 dönüş, premium ışık"))
        assert any("kaydedildi" in b.lower() for b in _bodies(wa))
        # appears in the refreshed prompt list
        assert any("Ürün Reklamı" in str(r) for r in wa.sent[-1]["rows"])
    finally:
        await fx.client.aclose()


async def test_command_alias_balance(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, text="/bakiye"))
        assert any("hesabım" in b.lower() or "toplam" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


async def test_buy_flow_lists_packages(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:buy"))
        assert store.get_session(phone)["state"] == "BUY_PACKAGE"
        assert any(r[0].startswith("pkg:") for r in wa.sent[-1]["rows"])
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="pkg:p2"))  # no Stripe key → graceful
        assert any("kullanılamıyor" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


async def test_image_edit_to_confirm(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone, use_case="ecommerce")
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:edit"))  # direct image-edit
        assert store.get_session(phone)["state"] == "GEN_IMG_AWAIT_PHOTO"
        await fsm.handle_inbound(wa, fx, _inb(phone, media_id="MID", mime_type="image/png", text="arka planı gece yap"))
        st = store.get_session(phone)
        assert st["state"] == "GEN_CONFIRM"
        assert st["context"]["gen"].get("source_media_url", "").startswith("http")
        assert "4" in _bodies(wa)[-1]  # image cost
    finally:
        await fx.client.aclose()


async def test_german_language(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone, lang="de")
        assert store.get_session(phone)["context"]["lang"] == "de"
        assert any("hallo" in b.lower() or "guthaben" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


async def test_repeat_last(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        token = await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:gen"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="type:video"))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="bir tanıtım videosu"))
        c0 = (await fx.me(token))["credits"]
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="confirm:yes"))
        c1 = (await fx.me(token))["credits"]
        cost = c0 - c1
        assert cost > 0  # a generation was charged
        assert store.get_session(phone)["context"].get("last_gen", {}).get("type") == "video"
        # one-tap repeat → another generation of the same cost, no wizard
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="act:repeat"))
        assert (await fx.me(token))["credits"] == c1 - cost
    finally:
        await fx.client.aclose()


async def test_gallery_categories(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        # create a video so the gallery has content
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:gen"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="type:video"))
        await fsm.handle_inbound(wa, fx, _inb(phone, text="klip"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="confirm:yes"))
        # gallery → category buttons
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:history"))
        rows = wa.sent[-1]["rows"]
        assert any(r[0] == "hist:video" for r in rows) and any(r[0] == "hist:all" for r in rows)
        # tap video category → real generation listed (backed by /api/generations?type=video)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="hist:video"))
        assert any("video" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


async def test_account_card(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        await _link(wa, fx, backend, phone)
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:balance"))
        assert any("hesabım" in b.lower() or "toplam" in b.lower() for b in _bodies(wa))
    finally:
        await fx.client.aclose()


@pytest.mark.slow
async def test_image_edit_completes_and_delivers(backend):
    phone = _phone()
    wa, fx = FakeWA(), FluxVAI(httpx.AsyncClient())
    try:
        token = await _link(wa, fx, backend, phone, use_case="ecommerce")
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="nav:edit"))
        await fsm.handle_inbound(wa, fx, _inb(phone, media_id="MID", mime_type="image/png", text="arka planı gece yap"))
        await fsm.handle_inbound(wa, fx, _inb(phone, sel="confirm:yes"))
        assert (await fx.me(token))["credits"] == 96
        for _ in range(40):
            await asyncio.sleep(2)
            if store.get_session(phone)["state"] == "IDLE":
                break
        assert store.get_session(phone)["state"] == "IDLE"
        assert any(m["kind"] == "image" for m in wa.sent)
    finally:
        await fx.client.aclose()
