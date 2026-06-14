"""Conversation state machine (bilingual). One entry point: handle_inbound()."""
import asyncio
import logging

from . import i18n, store, tasks
from .fluxvai_client import FluxVAI, NotLinked
from .whatsapp import WhatsApp

log = logging.getLogger("bot.fsm")

_ASPECT = {"Instagram": "9:16", "TikTok": "9:16", "LinkedIn": "1:1", "X": "16:9", "YouTube": "16:9", "Universal": "16:9"}
DURATIONS = [15, 30, 60]
_KEEP_WORDS = ("tamam", "ok", "okey", "evet", "aynen", "devam", "kullan", "yes", "keep")
_TEMPLATE_WORDS = ("şablon", "sablon", "şablonlar", "sablonlar", "template", "templates")

# Smart defaults so the fast path (type → prompt → create) needs no extra steps.
_DEFAULTS = {
    "video": {"platform": "Universal", "aspect": "16:9", "style": "cinematic", "duration": 30},
    "image": {"platform": "Universal", "aspect": "1:1", "style": "realistic"},
    "audio": {"platform": "Universal", "style": "cinematic", "duration": 30},
    "3d": {"platform": "Universal", "aspect": "1:1", "style": "realistic"},
}


def _apply_defaults(gen: dict) -> None:
    for k, v in _DEFAULTS.get(gen.get("type"), {}).items():
        gen.setdefault(k, v)


# ── helpers ───────────────────────────────────────────────────────────
def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _lang(ctx: dict) -> str:
    return ctx.get("lang", "tr")


def _keep(ctx: dict) -> dict:
    return {k: ctx[k] for k in ("jwt", "user", "use_case", "lang", "last_gen") if k in ctx}


def _go_idle(phone: str, ctx: dict) -> None:
    store.set_session(phone, "IDLE", _keep(ctx))


def _use_case(ctx: dict) -> str:
    return ctx.get("use_case") or (ctx.get("user") or {}).get("onboarding_use_case") or ""


async def _refresh_balance(fx: FluxVAI, ctx: dict) -> int:
    try:
        me = await fx.me(ctx["jwt"])
        ctx["user"] = me
        return int(me.get("credits", 0))
    except Exception:  # noqa: BLE001
        return int((ctx.get("user") or {}).get("credits", 0))


async def _ask_language(wa: WhatsApp, phone: str, ctx: dict) -> None:
    store.set_session(phone, "LANG_SELECT", ctx)
    await wa.send_list(phone, i18n.t(ctx.get("lang", "tr"), "ask_language"), "Dil / Lang", i18n.language_rows())


