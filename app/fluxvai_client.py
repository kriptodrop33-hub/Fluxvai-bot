"""Async HTTP client for the FluxVAI backend (bridge + reused /api endpoints)."""
import base64
import logging

import httpx

from .config import get_settings

log = logging.getLogger("bot.fluxvai")

# Mirror of backend CREDIT_COST. The backend's /api/cost-estimate ignores the
# request body and always returns 15, so we compute cost locally instead.
CREDIT_COST = {"video": 15, "image": 4, "audio": 5, "3d": 25}

# Generation types offered in the wizard, with WhatsApp-friendly Turkish labels.
GEN_TYPES = [
    ("video", "🎬 Video", "Sosyal medya videosu"),
    ("image", "🖼️ Görsel", "Tek kare görsel/poster"),
    ("audio", "🎵 Ses", "Seslendirme / müzik"),
    ("3d", "📦 3D Model", "3B model / render"),
]


class NotLinked(Exception):
    """Raised when a phone has no verified FluxVAI account."""


class FluxVAI:
    def __init__(self, client: httpx.AsyncClient, channel: str = "whatsapp"):
        self.client = client
        self.s = get_settings()
        self.channel = channel  # "whatsapp" → /internal/wa/*, anything else → /internal/link/*

    def _u(self, path: str) -> str:
        return f"{self.s.fluxvai_base_url}{path}"

    def _bot_headers(self) -> dict:
        return {"X-Bot-Secret": self.s.bot_service_secret}

    @staticmethod
    def _auth(jwt: str) -> dict:
        return {"Authorization": f"Bearer {jwt}"}

    @property
    def _is_wa(self) -> bool:
        return self.channel == "whatsapp"

    # ── bridge (X-Bot-Secret). ext_id = phone (WA) or chat_id (Telegram). ──
    async def resolve(self, ext_id) -> dict:
        if self._is_wa:
            r = await self.client.post(self._u("/internal/wa/resolve"), headers=self._bot_headers(), json={"phone": ext_id}, timeout=15)
        else:
            r = await self.client.post(self._u("/internal/link/resolve"), headers=self._bot_headers(), json={"channel": self.channel, "ext_id": str(ext_id)}, timeout=15)
        if r.status_code == 404:
            raise NotLinked()
        r.raise_for_status()
        return r.json()

    async def link(self, ext_id, code: str) -> httpx.Response:
        if self._is_wa:
            return await self.client.post(self._u("/internal/wa/link"), headers=self._bot_headers(), json={"phone": ext_id, "code": code}, timeout=15)
        return await self.client.post(self._u("/internal/link/bind"), headers=self._bot_headers(), json={"channel": self.channel, "ext_id": str(ext_id), "code": code}, timeout=15)

    async def checkout(self, ext_id, package_id: str) -> httpx.Response:
        if self._is_wa:
            return await self.client.post(self._u("/internal/wa/checkout"), headers=self._bot_headers(), json={"phone": ext_id, "package_id": package_id}, timeout=20)
        return await self.client.post(self._u("/internal/link/checkout"), headers=self._bot_headers(), json={"channel": self.channel, "ext_id": str(ext_id), "package_id": package_id}, timeout=20)

    # ── per-user (minted JWT) ──
    async def me(self, jwt: str) -> dict:
        r = await self.client.get(self._u("/api/auth/me"), headers=self._auth(jwt), timeout=15)
        r.raise_for_status()
        return r.json()

    async def packages(self) -> list:
        r = await self.client.get(self._u("/api/credits/packages"), timeout=15)
        r.raise_for_status()
        return r.json()

    async def generate(self, jwt: str, body: dict) -> httpx.Response:
        return await self.client.post(self._u("/api/generate"), headers=self._auth(jwt), json=body, timeout=20)

    async def poll(self, jwt: str, gen_id: str) -> dict:
        r = await self.client.get(self._u(f"/api/generations/{gen_id}"), headers=self._auth(jwt), timeout=15)
        r.raise_for_status()
        return r.json()

    async def recent_generations(self, jwt: str, gen_type: str | None = None, limit: int = 10) -> list:
        params: dict = {"limit": limit}
        if gen_type:
            params["type"] = gen_type
        r = await self.client.get(self._u("/api/generations"), headers=self._auth(jwt), params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    async def stats(self, jwt: str) -> dict:
        r = await self.client.get(self._u("/api/stats"), headers=self._auth(jwt), timeout=15)
        r.raise_for_status()
        return r.json()

    async def templates(self, platform: str | None = None, gen_type: str | None = None, limit: int = 9) -> list:
        params: dict = {}
        if platform and platform != "Universal":
            params["platform"] = platform
        if gen_type:
            params["type"] = gen_type
        r = await self.client.get(self._u("/api/templates"), params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data[:limit] if isinstance(data, list) else []

    async def list_prompts(self, jwt: str, gen_type: str | None = None) -> list:
        params = {"type": gen_type} if gen_type else {}
        r = await self.client.get(self._u("/api/prompt-templates"), headers=self._auth(jwt), params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    async def save_prompt(self, jwt: str, title: str, prompt: str, gen_type: str = "video") -> dict:
        r = await self.client.post(self._u("/api/prompt-templates"), headers=self._auth(jwt),
                                   json={"title": title, "prompt": prompt, "type": gen_type}, timeout=15)
        r.raise_for_status()
        return r.json()

    async def set_onboarding(self, jwt: str, use_case: str, platforms: list | None = None) -> dict:
        body: dict = {"use_case": use_case}
        if platforms is not None:
            body["preferred_platforms"] = platforms
        r = await self.client.post(self._u("/api/users/me/onboarding"), headers=self._auth(jwt), json=body, timeout=15)
        r.raise_for_status()
        return r.json()

    async def upload(self, ext_id, content: bytes, mime: str) -> dict:
        """Store user media in FluxVAI. Media is downloaded by the channel sender."""
        b64 = base64.b64encode(content).decode()
        if self._is_wa:
            payload, url = {"phone": ext_id, "content_b64": b64, "mime_type": mime}, "/internal/wa/upload"
        else:
            payload, url = {"channel": self.channel, "ext_id": str(ext_id), "content_b64": b64, "mime_type": mime}, "/internal/link/upload"
        r = await self.client.post(self._u(url), headers=self._bot_headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def cost_for(self, gen_type: str) -> int:
        return CREDIT_COST.get(gen_type, 15)

    async def cost_estimate(self, body: dict) -> int:
        """Real cost from the backend (matches what /api/generate charges:
        base + duration + quality/model multipliers). Falls back to the flat map."""
        try:
            r = await self.client.post(self._u("/api/cost-estimate"), json=body, timeout=15)
            r.raise_for_status()
            return int(r.json().get("credits") or self.cost_for(body.get("type", "video")))
        except Exception:  # noqa: BLE001
            return self.cost_for(body.get("type", "video"))
