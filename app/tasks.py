"""Background generation polling + delivery. No import of fsm (one-way dep)."""
import asyncio
import logging
import time

import httpx

from . import i18n, store
from .config import get_settings

log = logging.getLogger("bot.tasks")


def _reset_idle(phone: str) -> None:
    sess = store.get_session(phone)
    ctx = sess["context"]
    keep = {k: ctx[k] for k in ("jwt", "user") if k in ctx}
    store.set_session(phone, "IDLE", keep)


async def poll_and_deliver(wa, fx, phone: str, jwt: str, gen_id: str) -> None:
    """Poll a generation until completed/failed, then message the user.

    The mock backend completes lazily (~28s after creation, only when polled),
    so we keep polling at POLL_INTERVAL until POLL_TIMEOUT.
    """
    s = get_settings()
    deadline = time.time() + s.poll_timeout_secs
    try:
        while time.time() < deadline:
            await asyncio.sleep(s.poll_interval_secs)
            try:
                g = await fx.poll(jwt, gen_id)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    try:
                        data = await fx.resolve(phone)
                        jwt = data["token"]
                        continue
                    except Exception:  # noqa: BLE001
                        break
                if e.response.status_code == 404:
                    break
                raise
            status = g.get("status")
            lang = store.get_session(phone)["context"].get("lang", "tr")
            if status == "completed":
                out = g.get("output_url")
                delivered = False
                if g.get("type") == "image" and out and str(out).startswith("http"):
                    resp = await wa.send_image(phone, out, caption=i18n.gen_done_caption(lang, g.get("credits_used")))
                    delivered = resp is not None and getattr(resp, "status_code", 500) < 400
                if not delivered:
                    await wa.send_text(phone, i18n.gen_done(lang, g.get("type"), g.get("credits_used"), out))
                store.complete_pending(gen_id)
                _reset_idle(phone)
                try:  # fast next-step buttons: 🔁 Repeat / 🎬 New / 📋 Menu
                    await wa.send_buttons(phone, i18n.t(lang, "quick_after"), i18n.quick_actions(lang))
                except Exception:  # noqa: BLE001
                    pass
                return
            if status == "failed":
                await wa.send_text(phone, i18n.t(lang, "gen_failed"))
                store.complete_pending(gen_id)
                _reset_idle(phone)
                return
        # Timed out — leave the pending row so resume_pending can re-check later.
        lang = store.get_session(phone)["context"].get("lang", "tr")
        await wa.send_text(phone, i18n.t(lang, "gen_timeout"))
        _reset_idle(phone)
    except Exception as e:  # noqa: BLE001
        log.warning("poll_and_deliver error (%s): %s", gen_id, e)


async def resume_pending(wa, fx) -> None:
    """On startup, re-arm polling for generations that hadn't been delivered."""
    pending = store.list_pending()
    if pending:
        log.info("resuming %d pending generation(s)", len(pending))
    for row in pending:
        asyncio.create_task(poll_and_deliver(wa, fx, row["phone"], row["jwt"], row["gen_id"]))