async def _send_menu(wa: WhatsApp, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    user = ctx.get("user") or {}
    credits = int(user.get("credits", 0))
    await wa.send_buttons(phone, i18n.greeting(lang, user.get("name", ""), credits), i18n.main_menu_buttons(lang))


async def _send_more_menu(wa: WhatsApp, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    await wa.send_list(phone, i18n.t(lang, "more_title"), "Aç" if lang == "tr" else "Open", i18n.more_menu(lang))


async def _after_auth(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    if _use_case(ctx):
        store.set_session(phone, "IDLE", ctx)
        await _send_menu(wa, phone, ctx)
        return
    store.set_session(phone, "ONBOARDING", ctx)
    lang = _lang(ctx)
    await wa.send_list(phone, i18n.t(lang, "ask_use_case"), "Seç" if lang == "tr" else "Pick",
                       [(f"onb:{k}", label, desc) for k, label, desc in i18n.use_cases(lang)])


async def _start(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    """After language is known: resolve the account or ask for a code."""
    try:
        data = await fx.resolve(phone)
        ctx["jwt"], ctx["user"] = data["token"], data["user"]
        await _after_auth(wa, fx, phone, ctx)
    except NotLinked:
        store.set_session(phone, "AWAITING_CODE", ctx)
        await wa.send_text(phone, i18n.t(_lang(ctx), "ask_code"))
    except Exception as e:  # noqa: BLE001  — backend unreachable (e.g. before fluxvai.app is live)
        log.warning("resolve failed (backend down?): %s", e)
        await wa.send_text(phone, i18n.t(_lang(ctx), "service_unavailable"))


async def _attempt_link(wa: WhatsApp, fx: FluxVAI, phone: str, code: str, ctx: dict) -> None:
    resp = await fx.link(phone, code)
    lang = _lang(ctx)
    if resp.status_code == 200:
        data = resp.json()
        ctx["jwt"], ctx["user"] = data["token"], data["user"]
        await _after_auth(wa, fx, phone, ctx)
        return
    store.set_session(phone, "AWAITING_CODE", ctx)
    key = {409: "code_taken", 429: "code_ratelimit"}.get(resp.status_code, "code_invalid")
    await wa.send_text(phone, i18n.t(lang, key))


async def _start_generation_wizard(wa: WhatsApp, phone: str, ctx: dict) -> None:
    ctx["gen"] = {}
    store.set_session(phone, "GEN_TYPE", ctx)
    lang = _lang(ctx)
    label = "Ne üretelim?" if lang == "tr" else "What to create?"
    await wa.send_buttons(phone, label, i18n.type_quick(lang))


async def _start_image_edit(wa: WhatsApp, phone: str, ctx: dict) -> None:
    ctx["gen"] = {"type": "image", "imgedit": True, "platform": "Universal", "style": "realistic"}
    store.set_session(phone, "GEN_IMG_AWAIT_PHOTO", ctx)
    await wa.send_text(phone, i18n.t(_lang(ctx), "ask_photo"))


async def _ask_platform(wa: WhatsApp, phone: str, ctx: dict) -> None:
    store.set_session(phone, "GEN_PLATFORM", ctx)
    lang = _lang(ctx)
    label = "Hangi platform?" if lang == "tr" else "Which platform?"
    await wa.send_list(phone, label, "Platform", i18n.platforms(lang))


async def _ask_style(wa: WhatsApp, phone: str, ctx: dict) -> None:
    store.set_session(phone, "GEN_STYLE", ctx)
    lang = _lang(ctx)
    label = "Hangi stil?" if lang == "tr" else "Which style?"
    await wa.send_list(phone, label, "Stil" if lang == "tr" else "Style",
                       [(f"style:{sid}", lbl, desc) for sid, lbl, desc in i18n.styles(lang)])


async def _send_templates(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    g = ctx["gen"]
    lang = _lang(ctx)
    try:
        tmpls = await fx.templates(gen_type=g.get("type"), limit=8)  # type-only → more matches
    except Exception:  # noqa: BLE001
        tmpls = []
    if not tmpls:
        store.set_session(phone, "GEN_PROMPT", ctx)
        await wa.send_text(phone, i18n.t(lang, "no_templates"))
        await wa.send_text(phone, i18n.t(lang, "ask_prompt"))
        return
    g["_tmpls"] = {t["id"]: {"title": t.get("title", ""), "prompt": t.get("prompt", ""),
                             "style": t.get("style"), "duration": t.get("duration"), "aspect": t.get("aspect")}
                   for t in tmpls}
    rows = [(f"tmpl:{t['id']}", t.get("title", "Şablon")[:24], f"{t.get('duration', '')} • {t.get('style', '')}"[:72]) for t in tmpls]
    rows.append(("tmpl:scratch", i18n.t(lang, "scratch_row"), ""))
    store.set_session(phone, "GEN_TEMPLATE", ctx)
    await wa.send_list(phone, i18n.t(lang, "template_intro"), "Şablon" if lang == "tr" else "Template", rows)


async def _send_packages(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    try:
        pkgs = await fx.packages()
    except Exception:  # noqa: BLE001
        await wa.send_text(phone, i18n.t(lang, "payment_unavailable"))
        _go_idle(phone, ctx)
        return
    rows = [(f"pkg:{p['id']}", f"{p['name']} • {p['credits']}", f"{p.get('currency', '$')}{p['price']}") for p in pkgs[:10]]
    store.set_session(phone, "BUY_PACKAGE", ctx)
    await wa.send_list(phone, i18n.t(lang, "packages_intro"), "Paket" if lang == "tr" else "Packages", rows)


async def _show_prompts(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    try:
        prompts = await fx.list_prompts(ctx["jwt"])
    except Exception:  # noqa: BLE001
        prompts = []
    user_p = [p for p in prompts if not p.get("is_system")]
    sys_p = [p for p in prompts if p.get("is_system")]
    shown = (user_p + sys_p)[:8]
    ctx["_prompts"] = {p["id"]: {"prompt": p.get("prompt", ""), "type": p.get("type", "video")} for p in shown}
    rows = [("prompt:new", i18n.t(lang, "prompt_new_row"), "")]
    for p in shown:
        tag = "★" if not p.get("is_system") else "○"
        rows.append((f"uprompt:{p['id']}", f"{tag} {p.get('title', '')}"[:24], (p.get("prompt", "") or "")[:60]))
    store.set_session(phone, "PROMPTS_MENU", ctx)
    title = i18n.t(lang, "prompts_title") if user_p else i18n.t(lang, "prompts_empty")
    await wa.send_list(phone, title, "Promptlar" if lang == "tr" else "Prompts", rows)


async def _show_gallery_categories(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    await wa.send_list(phone, i18n.t(lang, "gallery_pick"), "Galeri" if lang == "tr" else "Gallery",
                       i18n.gallery_categories(lang))


async def _show_gallery(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict, gtype: str) -> None:
    lang = _lang(ctx)
    gt = None if gtype == "all" else gtype
    try:
        gens = await fx.recent_generations(ctx["jwt"], gen_type=gt, limit=10)
    except Exception:  # noqa: BLE001
        gens = []
    if not gens:
        await wa.send_text(phone, i18n.t(lang, "no_items"))
    else:
        lines = [i18n.t(lang, "history_title")]
        for g in gens[:10]:
            emoji = {"completed": "✅", "processing": "⏳", "failed": "❌"}.get(g.get("status"), "•")
            name = (g.get("prompt") or g.get("filename") or "")[:40]
            lines.append(f"{emoji} {i18n.type_label(lang, g.get('type'))} — {name}")
            if g.get("output_url"):
                lines.append(f"   {g['output_url']}")
        await wa.send_text(phone, "\n".join(lines))
    _go_idle(phone, ctx)
    await wa.send_buttons(phone, i18n.t(lang, "quick_after"), i18n.quick_actions(lang))


async def _show_account(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    await _refresh_balance(fx, ctx)
    try:
        st = await fx.stats(ctx["jwt"])
    except Exception:  # noqa: BLE001
        st = {}
    credits = int(st.get("credits_remaining", (ctx.get("user") or {}).get("credits", 0)))
    await wa.send_text(phone, i18n.account_card(lang, credits, st.get("total_generations", 0),
                                                st.get("processing", 0), st.get("credits_used", 0)))
    await _send_menu(wa, phone, ctx)


# ── main entry point ──────────────────────────────────────────────────
async def handle_inbound(wa: WhatsApp, fx: FluxVAI, inbound: dict) -> None:
    phone = inbound.get("phone")
    if not phone:
        return
    try:
        await _dispatch(wa, fx, inbound, phone)
    except Exception as e:  # noqa: BLE001
        log.exception("handler error for %s: %s", phone, e)
        try:
            sess = store.get_session(phone)
            await wa.send_text(phone, i18n.t(sess["context"].get("lang", "tr"), "generic_error"))
        except Exception:  # noqa: BLE001
            pass


async def _dispatch(wa: WhatsApp, fx: FluxVAI, inbound: dict, phone: str) -> None:
    raw = (inbound.get("text") or "").strip()
    sel = inbound.get("selection_id")
    low = raw.lower()
    has_media = bool(inbound.get("media_id"))

    sess = store.get_session(phone)
    state = sess["state"]
    ctx = sess["context"]

    # 1) Language selection — always first.
    if state == "LANG_SELECT":
        if sel and sel.startswith("lang:") and sel.split(":", 1)[1] in i18n.LANGS:
            ctx["lang"] = sel.split(":", 1)[1]
            await wa.send_text(phone, i18n.t(ctx["lang"], "language_saved"))
            await _start(wa, fx, phone, ctx)
        else:
            await _ask_language(wa, phone, ctx)
        return
    if "lang" not in ctx:
        await _ask_language(wa, phone, ctx)
        return
    lang = ctx["lang"]

    cmd = i18n.parse_command(raw) if not has_media else None

    # 2) Commands that work in any (linked-or-not) state.
    if cmd == "lang" or sel == "nav:lang":
        await _ask_language(wa, phone, ctx)
        return
    if cmd == "help" or sel == "nav:help":
        await wa.send_text(phone, i18n.help_text(lang))
        return

    # 3) Link gating.
    if state == "UNLINKED":
        try:
            data = await fx.resolve(phone)
            ctx["jwt"], ctx["user"] = data["token"], data["user"]
            await _after_auth(wa, fx, phone, ctx)
            return
        except NotLinked:
            pass
        code = _digits(raw)
        if len(code) == 6:
            await _attempt_link(wa, fx, phone, code, ctx)
        else:
            store.set_session(phone, "AWAITING_CODE", ctx)
            await wa.send_text(phone, i18n.t(lang, "ask_code"))
        return

    if state == "AWAITING_CODE":
        code = _digits(raw)
        if len(code) != 6:
            await wa.send_text(phone, i18n.t(lang, "ask_code_retry"))
            return
        await _attempt_link(wa, fx, phone, code, ctx)
        return

    # 4) Linked global actions (commands + main-menu taps).
    if cmd == "cancel":
        _go_idle(phone, ctx)
        await wa.send_text(phone, i18n.t(lang, "cancelled"))
        await _send_menu(wa, phone, ctx)
        return
    if cmd == "menu" or sel == "nav:menu":
        _go_idle(phone, ctx)
        await _send_menu(wa, phone, ctx)
        return
    if sel == "nav:more":
        await _send_more_menu(wa, phone, ctx)
        return
    if cmd in ("create", "templates") or sel == "nav:gen":
        await _start_generation_wizard(wa, phone, ctx)
        return
    if cmd == "edit" or sel == "nav:edit":
        await _start_image_edit(wa, phone, ctx)
        return
    if cmd == "prompts" or sel == "nav:prompts":
        await _show_prompts(wa, fx, phone, ctx)
        return
    if cmd == "buy" or sel == "nav:buy":
        await _send_packages(wa, fx, phone, ctx)
        return
    if cmd == "balance" or sel == "nav:balance":
        await _show_account(wa, fx, phone, ctx)
        return
    if cmd == "history" or sel == "nav:history":
        await _show_gallery_categories(wa, fx, phone, ctx)
        return
    if sel and sel.startswith("hist:"):
        await _show_gallery(wa, fx, phone, ctx, sel.split(":", 1)[1])
        return
    if cmd == "repeat" or sel == "act:repeat":
        last = ctx.get("last_gen")
        if not last:
            await wa.send_text(phone, i18n.t(lang, "no_last_gen"))
            await _send_menu(wa, phone, ctx)
        else:
            ctx["gen"] = dict(last)  # one-tap re-run of the previous generation
            await _do_generate(wa, fx, phone, ctx)
        return

    # 5) Inbound photo (image-edit flow).
    if has_media:
        if state == "GEN_IMG_AWAIT_PHOTO":
            await _handle_uploaded_photo(wa, fx, phone, ctx, inbound)
        else:
            await wa.send_text(phone, i18n.t(lang, "photo_out_of_flow"))
        return

    # 6) State machine.
    if state == "ONBOARDING":
        if sel and sel.startswith("onb:"):
            key = sel.split(":", 1)[1]
            ctx["use_case"] = key
            if key != "skip" and ctx.get("jwt"):
                try:
                    await fx.set_onboarding(ctx["jwt"], key)
                    if isinstance(ctx.get("user"), dict):
                        ctx["user"]["onboarding_use_case"] = key
                except Exception:  # noqa: BLE001
                    pass
            await wa.send_text(phone, i18n.t(lang, "onboarding_saved"))
            _go_idle(phone, ctx)
            await _send_menu(wa, phone, ctx)
        else:
            await _after_auth(wa, fx, phone, ctx)
        return

    if state == "IDLE":
        _go_idle(phone, ctx)
        await _send_menu(wa, phone, ctx)
        return

    if state == "GEN_TYPE":
        if sel == "type:more":
            label = "Tüm türler:" if lang == "tr" else "All types:"
            await wa.send_list(phone, label, "Tür" if lang == "tr" else "Type", i18n.types(lang, _use_case(ctx)))
        elif sel == "type:imgedit":
            await _start_image_edit(wa, phone, ctx)
        elif sel and sel.startswith("type:"):
            ctx["gen"]["type"] = sel.split(":", 1)[1]
            _apply_defaults(ctx["gen"])  # fast path: skip platform/style/duration
            store.set_session(phone, "GEN_PROMPT", ctx)
            await wa.send_text(phone, i18n.t(lang, "ask_prompt"))
        else:
            await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
        return

    if state == "GEN_PLATFORM":  # only reached via "⚙️ Detay"
        if sel and sel.startswith("plat:"):
            pid = sel.split(":", 1)[1]
            ctx["gen"]["platform"] = pid
            ctx["gen"]["aspect"] = _ASPECT.get(pid, "16:9")
            await _ask_style(wa, phone, ctx)
        else:
            await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
        return

    if state == "GEN_TEMPLATE":
        if sel == "tmpl:scratch":
            ctx["gen"].pop("_tmpls", None)
            store.set_session(phone, "GEN_PROMPT", ctx)
            await wa.send_text(phone, i18n.t(lang, "ask_prompt"))
        elif sel and sel.startswith("tmpl:"):
            tmpl = (ctx["gen"].get("_tmpls") or {}).get(sel.split(":", 1)[1])
            if not tmpl:
                await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
                return
            g = ctx["gen"]
            g["template_id"] = sel.split(":", 1)[1]
            g["prompt"] = tmpl.get("prompt") or ""
            if tmpl.get("style"):
                g["style"] = tmpl["style"]
            if tmpl.get("aspect"):
                g["aspect"] = tmpl["aspect"]
            dur = _digits(str(tmpl.get("duration") or ""))
            if dur:
                g["duration"] = int(dur)
            g["_from_template"] = True
            g.pop("_tmpls", None)
            store.set_session(phone, "GEN_PROMPT", ctx)
            await wa.send_text(phone, i18n.template_prefill(lang, tmpl.get("title", "Şablon"), g["prompt"]))
        else:
            await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
        return

    if state == "GEN_PROMPT":
        g = ctx["gen"]
        if low in _TEMPLATE_WORDS:
            await _send_templates(wa, fx, phone, ctx)
            return
        if g.get("prompt") and (not raw or low in _KEEP_WORDS):
            pass
        elif not raw:
            await wa.send_text(phone, i18n.t(lang, "prompt_empty"))
            return
        elif len(raw) > 2000:
            await wa.send_text(phone, i18n.t(lang, "prompt_too_long"))
            return
        else:
            g["prompt"] = raw
        await _show_confirm(wa, fx, phone, ctx)  # defaults already set; tweak via "⚙️ Detay"
        return

    if state == "GEN_STYLE":
        if sel and sel.startswith("style:"):
            ctx["gen"]["style"] = sel.split(":", 1)[1]
            if ctx["gen"]["type"] in ("video", "audio"):
                store.set_session(phone, "GEN_DURATION", ctx)
                await wa.send_buttons(phone, i18n.t(lang, "ask_duration"), [(f"dur:{d}", f"{d} sn") for d in DURATIONS])
            else:
                await _show_confirm(wa, fx, phone, ctx)
        else:
            await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
        return

    if state == "GEN_DURATION":
        dur = int(_digits(sel)) if (sel and sel.startswith("dur:")) else (int(_digits(raw)) if _digits(raw) else None)
        if not dur:
            await wa.send_buttons(phone, i18n.t(lang, "ask_duration"), [(f"dur:{d}", f"{d} sn") for d in DURATIONS])
            return
        ctx["gen"]["duration"] = dur
        await _show_confirm(wa, fx, phone, ctx)
        return

    if state == "GEN_IMG_AWAIT_PHOTO":
        await wa.send_text(phone, i18n.t(lang, "expect_photo"))
        return

    if state == "GEN_IMG_PROMPT":
        if not raw:
            await wa.send_text(phone, i18n.t(lang, "ask_edit_prompt"))
            return
        ctx["gen"]["prompt"] = raw[:2000]
        await _show_confirm(wa, fx, phone, ctx)
        return

    if state == "GEN_CONFIRM":
        if sel == "confirm:yes" or low in _KEEP_WORDS:
            await _do_generate(wa, fx, phone, ctx)
        elif sel == "confirm:detail":
            ctx["gen"]["_detail"] = True
            await _ask_platform(wa, phone, ctx)
        elif sel == "confirm:no":
            _go_idle(phone, ctx)
            await wa.send_text(phone, i18n.t(lang, "cancelled"))
        else:
            await wa.send_buttons(phone, i18n.t(lang, "pick_from_list"), i18n.confirm_buttons(lang))
        return

    if state == "GEN_PROCESSING":
        await wa.send_text(phone, i18n.t(lang, "processing"))
        return

    if state == "BUY_PACKAGE":
        if sel and sel.startswith("pkg:"):
            await _do_checkout(wa, fx, phone, ctx, sel.split(":", 1)[1])
        else:
            await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
        return

    if state == "BUY_AWAIT_PAYMENT":
        await wa.send_text(phone, i18n.t(lang, "await_payment_nudge"))
        return

    # ── My prompts ──
    if state == "PROMPTS_MENU":
        if sel == "prompt:new":
            store.set_session(phone, "PROMPT_SAVE_TITLE", ctx)
            await wa.send_text(phone, i18n.t(lang, "save_prompt_title"))
        elif sel and sel.startswith("uprompt:"):
            p = (ctx.get("_prompts") or {}).get(sel.split(":", 1)[1])
            if not p:
                await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
                return
            ctx["gen"] = {"type": p.get("type", "video"), "prompt": p.get("prompt", "")}
            _apply_defaults(ctx["gen"])
            ctx.pop("_prompts", None)
            await _show_confirm(wa, fx, phone, ctx)  # straight to confirm — fastest
        else:
            await wa.send_text(phone, i18n.t(lang, "pick_from_list"))
        return

    if state == "PROMPT_SAVE_TITLE":
        if not raw:
            await wa.send_text(phone, i18n.t(lang, "save_prompt_title"))
            return
        ctx["_new_prompt_title"] = raw[:80]
        store.set_session(phone, "PROMPT_SAVE_TEXT", ctx)
        await wa.send_text(phone, i18n.t(lang, "save_prompt_text"))
        return

    if state == "PROMPT_SAVE_TEXT":
        if not raw:
            await wa.send_text(phone, i18n.t(lang, "save_prompt_text"))
            return
        title = ctx.pop("_new_prompt_title", "Prompt")
        try:
            await fx.save_prompt(ctx["jwt"], title, raw[:2000])
            await wa.send_text(phone, i18n.prompt_saved(lang, title))
        except Exception:  # noqa: BLE001
            await wa.send_text(phone, i18n.t(lang, "generic_error"))
        await _show_prompts(wa, fx, phone, ctx)
        return

    # ── Fallback ──
    _go_idle(phone, ctx)
    await _send_menu(wa, phone, ctx)


async def _handle_uploaded_photo(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict, inbound: dict) -> None:
    lang = _lang(ctx)
    await wa.send_text(phone, i18n.t(lang, "photo_received"))
    try:
        data, mime = await wa.download_media(inbound["media_id"])
        up = await fx.upload(phone, data, inbound.get("mime_type") or mime)
    except Exception as e:  # noqa: BLE001
        log.warning("photo handling failed: %s", e)
        await wa.send_text(phone, i18n.t(lang, "photo_fail"))
        return
    ctx["gen"]["source_media_url"] = up.get("url")
    ctx["gen"]["source_media_id"] = up.get("media_id")
    caption = (inbound.get("text") or "").strip()
    if caption:
        ctx["gen"]["prompt"] = caption[:2000]
        await _show_confirm(wa, fx, phone, ctx)
    else:
        store.set_session(phone, "GEN_IMG_PROMPT", ctx)
        await wa.send_text(phone, i18n.t(lang, "ask_edit_prompt"))


async def _show_confirm(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    g = ctx["gen"]
    cost = await fx.cost_estimate({"type": g["type"], "duration": g.get("duration")})  # real charge
    balance = await _refresh_balance(fx, ctx)
    if balance < cost:
        await wa.send_text(phone, i18n.insufficient(lang, cost, balance))
        await _send_packages(wa, fx, phone, ctx)
        return
    store.set_session(phone, "GEN_CONFIRM", ctx)
    await wa.send_buttons(
        phone,
        i18n.confirm_summary(lang, g["type"], g.get("platform"), g.get("prompt", ""), g.get("style"),
                             g.get("duration"), cost, balance),
        i18n.confirm_buttons(lang),
    )


async def _do_generate(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict) -> None:
    lang = _lang(ctx)
    if ctx.get("submitting"):
        await wa.send_text(phone, i18n.t(lang, "already_submitting"))
        return
    ctx["submitting"] = True
    store.set_session(phone, "GEN_CONFIRM", ctx)

    g = ctx["gen"]
    body = {
        "type": g["type"], "prompt": g.get("prompt", ""), "platform": g.get("platform", "Universal"),
        "duration": g.get("duration", 30), "style": g.get("style", "cinematic"), "aspect": g.get("aspect", "16:9"),
    }
    if g.get("template_id"):
        body["template_id"] = g["template_id"]
    if g.get("source_media_url"):
        body["source_media_url"] = g["source_media_url"]
        body["source_media_id"] = g.get("source_media_id")

    resp = await fx.generate(ctx["jwt"], body)
    ctx["submitting"] = False

    if resp.status_code == 402:
        cost = await fx.cost_estimate({"type": g["type"], "duration": g.get("duration")})
        await wa.send_text(phone, i18n.insufficient(lang, cost, await _refresh_balance(fx, ctx)))
        await _send_packages(wa, fx, phone, ctx)
        return
    if resp.status_code == 401:
        ctx["jwt"] = (await fx.resolve(phone))["token"]
        resp = await fx.generate(ctx["jwt"], body)
    if resp.status_code != 200:
        log.warning("generate failed %s: %s", resp.status_code, resp.text[:300])
        _go_idle(phone, ctx)
        await wa.send_text(phone, i18n.t(lang, "generic_error"))
        return

    gen_id = resp.json()["id"]
    ctx["last_gen"] = dict(body)  # remembered for one-tap "🔁 Repeat"
    store.add_pending(gen_id, phone, ctx["jwt"])
    store.set_session(phone, "GEN_PROCESSING", _keep(ctx))
    await wa.send_text(phone, i18n.t(lang, "processing"))
    asyncio.create_task(tasks.poll_and_deliver(wa, fx, phone, ctx["jwt"], gen_id))


async def _do_checkout(wa: WhatsApp, fx: FluxVAI, phone: str, ctx: dict, package_id: str) -> None:
    lang = _lang(ctx)
    try:
        resp = await fx.checkout(phone, package_id)
    except Exception:  # noqa: BLE001
        await wa.send_text(phone, i18n.t(lang, "payment_unavailable"))
        _go_idle(phone, ctx)
        return
    if resp.status_code != 200:
        await wa.send_text(phone, i18n.t(lang, "payment_unavailable"))
        _go_idle(phone, ctx)
        return
    data = resp.json()
    store.set_session(phone, "BUY_AWAIT_PAYMENT", ctx)
    await wa.send_text(phone, i18n.checkout_link(lang, data.get("name", "Kredi"), data.get("url")))
