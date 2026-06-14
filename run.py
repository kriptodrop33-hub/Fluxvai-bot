"""Single entrypoint for cloud hosts (Railway/Render/etc.).

Both bot channels share this command — they differ only by the BOT_MODE env:
  BOT_MODE=telegram  → Telegram long-polling bot (default)
  BOT_MODE=whatsapp  → WhatsApp Cloud API webhook bot

Binds to $PORT (injected by Railway) or the per-mode config default.
"""
import os

import uvicorn

from app.config import get_settings


def main() -> None:
    s = get_settings()
    mode = os.getenv("BOT_MODE", "telegram").strip().lower()
    target = "app.telegram_main:app" if mode == "telegram" else "app.main:app"
    default_port = s.telegram_bot_port if mode == "telegram" else s.bot_port
    port = int(os.getenv("PORT") or default_port)
    print(f"▶ FluxVAI bot starting · mode={mode} · port={port}")
    uvicorn.run(target, host="0.0.0.0", port=port, log_level=s.log_level.lower())


if __name__ == "__main__":
    main()
