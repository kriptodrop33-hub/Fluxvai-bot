import os
import pathlib
import sys
import tempfile

# Make the bot package importable and configure the environment BEFORE app imports.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

os.environ.setdefault("BOT_SERVICE_SECRET", "test-bot-secret-123")
os.environ.setdefault("FLUXVAI_BASE_URL", "http://127.0.0.1:8001")
os.environ.setdefault("WA_APP_SECRET", "")  # skip webhook signature in tests
os.environ.setdefault("WA_PHONE_NUMBER_ID", "0000000000")
os.environ.setdefault("WA_ACCESS_TOKEN", "test")
os.environ.setdefault("POLL_INTERVAL_SECS", "2")
os.environ.setdefault("POLL_TIMEOUT_SECS", "60")

_DB = pathlib.Path(tempfile.gettempdir()) / "fluxvai_bot_test.sqlite3"
for p in (_DB, pathlib.Path(str(_DB) + "-wal"), pathlib.Path(str(_DB) + "-shm")):
    try:
        p.unlink()
    except FileNotFoundError:
        pass
os.environ.setdefault("BOT_DB_PATH", str(_DB))


class FakeWA:
    """Captures outbound messages instead of calling the Graph API."""

    def __init__(self, channel="whatsapp"):
        self.sent = []  # list of dicts: {kind, to, body, ...}
        self.channel = channel

    async def send_text(self, to, text):
        self.sent.append({"kind": "text", "to": to, "body": text})

    async def send_buttons(self, to, body, buttons):
        self.sent.append({"kind": "buttons", "to": to, "body": body, "buttons": list(buttons)})

    async def send_list(self, to, body, button_text, rows, section_title="Seçenekler"):
        self.sent.append({"kind": "list", "to": to, "body": body, "rows": list(rows)})

    async def send_template(self, to, name, lang="tr", components=None):
        self.sent.append({"kind": "template", "to": to, "name": name})

    async def send_image(self, to, link, caption=None):
        self.sent.append({"kind": "image", "to": to, "link": link, "body": caption or ""})

        class _R:
            status_code = 200

        return _R()

    async def download_media(self, media_id):
        # 1x1 PNG — stands in for a real WhatsApp/Telegram media download in tests.
        import base64
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
        )
        return png, "image/png"

    # helpers
    def last(self):
        return self.sent[-1] if self.sent else None

    def texts(self):
        return [m["body"] for m in self.sent if m["kind"] == "text"]

    def all_bodies(self):
        return [m.get("body", "") for m in self.sent]
