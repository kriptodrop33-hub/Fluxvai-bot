"""Telegram Bot API adapter — same sender interface as the WhatsApp class,
so it plugs straight into the shared FSM. Uses long polling (no public URL)."""
import logging

import httpx

from .config import get_settings

log = logging.getLogger("bot.telegram")

_EXT_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}


def _plain(text: str) -> str:
    """Telegram chokes on stray Markdown; drop the * bold markers, send clean text."""
    return (text or "").replace("*", "")


class Telegram:
    """Outbound + media for Telegram. Inline keyboards replace WhatsApp buttons/lists
    (Telegram has no 3-button / 10-row caps, so everything maps cleanly)."""

    channel = "telegram"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.s = get_settings()

    async def _call(self, method: str, payload: dict) -> httpx.Response | None:
        try:
            r = await self.client.post(f"{self.s.telegram_api}/{method}", json=payload, timeout=20)
            if r.status_code >= 400:
                log.warning("TG %s failed %s: %s", method, r.status_code, r.text[:400])
            return r
        except Exception as e:  # noqa: BLE001
            log.warning("TG %s error: %s", method, e)
            return None

    @staticmethod
    def _keyboard(rows, cols: int = 2) -> dict:
        """Inline keyboard as a grid: ≤3 items → one row; otherwise `cols` per row."""
        btns = [{"text": _plain(r[1])[:64], "callback_data": r[0][:64]} for r in rows]
        grid = [btns] if len(btns) <= 3 else [btns[i:i + cols] for i in range(0, len(btns), cols)]
        return {"inline_keyboard": grid}

    async def setup(self) -> None:
        """One-time profile polish: command menu, menu button, descriptions."""
        try:
            from . import i18n
            await self._call("setMyCommands", {"commands": i18n.bot_commands("en")})
            await self._call("setMyCommands", {"commands": i18n.bot_commands("tr"), "language_code": "tr"})
            await self._call("setChatMenuButton", {"menu_button": {"type": "commands"}})
            await self._call("setMyShortDescription", {"short_description": i18n.bot_about("en")[:120]})
            await self._call("setMyShortDescription", {"short_description": i18n.bot_about("tr")[:120], "language_code": "tr"})
            await self._call("setMyDescription", {"description": i18n.bot_about("en")})
        except Exception as e:  # noqa: BLE001
            log.warning("telegram setup failed: %s", e)

    async def send_text(self, to, text) -> httpx.Response | None:
        return await self._call("sendMessage", {"chat_id": to, "text": _plain(text)[:4096], "disable_web_page_preview": False})

    async def send_buttons(self, to, body, buttons) -> httpx.Response | None:
        return await self._call("sendMessage", {"chat_id": to, "text": _plain(body)[:4096], "reply_markup": self._keyboard(buttons)})

    async def send_list(self, to, body, button_text, rows, section_title="") -> httpx.Response | None:
        return await self._call("sendMessage", {"chat_id": to, "text": _plain(body)[:4096], "reply_markup": self._keyboard(rows)})

    async def send_image(self, to, link, caption=None) -> httpx.Response | None:
        payload = {"chat_id": to, "photo": link}
        if caption:
            payload["caption"] = _plain(caption)[:1024]
        return await self._call("sendPhoto", payload)

    async def send_template(self, to, name, lang="tr", components=None) -> httpx.Response | None:
        # Telegram has no 24h window / templates; just send text.
        return await self.send_text(to, name)

    async def answer_callback(self, callback_id: str) -> None:
        await self._call("answerCallbackQuery", {"callback_query_id": callback_id})

    async def download_media(self, file_id: str) -> tuple[bytes, str]:
        r1 = await self.client.get(f"{self.s.telegram_api}/getFile", params={"file_id": file_id}, timeout=20)
        r1.raise_for_status()
        file_path = r1.json()["result"]["file_path"]
        r2 = await self.client.get(f"{self.s.telegram_file_api}/{file_path}", timeout=30)
        r2.raise_for_status()
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "jpg"
        return r2.content, _EXT_MIME.get(ext, "image/jpeg")


def parse_update(update: dict) -> dict | None:
    """Normalize a Telegram update into the shared inbound shape.

    Identity key (`phone`) = chat id. Button taps arrive as callback_query.data.
    """
    if "callback_query" in update:
        cq = update["callback_query"]
        chat = ((cq.get("message") or {}).get("chat") or {}).get("id") or (cq.get("from") or {}).get("id")
        return {
            "phone": str(chat), "wamid": f"tg.cb.{cq.get('id')}", "type": "interactive",
            "text": None, "selection_id": cq.get("data"), "media_id": None, "mime_type": None,
            "_callback_id": cq.get("id"),
        }

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return None
    chat = (msg.get("chat") or {}).get("id")
    base = {"phone": str(chat), "wamid": f"tg.{update.get('update_id')}", "type": "text",
            "text": None, "selection_id": None, "media_id": None, "mime_type": None}

    if "text" in msg:
        base["text"] = msg["text"]
    elif "photo" in msg:
        photos = msg["photo"] or []
        if photos:
            base["type"] = "image"
            base["media_id"] = photos[-1]["file_id"]  # largest size
            base["mime_type"] = "image/jpeg"
            base["text"] = msg.get("caption")
    elif "document" in msg and (msg["document"].get("mime_type", "").startswith("image/")):
        base["type"] = "image"
        base["media_id"] = msg["document"]["file_id"]
        base["mime_type"] = msg["document"].get("mime_type", "image/jpeg")
        base["text"] = msg.get("caption")
    else:
        return None
    return base
