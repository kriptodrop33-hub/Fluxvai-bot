"""Meta WhatsApp webhook: GET verification + POST inbound."""
import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from . import fsm, store
from .config import get_settings
from .security import verify_meta_signature
from .whatsapp import parse_inbound

log = logging.getLogger("bot.webhook")
router = APIRouter()


@router.get("/webhook")
async def verify(request: Request):
    s = get_settings()
    qp = request.query_params
    if qp.get("hub.mode") == "subscribe" and qp.get("hub.verify_token") == s.wa_verify_token:
        return PlainTextResponse(qp.get("hub.challenge", ""))
    return PlainTextResponse("forbidden", status_code=403)


@router.post("/webhook")
async def receive(request: Request):
    s = get_settings()
    raw = await request.body()

    if not verify_meta_signature(s.wa_app_secret, raw, request.headers.get("X-Hub-Signature-256")):
        log.warning("rejected webhook: bad signature")
        return PlainTextResponse("forbidden", status_code=403)

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"status": "ignored"})

    wa = request.app.state.wa
    fx = request.app.state.fx

    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            inbound = parse_inbound(value)
            if not inbound or not inbound.get("phone"):
                continue  # status update or non-message event
            # Idempotency: WhatsApp re-delivers on slow/missing 200.
            if not store.mark_seen(inbound.get("wamid")):
                log.info("duplicate wamid %s — skipping", inbound.get("wamid"))
                continue
            store.touch_last_inbound(inbound["phone"])
            # Return 200 fast; do the slow work off the request path.
            asyncio.create_task(fsm.handle_inbound(wa, fx, inbound))

    return JSONResponse({"status": "ok"})
