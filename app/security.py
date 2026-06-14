"""Webhook + internal-call signature checks (stdlib only)."""
import hashlib
import hmac
import logging

log = logging.getLogger("bot.security")


def verify_meta_signature(app_secret: str, raw_body: bytes, header_sig: str | None) -> bool:
    """Validate Meta's X-Hub-Signature-256 over the *raw* request body.

    If no app secret is configured we allow the request (local-dev convenience)
    but log a loud warning — never ship to production without it.
    """
    if not app_secret:
        log.warning("WA_APP_SECRET not set — skipping webhook signature check (DEV ONLY)")
        return True
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig)


def check_internal_secret(bot_secret: str, presented: str | None) -> bool:
    """Constant-time comparison for the X-Bot-Secret header on /internal/* routes."""
    return bool(bot_secret) and bool(presented) and hmac.compare_digest(bot_secret, presented)
