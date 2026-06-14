"""Telegram entrypoint: long-polling loop + a tiny /internal/notify server.

Reuses the shared FSM, store, i18n, tasks and the FluxVAI bridge (channel='telegram').
No public URL needed — Telegram is polled via getUpdates.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import fsm, notify, store, tasks, telegram
from .config import get_settings
from .fluxvai_client import FluxVAI


async def _poll_loop(app: FastAPI) -> None:
    s = get_settings()
    wa, fx = app.state.wa, app.state.fx
    log = logging.getLogger("bot.telegram")
    offset = None
    log.info("Telegram long-polling started")
    while not app.state.stop:
        try:
            body = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
            if offset is not None:
                body["offset"] = offset
            r = await app.state.client.post(f"{s.telegram_api}/getUpdates", json=body, timeout=40)
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                inbound = telegram.parse_update(upd)
                if not inbound or not inbound.get("phone"):
                    continue
                if not store.mark_seen(inbound["wamid"]):
                    continue
                if inbound.get("_callback_id"):
                    await wa.answer_callback(inbound["_callback_id"])
                store.touch_last_inbound(inbound["phone"])
                asyncio.create_task(fsm.handle_inbound(wa, fx, inbound))
        except Exception as e:  # noqa: BLE001
            log.warning("poll loop error: %s", e)
            await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logging.basicConfig(level=getattr(logging, s.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    store.init(s.telegram_db_path)  # separate DB → chat_id keys never collide with WA phones

    app.state.client = httpx.AsyncClient()
    app.state.wa = telegram.Telegram(app.state.client)
    app.state.fx = FluxVAI(app.state.client, channel="telegram")
    app.state.stop = False

    log = logging.getLogger("bot.telegram")
    try:
        me = await app.state.client.get(f"{s.telegram_api}/getMe", timeout=15)
        log.info("Telegram bot: @%s", (me.json().get("result") or {}).get("username", "?"))
    except Exception as e:  # noqa: BLE001
        log.warning("getMe failed: %s", e)

    await app.state.wa.setup()  # command menu, menu button, descriptions
    await tasks.resume_pending(app.state.wa, app.state.fx)
    poller = asyncio.create_task(_poll_loop(app))
    try:
        yield
    finally:
        app.state.stop = True
        poller.cancel()
        await app.state.client.aclose()


app = FastAPI(title="FluxVAI Telegram Bot", lifespan=lifespan)
app.include_router(notify.router)  # backend Stripe webhook → credits-loaded push


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "fluxvai-telegram-bot"})


if __name__ == "__main__":
    import os

    import uvicorn

    s = get_settings()
    port = int(os.getenv("PORT") or s.telegram_bot_port)
    uvicorn.run("app.telegram_main:app", host="0.0.0.0", port=port, log_level=s.log_level.lower())
