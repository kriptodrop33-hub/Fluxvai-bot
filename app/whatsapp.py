"""WhatsApp Cloud API client (sending) + inbound payload parsing."""
import logging

import httpx

from .config import get_settings

log = logging.getLogger("bot.whatsapp")


class WhatsApp:
    """Thin async wrapper over Graph API POST /{phone_number_id}/messages.

    Every send is best-effort: failures are logged, never raised into the
    webhook path (a raise there would make Meta retry the whole delivery).
    """

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.s = get_settings()

    async def _send(self, payload: dict) -> httpx.Response | None:
        body = {"messaging_product": "whatsapp", "recipient_type": "individual", **payload}
        headers = {
            "Authorization": f"Bearer {self.s.wa_access_token}",
            "Content-Type": "application/json",
        }
        try:
            r = await self.client.post(self.s.messages_url, headers=headers, json=body, timeout=20)
            if r.status_code >= 400:
                log.warning("WA send failed %s: %s", r.status_code, r.text[:500])
            return r
        except Exception as e:  # noqa: BLE001
            log.warning("WA send error: %s", e)
            return None

    async def send_text(self, to: str, text: str) -> httpx.Response | None:
        return await self._send({"to": to, "type": "text", "text": {"preview_url": True, "body": text[:4096]}})

    async def send_buttons(self, to: str, body: str, buttons: list[tuple[str, str]]) -> httpx.Response | None:
        """buttons: list of (id, title); WhatsApp allows at most 3 reply buttons."""
        rows = [{"type": "reply", "reply": {"id": bid, "title": title[:20]}} for bid, title in buttons[:3]]
        return await self._send({
            "to": to,
            "type": "interactive",
            "interactive": {"type": "button", "body": {"text": body[:1024]}, "action": {"buttons": rows}},
        })

    async def send_list(
        self, to: str, body: str, button_text: str, rows: list[tuple[str, str, str]], section_title: str = "Seçenekler"
    ) -> httpx.Response | None:
        """rows: list of (id, title, description); at most 10 rows per section."""
        section_rows = [
            {"id": rid, "title": title[:24], "description": (desc or "")[:72]} for rid, title, desc in rows[:10]
        ]
        return await self._send({
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body[:1024]},
                "action": {"button": button_text[:20], "sections": [{"title": section_title[:24], "rows": section_rows}]},
            },
        })

    async def send_template(self, to: str, name: str, lang: str = "tr", components: list | None = None) -> httpx.Response | None:
        tpl: dict = {"name": name, "language": {"code": lang}}
        if components:
            tpl["components"] = components
        return await self._send({"to": to, "type": "template", "template": tpl})

    async def send_image(self, to: str, link: str, caption: str | None = None) -> httpx.Response | None:
        """Send an image by public URL. (Outbound media needs a publicly fetchable HTTPS link.)"""
        img: dict = {"link": link}
        if caption:
            img["caption"] = caption[:1024]
        return await self._send({"to": to, "type": "image", "image": img})

    async def download_media(self, media_id: str) -> tuple[bytes, str]:
        """Two-step Meta Graph fetch: media_id → short-lived URL → binary bytes."""
        hdr = {"Authorization": f"Bearer {self.s.wa_access_token}"}
        r1 = await self.client.get(f"{self.s.graph_base}/{media_id}", headers=hdr, timeout=20)
        r1.raise_for_status()
        info = r1.json()
        r2 = await self.client.get(info["url"], headers=hdr, timeout=30)
        r2.raise_for_status()
        return r2.content, info.get("mime_type") or "image/jpeg"


def parse_inbound(value: dict) -> dict | None:
    """Normalize a Meta webhook 'value' object into a single inbound message.

    Returns {phone, wamid, type, text, selection_id} or None for non-message
    events (delivery/read statuses, etc.).
    """
    msgs = value.get("messages") or []
    if not msgs:
        return None
    m = msgs[0]
    mtype = m.get("type")
    text: str | None = None
    selection_id: str | None = None
    media_id: str | None = None
    mime_type: str | None = None

    if mtype == "text":
        text = (m.get("text") or {}).get("body")
    elif mtype == "interactive":
        inter = m.get("interactive") or {}
        if inter.get("type") == "button_reply":
            br = inter.get("button_reply") or {}
            selection_id, text = br.get("id"), br.get("title")
        elif inter.get("type") == "list_reply":
            lr = inter.get("list_reply") or {}
            selection_id, text = lr.get("id"), lr.get("title")
    elif mtype == "button":  # quick-reply on a template message
        b = m.get("button") or {}
        text, selection_id = b.get("text"), b.get("payload")
    elif mtype in ("image", "document", "video", "audio", "sticker"):
        media = m.get(mtype) or {}
        media_id = media.get("id")
        mime_type = media.get("mime_type")
        text = media.get("caption")  # caption (if any) doubles as the prompt

    return {
        "phone": m.get("from"),
        "wamid": m.get("id"),
        "type": mtype,
        "text": text,
        "selection_id": selection_id,
        "media_id": media_id,
        "mime_type": mime_type,
    }
