"""Backend → bot push channel. The FluxVAI Stripe webhook calls this after a
successful payment so the user gets a 'credits loaded' message on WhatsApp."""
import logging
import time

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import i18n, store
from .config import get_settings
from .security import check_internal_secret

log = logging.getLogger("bot.notify")
router = APIRouter()

# WhatsApp only allows free-form messages within 24h of the user's last inbound.
_WINDOW_SECS = 24 * 60 * 60


class NotifyBody(BaseModel):
    phone: str
    kind: str = "generic"
    text: str | None = None
    amount: int | None = None
    new_balance: int | None = None


@router.post("/internal/notify")
async def notify(body: NotifyBody, request: Request, x_bot_secret: str | None = Header(None, alias="X-Bot-Secret")):
    s = get_settings()
    if not check_internal_secret(s.bot_service_secret, x_bot_secret):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    wa = request.app.state.wa
    phone = "".join(ch for ch in body.phone if ch.isdigit())

    sess = store.get_session(phone)
    lang = sess["context"].get("lang", "tr")
    if body.kind == "credits_loaded":
        text = i18n.credits_loaded(lang, body.amount, body.new_balance)
        # Move the user out of the waiting state (keep auth + lang).
        ctx = {k: sess["context"][k] for k in ("jwt", "user", "use_case", "lang") if k in sess["context"]}
        store.set_session(phone, "IDLE", ctx)
    else:
        text = body.text or ""

    within_window = (time.time() - store.get_last_inbound(phone)) < _WINDOW_SECS
    if within_window:
        await wa.send_text(phone, text)
    else:
        # Outside the 24h window a free-form message is blocked by Meta; an
        # approved template is required. Configure 'payment_confirmation' in
        # Meta and switch this to send_template once approved.
        log.warning("phone %s outside 24h window — needs approved template for push", phone)
        await wa.send_text(phone, text)  # best-effort; will fail silently if blocked

    return JSONResponse({"status": "ok"})
