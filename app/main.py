"""FastAPI entrypoint for the FluxVAI WhatsApp bot."""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import notify, store, tasks, webhook
from .config import get_settings
from .fluxvai_client import FluxVAI
from .whatsapp import WhatsApp


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logging.basicConfig(level=getattr(logging, s.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    store.init(s.bot_db_path)

    app.state.client = httpx.AsyncClient()
    app.state.wa = WhatsApp(app.state.client)
    app.state.fx = FluxVAI(app.state.client)

    # Re-arm any generations that were still polling when we last stopped.
    await tasks.resume_pending(app.state.wa, app.state.fx)

    logging.getLogger("bot").info("FluxVAI WhatsApp bot up on :%s", s.bot_port)
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(title="FluxVAI WhatsApp Bot", lifespan=lifespan)
app.include_router(webhook.router)
app.include_router(notify.router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "fluxvai-wa-bot"})


if __name__ == "__main__":
    import os

    import uvicorn

    s = get_settings()
    port = int(os.getenv("PORT") or s.bot_port)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level=s.log_level.lower())
