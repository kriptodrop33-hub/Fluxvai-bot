"""Multilingual bot copy (data-driven). Add a language = add a dict entry.

Languages: tr, en, de, ar, es, fr, ru. Chosen on /start (list picker),
remembered per user in the session. t(lang,key) for strings; helper funcs
build dynamic messages; *(lang) builders return localized option rows.
"""

DEFAULT_LANG = "tr"
LANG_NAMES = {  # native names, shown in the picker
    "tr": "🇹🇷 Türkçe", "en": "🇬🇧 English", "de": "🇩🇪 Deutsch", "ar": "🇸🇦 العربية",
    "es": "🇪🇸 Español", "fr": "🇫🇷 Français", "ru": "🇷🇺 Русский",
}
LANGS = tuple(LANG_NAMES.keys())

# ── strings + dynamic templates (placeholders in {}) ──────────────────
S = {
    "tr": {
        "ask_language": "🌐 Dil seç / Choose language:",
        "language_saved": "✅ Dil: Türkçe",
        "ask_code": "Önce WhatsApp/Telegram'ı FluxVAI hesabına bağla 🔗\n\nfluxvai.app → Ayarlar → *Kod oluştur* → 6 haneli kodu buraya yaz 👇",
        "ask_code_retry": "Lütfen siteden aldığın *6 haneli* kodu yaz (örn. 123456).",
        "code_invalid": "❌ Kod geçersiz veya süresi dolmuş. Siteden yeni kod al.",
        "code_taken": "⚠️ Bu hesap başka bir kullanıcıya bağlı.",
        "code_ratelimit": "⏳ Çok fazla deneme. Biraz sonra tekrar dene.",
        "pick_from_list": "Lütfen listeden seç 👇",
        "cancelled": "İptal edildi. Ana menüye döndük.",
        "ask_prompt": "✍️ Ne üretmek istediğini yaz.\n_Örn: \"Gün batımında koşan biri, sinematik\"_\n\n💡 *şablon* → hazır şablonlar · *promptlarım* → kayıtlılar",
        "prompt_empty": "Lütfen ne üretmek istediğini yaz.",
        "prompt_too_long": "Çok uzun (maks 2000 karakter).",
        "ask_duration": "⏱️ Süre seç:",
        "processing": "🎬 Üretim başladı! Hazır olunca göndereceğim…",
        "already_submitting": "⏳ Önceki isteğin işleniyor, bekle.",
        "gen_failed": "❌ Üretim başarısız. *menü* yazıp tekrar dene.",
        "gen_timeout": "⏳ Biraz uzun sürüyor, hazır olunca haber vereceğim.",
        "packages_intro": "💳 Kredi paketi seç:",
        "payment_unavailable": "⚠️ Ödeme şu an kullanılamıyor.",
        "await_payment_nudge": "💳 Ödemeni bekliyorum. Tamamlandıysa krediler birazdan yüklenir. *menü* yaz.",
        "generic_error": "⚠️ Bir şeyler ters gitti. *menü* yaz.",
        "ask_use_case": "Ağırlıklı ne üreteceksin? 🙌",
        "onboarding_saved": "Harika, ayarladım! 🎯",
        "template_intro": "✨ Hazır şablon seç ya da sıfırdan başla:",
        "no_templates": "Hazır şablon yok, sıfırdan devam edelim.",
        "scratch_row": "✍️ Sıfırdan başla",
        "prompt_new_row": "➕ Yeni prompt kaydet",
        "ask_photo": "📷 Düzenlemek istediğin fotoğrafı gönder.",
        "photo_received": "📥 Fotoğrafı aldım, hazırlıyorum…",
        "photo_fail": "❌ Fotoğrafı işleyemedim, tekrar gönder.",
        "ask_edit_prompt": "✍️ Bu görseli nasıl değiştireyim? _Örn: arka planı gece yap_",
        "expect_photo": "Önce bir fotoğraf gönder 📷",
        "photo_out_of_flow": "Önce *menü* → ✏️ Görsel Düzenle ile başla.",
        "more_title": "⚙️ Diğer seçenekler:",
        "prompts_title": "📝 Promptların:",
        "prompts_empty": "Kayıtlı promptun yok. Yeni ekle 👇",
        "save_prompt_title": "Prompt için *başlık* yaz.",
        "save_prompt_text": "Şimdi *prompt metnini* yaz.",
        "no_history": "Henüz üretim geçmişin yok.",
        "history_title": "🕘 Son üretimlerin:",
        "no_last_gen": "Henüz yinelenecek üretim yok.",
        "quick_after": "Sırada ne var?",
        # dynamic templates
        "greeting": "Merhaba {name}! 👋\n💰 Bakiye: *{credits}* kredi\n\nNe yapmak istersin?",
        "balance": "💰 Bakiyen: *{credits}* kredi.",
        "insufficient": "😕 Bu üretim *{cost}* kredi gerektiriyor, bakiyen *{balance}*. Paket seç 👇",
        "checkout": "🛒 *{name}* için ödeme:\n{url}\n\nÖdeme sonrası kredilerin otomatik yüklenir.",
        "credits_loaded": "✅ *{amount}* kredi yüklendi! 💰 Yeni bakiye: *{new_balance}*. *menü* yaz.",
        "summary": "📋 *Özet*\n• Tür: {label}\n• Platform: {platform}\n• Stil: {style}{dur}\n• Açıklama: {prompt}\n\n💸 Maliyet: *{cost}* | 💰 Bakiye: *{balance}*\n\nOnaylıyor musun?",
        "dur_fmt": "\n• Süre: {duration} sn",
        "used_fmt": " ({n} kredi)",
        "gen_done": "✅ {label} hazır!{used}{url}\n\nYeni üretim için *menü* yaz.",
        "caption": "✅ Hazır!{used} *menü* yaz.",
        "template_prefill": "📌 *{title}* seçildi.\n_{prompt}_\n\n*tamam* yaz ya da kendi açıklamanı gönder.",
        "prompt_saved": "✅ *{title}* kaydedildi.",
    },
    "en": {
        "ask_language": "🌐 Choose language / Dil seç:",
        "language_saved": "✅ Language: English",
        "ask_code": "First link WhatsApp/Telegram to your FluxVAI account 🔗\n\nfluxvai.app → Settings → *Generate code* → type the 6-digit code here 👇",
        "ask_code_retry": "Please type the *6-digit* code from the site (e.g. 123456).",
        "code_invalid": "❌ Invalid or expired code. Get a new one from the site.",
        "code_taken": "⚠️ This account is linked to another user.",
        "code_ratelimit": "⏳ Too many attempts. Try again later.",
        "pick_from_list": "Please pick from the list 👇",
        "cancelled": "Cancelled. Back to the main menu.",
        "ask_prompt": "✍️ Describe what to create.\n_e.g. \"A person running at sunset, cinematic\"_\n\n💡 *templates* → ready ones · *prompts* → saved ones",
        "prompt_empty": "Please describe what to create.",
        "prompt_too_long": "Too long (max 2000 chars).",
        "ask_duration": "⏱️ Pick a duration:",
        "processing": "🎬 Generation started! I'll send it when ready…",
        "already_submitting": "⏳ Your previous request is processing, please wait.",
        "gen_failed": "❌ Generation failed. Type *menu* to retry.",
        "gen_timeout": "⏳ Taking longer than usual; I'll notify you when ready.",
        "packages_intro": "💳 Choose a credit package:",
        "payment_unavailable": "⚠️ Payments are unavailable right now.",
        "await_payment_nudge": "💳 Waiting for payment. Credits load shortly after. Type *menu*.",
        "generic_error": "⚠️ Something went wrong. Type *menu*.",
        "ask_use_case": "What will you mostly create? 🙌",
        "onboarding_saved": "Great, all set! 🎯",
        "template_intro": "✨ Pick a ready template or start from scratch:",
        "no_templates": "No ready templates, let's start from scratch.",
        "scratch_row": "✍️ Start from scratch",
        "prompt_new_row": "➕ Save new prompt",
        "ask_photo": "📷 Send the photo you want to edit.",
        "photo_received": "📥 Got your photo, preparing…",
        "photo_fail": "❌ Couldn't process the photo, resend please.",
        "ask_edit_prompt": "✍️ How should I change this image? _e.g. make the background night_",
        "expect_photo": "Send a photo first 📷",
        "photo_out_of_flow": "Start via *menu* → ✏️ Edit Image.",
        "more_title": "⚙️ More options:",
        "prompts_title": "📝 Your prompts:",
        "prompts_empty": "No saved prompts. Add one 👇",
        "save_prompt_title": "Type a *title* for the prompt.",
        "save_prompt_text": "Now type the *prompt text*.",
        "no_history": "No generations yet.",
        "history_title": "🕘 Your recent generations:",
        "no_last_gen": "Nothing to repeat yet.",
        "quick_after": "What's next?",
        "greeting": "Hi {name}! 👋\n💰 Balance: *{credits}* credits\n\nWhat would you like to do?",
        "balance": "💰 Your balance: *{credits}* credits.",
        "insufficient": "😕 This needs *{cost}* credits, you have *{balance}*. Pick a package 👇",
        "checkout": "🛒 Payment for *{name}*:\n{url}\n\nCredits load automatically after payment.",
        "credits_loaded": "✅ *{amount}* credits added! 💰 New balance: *{new_balance}*. Type *menu*.",
        "summary": "📋 *Summary*\n• Type: {label}\n• Platform: {platform}\n• Style: {style}{dur}\n• Prompt: {prompt}\n\n💸 Cost: *{cost}* | 💰 Balance: *{balance}*\n\nConfirm?",
        "dur_fmt": "\n• Duration: {duration}s",
        "used_fmt": " ({n} credits)",
        "gen_done": "✅ Your {label} is ready!{used}{url}\n\nType *menu* to create more.",
        "caption": "✅ Ready!{used} Type *menu*.",
        "template_prefill": "📌 *{title}* selected.\n_{prompt}_\n\nType *ok* or send your own description.",
        "prompt_saved": "✅ *{title}* saved.",
    },
    "de": {
        "ask_language": "🌐 Sprache wählen:",
        "language_saved": "✅ Sprache: Deutsch",
        "ask_code": "Verbinde WhatsApp/Telegram zuerst mit deinem FluxVAI-Konto 🔗\n\nfluxvai.app → Einstellungen → *Code erstellen* → 6-stelligen Code hier eingeben 👇",
        "ask_code_retry": "Bitte gib den *6-stelligen* Code von der Seite ein (z.B. 123456).",
        "code_invalid": "❌ Code ungültig oder abgelaufen. Hol dir einen neuen.",
        "code_taken": "⚠️ Dieses Konto ist bereits mit einem anderen Nutzer verknüpft.",
        "code_ratelimit": "⏳ Zu viele Versuche. Bitte später erneut.",
        "pick_from_list": "Bitte aus der Liste wählen 👇",
        "cancelled": "Abgebrochen. Zurück zum Hauptmenü.",
        "ask_prompt": "✍️ Beschreibe, was erstellt werden soll.\n_z.B. \"Person läuft bei Sonnenuntergang, filmisch\"_\n\n💡 *templates* · *prompts*",
        "prompt_empty": "Bitte beschreibe, was erstellt werden soll.",
        "prompt_too_long": "Zu lang (max. 2000 Zeichen).",
        "ask_duration": "⏱️ Dauer wählen:",
        "processing": "🎬 Erstellung gestartet! Ich sende es, sobald es fertig ist…",
        "already_submitting": "⏳ Deine vorige Anfrage läuft, bitte warten.",
        "gen_failed": "❌ Erstellung fehlgeschlagen. *menu* zum Wiederholen.",
        "gen_timeout": "⏳ Dauert länger; ich melde mich, wenn es fertig ist.",
        "packages_intro": "💳 Kreditpaket wählen:",
        "payment_unavailable": "⚠️ Zahlung derzeit nicht verfügbar.",
        "await_payment_nudge": "💳 Warte auf Zahlung. Credits werden danach geladen. *menu*.",
        "generic_error": "⚠️ Etwas ist schiefgelaufen. *menu*.",
        "ask_use_case": "Was erstellst du hauptsächlich? 🙌",
        "onboarding_saved": "Super, eingerichtet! 🎯",
        "template_intro": "✨ Vorlage wählen oder neu beginnen:",
        "no_templates": "Keine Vorlagen, beginnen wir neu.",
        "scratch_row": "✍️ Neu beginnen",
        "prompt_new_row": "➕ Neuen Prompt speichern",
        "ask_photo": "📷 Sende das Foto, das du bearbeiten willst.",
        "photo_received": "📥 Foto erhalten, wird vorbereitet…",
        "photo_fail": "❌ Foto konnte nicht verarbeitet werden, bitte erneut.",
        "ask_edit_prompt": "✍️ Wie soll ich das Bild ändern? _z.B. Hintergrund auf Nacht_",
        "expect_photo": "Sende zuerst ein Foto 📷",
        "photo_out_of_flow": "Starte über *menu* → ✏️ Bild bearbeiten.",
        "more_title": "⚙️ Weitere Optionen:",
        "prompts_title": "📝 Deine Prompts:",
        "prompts_empty": "Keine gespeicherten Prompts. Füge einen hinzu 👇",
        "save_prompt_title": "Gib einen *Titel* für den Prompt ein.",
        "save_prompt_text": "Gib nun den *Prompt-Text* ein.",
        "no_history": "Noch keine Erstellungen.",
        "history_title": "🕘 Deine letzten Erstellungen:",
        "no_last_gen": "Noch nichts zum Wiederholen.",
        "quick_after": "Was als Nächstes?",
        "greeting": "Hallo {name}! 👋\n💰 Guthaben: *{credits}* Credits\n\nWas möchtest du tun?",
        "balance": "💰 Dein Guthaben: *{credits}* Credits.",
        "insufficient": "😕 Benötigt *{cost}* Credits, du hast *{balance}*. Paket wählen 👇",
        "checkout": "🛒 Zahlung für *{name}*:\n{url}\n\nCredits werden nach der Zahlung geladen.",
        "credits_loaded": "✅ *{amount}* Credits hinzugefügt! 💰 Neues Guthaben: *{new_balance}*. *menu*.",
        "summary": "📋 *Übersicht*\n• Typ: {label}\n• Plattform: {platform}\n• Stil: {style}{dur}\n• Prompt: {prompt}\n\n💸 Kosten: *{cost}* | 💰 Guthaben: *{balance}*\n\nBestätigen?",
        "dur_fmt": "\n• Dauer: {duration}s",
        "used_fmt": " ({n} Credits)",
        "gen_done": "✅ Dein {label} ist fertig!{used}{url}\n\n*menu* für mehr.",
        "caption": "✅ Fertig!{used} *menu*.",
        "template_prefill": "📌 *{title}* gewählt.\n_{prompt}_\n\n*ok* schreiben oder eigene Beschreibung senden.",
        "prompt_saved": "✅ *{title}* gespeichert.",
    },
    "ar": {
        "ask_language": "🌐 اختر اللغة:",
        "language_saved": "✅ اللغة: العربية",
        "ask_code": "اربط واتساب/تيليجرام بحسابك في FluxVAI أولاً 🔗\n\nfluxvai.app ← الإعدادات ← *إنشاء رمز* ← اكتب الرمز المكوّن من 6 أرقام هنا 👇",
        "ask_code_retry": "اكتب الرمز المكوّن من *6 أرقام* من الموقع (مثال 123456).",
        "code_invalid": "❌ الرمز غير صالح أو منتهٍ. احصل على رمز جديد.",
        "code_taken": "⚠️ هذا الحساب مرتبط بمستخدم آخر.",
        "code_ratelimit": "⏳ محاولات كثيرة. حاول لاحقاً.",
        "pick_from_list": "اختر من القائمة 👇",
        "cancelled": "تم الإلغاء. عدنا إلى القائمة.",
        "ask_prompt": "✍️ صف ما تريد إنشاءه.\n_مثال: \"شخص يركض عند الغروب، سينمائي\"_\n\n💡 *templates* · *prompts*",
        "prompt_empty": "من فضلك صف ما تريد إنشاءه.",
        "prompt_too_long": "طويل جداً (2000 حرف كحد أقصى).",
        "ask_duration": "⏱️ اختر المدة:",
        "processing": "🎬 بدأ الإنشاء! سأرسله عند الجهوزية…",
        "already_submitting": "⏳ طلبك السابق قيد المعالجة، انتظر.",
        "gen_failed": "❌ فشل الإنشاء. اكتب *menu* للمحاولة.",
        "gen_timeout": "⏳ يستغرق وقتاً أطول؛ سأخبرك عند الجهوزية.",
        "packages_intro": "💳 اختر باقة أرصدة:",
        "payment_unavailable": "⚠️ الدفع غير متاح حالياً.",
        "await_payment_nudge": "💳 بانتظار الدفع. ستُضاف الأرصدة بعده. اكتب *menu*.",
        "generic_error": "⚠️ حدث خطأ ما. اكتب *menu*.",
        "ask_use_case": "ماذا ستُنشئ غالباً؟ 🙌",
        "onboarding_saved": "رائع، تم الضبط! 🎯",
        "template_intro": "✨ اختر قالباً جاهزاً أو ابدأ من الصفر:",
        "no_templates": "لا قوالب، لنبدأ من الصفر.",
        "scratch_row": "✍️ ابدأ من الصفر",
        "prompt_new_row": "➕ حفظ prompt جديد",
        "ask_photo": "📷 أرسل الصورة التي تريد تعديلها.",
        "photo_received": "📥 استلمت الصورة، جارٍ التحضير…",
        "photo_fail": "❌ تعذّر معالجة الصورة، أعد الإرسال.",
        "ask_edit_prompt": "✍️ كيف أعدّل هذه الصورة؟ _مثال: اجعل الخلفية ليلاً_",
        "expect_photo": "أرسل صورة أولاً 📷",
        "photo_out_of_flow": "ابدأ عبر *menu* ← ✏️ تعديل صورة.",
        "more_title": "⚙️ خيارات أخرى:",
        "prompts_title": "📝 prompts الخاصة بك:",
        "prompts_empty": "لا prompts محفوظة. أضف واحداً 👇",
        "save_prompt_title": "اكتب *عنواناً* للـ prompt.",
        "save_prompt_text": "الآن اكتب *نص الـ prompt*.",
        "no_history": "لا إنشاءات بعد.",
        "history_title": "🕘 آخر إنشاءاتك:",
        "no_last_gen": "لا شيء لإعادته بعد.",
        "quick_after": "ما التالي؟",
        "greeting": "مرحباً {name}! 👋\n💰 الرصيد: *{credits}* نقطة\n\nماذا تريد أن تفعل؟",
        "balance": "💰 رصيدك: *{credits}* نقطة.",
        "insufficient": "😕 يحتاج *{cost}* نقطة، لديك *{balance}*. اختر باقة 👇",
        "checkout": "🛒 الدفع لـ *{name}*:\n{url}\n\nستُضاف النقاط تلقائياً بعد الدفع.",
        "credits_loaded": "✅ أُضيفت *{amount}* نقطة! 💰 الرصيد الجديد: *{new_balance}*. اكتب *menu*.",
        "summary": "📋 *الملخص*\n• النوع: {label}\n• المنصة: {platform}\n• النمط: {style}{dur}\n• الوصف: {prompt}\n\n💸 التكلفة: *{cost}* | 💰 الرصيد: *{balance}*\n\nتأكيد؟",
        "dur_fmt": "\n• المدة: {duration} ث",
        "used_fmt": " ({n} نقطة)",
        "gen_done": "✅ {label} جاهز!{used}{url}\n\nاكتب *menu* للمزيد.",
        "caption": "✅ جاهز!{used} اكتب *menu*.",
        "template_prefill": "📌 تم اختيار *{title}*.\n_{prompt}_\n\nاكتب *tamam* أو أرسل وصفك.",
        "prompt_saved": "✅ تم حفظ *{title}*.",
    },
    "es": {
        "ask_language": "🌐 Elige idioma:",
        "language_saved": "✅ Idioma: Español",
        "ask_code": "Vincula WhatsApp/Telegram a tu cuenta FluxVAI 🔗\n\nfluxvai.app → Ajustes → *Generar código* → escribe el código de 6 dígitos aquí 👇",
        "ask_code_retry": "Escribe el código de *6 dígitos* del sitio (ej. 123456).",
        "code_invalid": "❌ Código inválido o caducado. Obtén uno nuevo.",
        "code_taken": "⚠️ Esta cuenta está vinculada a otro usuario.",
        "code_ratelimit": "⏳ Demasiados intentos. Inténtalo más tarde.",
        "pick_from_list": "Elige de la lista 👇",
        "cancelled": "Cancelado. Volvemos al menú.",
        "ask_prompt": "✍️ Describe qué crear.\n_ej. \"Persona corriendo al atardecer, cinematográfico\"_\n\n💡 *templates* · *prompts*",
        "prompt_empty": "Describe qué quieres crear.",
        "prompt_too_long": "Demasiado largo (máx. 2000 caracteres).",
        "ask_duration": "⏱️ Elige duración:",
        "processing": "🎬 ¡Generación iniciada! Te lo envío cuando esté listo…",
        "already_submitting": "⏳ Tu solicitud anterior está en proceso, espera.",
        "gen_failed": "❌ Falló la generación. Escribe *menu*.",
        "gen_timeout": "⏳ Tarda más de lo normal; te aviso al terminar.",
        "packages_intro": "💳 Elige un paquete de créditos:",
        "payment_unavailable": "⚠️ Pagos no disponibles ahora.",
        "await_payment_nudge": "💳 Esperando el pago. Los créditos se cargan después. *menu*.",
        "generic_error": "⚠️ Algo salió mal. Escribe *menu*.",
        "ask_use_case": "¿Qué crearás principalmente? 🙌",
        "onboarding_saved": "¡Genial, listo! 🎯",
        "template_intro": "✨ Elige una plantilla o empieza de cero:",
        "no_templates": "Sin plantillas, empecemos de cero.",
        "scratch_row": "✍️ Empezar de cero",
        "prompt_new_row": "➕ Guardar nuevo prompt",
        "ask_photo": "📷 Envía la foto que quieres editar.",
        "photo_received": "📥 Foto recibida, preparando…",
        "photo_fail": "❌ No pude procesar la foto, reenvíala.",
        "ask_edit_prompt": "✍️ ¿Cómo cambio esta imagen? _ej. fondo de noche_",
        "expect_photo": "Envía una foto primero 📷",
        "photo_out_of_flow": "Empieza con *menu* → ✏️ Editar imagen.",
        "more_title": "⚙️ Más opciones:",
        "prompts_title": "📝 Tus prompts:",
        "prompts_empty": "Sin prompts guardados. Añade uno 👇",
        "save_prompt_title": "Escribe un *título* para el prompt.",
        "save_prompt_text": "Ahora escribe el *texto del prompt*.",
        "no_history": "Aún no hay generaciones.",
        "history_title": "🕘 Tus generaciones recientes:",
        "no_last_gen": "Nada que repetir aún.",
        "quick_after": "¿Qué sigue?",
        "greeting": "¡Hola {name}! 👋\n💰 Saldo: *{credits}* créditos\n\n¿Qué quieres hacer?",
        "balance": "💰 Tu saldo: *{credits}* créditos.",
        "insufficient": "😕 Necesita *{cost}* créditos, tienes *{balance}*. Elige un paquete 👇",
        "checkout": "🛒 Pago de *{name}*:\n{url}\n\nLos créditos se cargan tras el pago.",
        "credits_loaded": "✅ ¡*{amount}* créditos añadidos! 💰 Nuevo saldo: *{new_balance}*. *menu*.",
        "summary": "📋 *Resumen*\n• Tipo: {label}\n• Plataforma: {platform}\n• Estilo: {style}{dur}\n• Prompt: {prompt}\n\n💸 Costo: *{cost}* | 💰 Saldo: *{balance}*\n\n¿Confirmar?",
        "dur_fmt": "\n• Duración: {duration}s",
        "used_fmt": " ({n} créditos)",
        "gen_done": "✅ ¡Tu {label} está listo!{used}{url}\n\nEscribe *menu* para más.",
        "caption": "✅ ¡Listo!{used} *menu*.",
        "template_prefill": "📌 *{title}* elegido.\n_{prompt}_\n\nEscribe *ok* o envía tu descripción.",
        "prompt_saved": "✅ *{title}* guardado.",
    },
    "fr": {
        "ask_language": "🌐 Choisis la langue :",
        "language_saved": "✅ Langue : Français",
        "ask_code": "Relie WhatsApp/Telegram à ton compte FluxVAI 🔗\n\nfluxvai.app → Paramètres → *Générer un code* → saisis le code à 6 chiffres ici 👇",
        "ask_code_retry": "Saisis le code à *6 chiffres* du site (ex. 123456).",
        "code_invalid": "❌ Code invalide ou expiré. Prends-en un nouveau.",
        "code_taken": "⚠️ Ce compte est lié à un autre utilisateur.",
        "code_ratelimit": "⏳ Trop de tentatives. Réessaie plus tard.",
        "pick_from_list": "Choisis dans la liste 👇",
        "cancelled": "Annulé. Retour au menu.",
        "ask_prompt": "✍️ Décris ce que tu veux créer.\n_ex. \"Une personne courant au coucher du soleil, cinématique\"_\n\n💡 *templates* · *prompts*",
        "prompt_empty": "Décris ce que tu veux créer.",
        "prompt_too_long": "Trop long (max 2000 caractères).",
        "ask_duration": "⏱️ Choisis la durée :",
        "processing": "🎬 Génération lancée ! Je l'envoie dès que c'est prêt…",
        "already_submitting": "⏳ Ta requête précédente est en cours, patiente.",
        "gen_failed": "❌ Échec de la génération. Écris *menu*.",
        "gen_timeout": "⏳ Ça prend plus de temps ; je te préviens quand c'est prêt.",
        "packages_intro": "💳 Choisis un pack de crédits :",
        "payment_unavailable": "⚠️ Paiement indisponible pour le moment.",
        "await_payment_nudge": "💳 En attente du paiement. Les crédits arrivent après. *menu*.",
        "generic_error": "⚠️ Une erreur est survenue. Écris *menu*.",
        "ask_use_case": "Que vas-tu créer surtout ? 🙌",
        "onboarding_saved": "Parfait, c'est réglé ! 🎯",
        "template_intro": "✨ Choisis un modèle ou pars de zéro :",
        "no_templates": "Pas de modèle, partons de zéro.",
        "scratch_row": "✍️ Partir de zéro",
        "prompt_new_row": "➕ Enregistrer un prompt",
        "ask_photo": "📷 Envoie la photo à modifier.",
        "photo_received": "📥 Photo reçue, préparation…",
        "photo_fail": "❌ Impossible de traiter la photo, renvoie-la.",
        "ask_edit_prompt": "✍️ Comment modifier cette image ? _ex. fond de nuit_",
        "expect_photo": "Envoie d'abord une photo 📷",
        "photo_out_of_flow": "Commence via *menu* → ✏️ Modifier l'image.",
        "more_title": "⚙️ Plus d'options :",
        "prompts_title": "📝 Tes prompts :",
        "prompts_empty": "Aucun prompt enregistré. Ajoutes-en un 👇",
        "save_prompt_title": "Saisis un *titre* pour le prompt.",
        "save_prompt_text": "Saisis maintenant le *texte du prompt*.",
        "no_history": "Pas encore de générations.",
        "history_title": "🕘 Tes générations récentes :",
        "no_last_gen": "Rien à répéter pour l'instant.",
        "quick_after": "Et ensuite ?",
        "greeting": "Salut {name} ! 👋\n💰 Solde : *{credits}* crédits\n\nQue veux-tu faire ?",
        "balance": "💰 Ton solde : *{credits}* crédits.",
        "insufficient": "😕 Il faut *{cost}* crédits, tu as *{balance}*. Choisis un pack 👇",
        "checkout": "🛒 Paiement de *{name}* :\n{url}\n\nLes crédits arrivent après le paiement.",
        "credits_loaded": "✅ *{amount}* crédits ajoutés ! 💰 Nouveau solde : *{new_balance}*. *menu*.",
        "summary": "📋 *Résumé*\n• Type : {label}\n• Plateforme : {platform}\n• Style : {style}{dur}\n• Prompt : {prompt}\n\n💸 Coût : *{cost}* | 💰 Solde : *{balance}*\n\nConfirmer ?",
        "dur_fmt": "\n• Durée : {duration}s",
        "used_fmt": " ({n} crédits)",
        "gen_done": "✅ Ton {label} est prêt !{used}{url}\n\nÉcris *menu* pour plus.",
        "caption": "✅ Prêt !{used} *menu*.",
        "template_prefill": "📌 *{title}* choisi.\n_{prompt}_\n\nÉcris *ok* ou envoie ta description.",
        "prompt_saved": "✅ *{title}* enregistré.",
    },
    "ru": {
        "ask_language": "🌐 Выбери язык:",
        "language_saved": "✅ Язык: Русский",
        "ask_code": "Сначала привяжи WhatsApp/Telegram к аккаунту FluxVAI 🔗\n\nfluxvai.app → Настройки → *Создать код* → введи 6-значный код здесь 👇",
        "ask_code_retry": "Введи *6-значный* код с сайта (напр. 123456).",
        "code_invalid": "❌ Код неверен или истёк. Получи новый.",
        "code_taken": "⚠️ Этот аккаунт привязан к другому пользователю.",
        "code_ratelimit": "⏳ Слишком много попыток. Позже.",
        "pick_from_list": "Выбери из списка 👇",
        "cancelled": "Отменено. Возврат в меню.",
        "ask_prompt": "✍️ Опиши, что создать.\n_напр. \"Человек бежит на закате, кинематографично\"_\n\n💡 *templates* · *prompts*",
        "prompt_empty": "Опиши, что нужно создать.",
        "prompt_too_long": "Слишком длинно (макс. 2000 символов).",
        "ask_duration": "⏱️ Выбери длительность:",
        "processing": "🎬 Генерация началась! Пришлю, когда будет готово…",
        "already_submitting": "⏳ Предыдущий запрос обрабатывается, подожди.",
        "gen_failed": "❌ Сбой генерации. Напиши *menu*.",
        "gen_timeout": "⏳ Дольше обычного; сообщу, когда будет готово.",
        "packages_intro": "💳 Выбери пакет кредитов:",
        "payment_unavailable": "⚠️ Оплата сейчас недоступна.",
        "await_payment_nudge": "💳 Жду оплату. Кредиты зачислятся после. *menu*.",
        "generic_error": "⚠️ Что-то пошло не так. Напиши *menu*.",
        "ask_use_case": "Что будешь создавать чаще? 🙌",
        "onboarding_saved": "Отлично, настроил! 🎯",
        "template_intro": "✨ Выбери шаблон или начни с нуля:",
        "no_templates": "Шаблонов нет, начнём с нуля.",
        "scratch_row": "✍️ Начать с нуля",
        "prompt_new_row": "➕ Сохранить промпт",
        "ask_photo": "📷 Пришли фото для редактирования.",
        "photo_received": "📥 Фото получено, готовлю…",
        "photo_fail": "❌ Не удалось обработать фото, пришли ещё раз.",
        "ask_edit_prompt": "✍️ Как изменить это изображение? _напр. сделай фон ночным_",
        "expect_photo": "Сначала пришли фото 📷",
        "photo_out_of_flow": "Начни через *menu* → ✏️ Редактировать фото.",
        "more_title": "⚙️ Другие опции:",
        "prompts_title": "📝 Твои промпты:",
        "prompts_empty": "Нет сохранённых промптов. Добавь 👇",
        "save_prompt_title": "Введи *название* промпта.",
        "save_prompt_text": "Теперь введи *текст промпта*.",
        "no_history": "Пока нет генераций.",
        "history_title": "🕘 Последние генерации:",
        "no_last_gen": "Пока нечего повторять.",
        "quick_after": "Что дальше?",
        "greeting": "Привет, {name}! 👋\n💰 Баланс: *{credits}* кредитов\n\nЧто хочешь сделать?",
        "balance": "💰 Твой баланс: *{credits}* кредитов.",
        "insufficient": "😕 Нужно *{cost}* кредитов, у тебя *{balance}*. Выбери пакет 👇",
        "checkout": "🛒 Оплата *{name}*:\n{url}\n\nКредиты зачислятся после оплаты.",
        "credits_loaded": "✅ *{amount}* кредитов добавлено! 💰 Новый баланс: *{new_balance}*. *menu*.",
        "summary": "📋 *Сводка*\n• Тип: {label}\n• Платформа: {platform}\n• Стиль: {style}{dur}\n• Промпт: {prompt}\n\n💸 Стоимость: *{cost}* | 💰 Баланс: *{balance}*\n\nПодтвердить?",
        "dur_fmt": "\n• Длительность: {duration}с",
        "used_fmt": " ({n} кредитов)",
        "gen_done": "✅ Твой {label} готов!{used}{url}\n\nНапиши *menu* для нового.",
        "caption": "✅ Готово!{used} *menu*.",
        "template_prefill": "📌 Выбран *{title}*.\n_{prompt}_\n\nНапиши *ok* или пришли своё описание.",
        "prompt_saved": "✅ *{title}* сохранён.",
    },
}

# Gallery + account strings, merged into S (kept separate to avoid editing 7 blocks).
_EXTRA = {
    "tr": {"gallery_pick": "🗂️ Hangi türü görmek istersin?", "no_items": "Bu kategoride henüz üretim yok.", "all_label": "🗂️ Tümü",
           "account": "💰 Bakiye: *{credits}* kredi\n\n📊 *Hesabım*\n• Toplam üretim: {total}\n• Tamamlanan: {done}\n• İşlenen: {processing}\n• Harcanan kredi: {used}"},
    "en": {"gallery_pick": "🗂️ Which type to browse?", "no_items": "No generations in this category yet.", "all_label": "🗂️ All",
           "account": "💰 Balance: *{credits}* credits\n\n📊 *Account*\n• Total: {total}\n• Completed: {done}\n• Processing: {processing}\n• Credits spent: {used}"},
    "de": {"gallery_pick": "🗂️ Welcher Typ?", "no_items": "Noch keine Erstellungen in dieser Kategorie.", "all_label": "🗂️ Alle",
           "account": "💰 Guthaben: *{credits}* Credits\n\n📊 *Konto*\n• Gesamt: {total}\n• Fertig: {done}\n• In Arbeit: {processing}\n• Ausgegeben: {used}"},
    "ar": {"gallery_pick": "🗂️ أي نوع تريد تصفّحه؟", "no_items": "لا إنشاءات في هذه الفئة بعد.", "all_label": "🗂️ الكل",
           "account": "💰 الرصيد: *{credits}* نقطة\n\n📊 *حسابي*\n• الإجمالي: {total}\n• المكتمل: {done}\n• قيد المعالجة: {processing}\n• المُنفق: {used}"},
    "es": {"gallery_pick": "🗂️ ¿Qué tipo ver?", "no_items": "Aún no hay generaciones en esta categoría.", "all_label": "🗂️ Todos",
           "account": "💰 Saldo: *{credits}* créditos\n\n📊 *Cuenta*\n• Total: {total}\n• Completadas: {done}\n• En proceso: {processing}\n• Créditos gastados: {used}"},
    "fr": {"gallery_pick": "🗂️ Quel type afficher ?", "no_items": "Aucune génération dans cette catégorie.", "all_label": "🗂️ Tous",
           "account": "💰 Solde : *{credits}* crédits\n\n📊 *Compte*\n• Total : {total}\n• Terminées : {done}\n• En cours : {processing}\n• Crédits dépensés : {used}"},
    "ru": {"gallery_pick": "🗂️ Какой тип показать?", "no_items": "В этой категории пока нет генераций.", "all_label": "🗂️ Все",
           "account": "💰 Баланс: *{credits}* кредитов\n\n📊 *Аккаунт*\n• Всего: {total}\n• Готово: {done}\n• В процессе: {processing}\n• Потрачено: {used}"},
}
for _lg, _kv in _EXTRA.items():
    S[_lg].update(_kv)

# Shown when the FluxVAI backend is unreachable (e.g. before the site is live).
for _lg, _msg in {
    "tr": "⚠️ Servis hazırlanıyor, birazdan tekrar dene.",
    "en": "⚠️ Service is starting up, please try again shortly.",
    "de": "⚠️ Dienst startet, bitte gleich erneut versuchen.",
    "ar": "⚠️ الخدمة قيد التشغيل، حاول بعد قليل.",
    "es": "⚠️ El servicio se está iniciando, inténtalo en breve.",
    "fr": "⚠️ Le service démarre, réessaie bientôt.",
    "ru": "⚠️ Сервис запускается, попробуй чуть позже.",
}.items():
    S[_lg]["service_unavailable"] = _msg

# Richer home/welcome banner (used by greeting()).
for _lg, _msg in {
    "tr": "✨ *FluxVAI Stüdyo*\nMerhaba {name}! 👋  💰 *{credits}* kredi\n\n🎬 Video · 🖼️ Görsel · 🎵 Ses · 📦 3D · ✏️ Düzenle\nNe yapmak istersin? 👇",
    "en": "✨ *FluxVAI Studio*\nHi {name}! 👋  💰 *{credits}* credits\n\n🎬 Video · 🖼️ Image · 🎵 Audio · 📦 3D · ✏️ Edit\nWhat would you like to do? 👇",
    "de": "✨ *FluxVAI Studio*\nHallo {name}! 👋  💰 *{credits}* Credits\n\n🎬 Video · 🖼️ Bild · 🎵 Audio · 📦 3D · ✏️ Bearbeiten\nWas möchtest du tun? 👇",
    "ar": "✨ *FluxVAI ستوديو*\nمرحباً {name}! 👋  💰 *{credits}* نقطة\n\n🎬 فيديو · 🖼️ صورة · 🎵 صوت · 📦 3D · ✏️ تعديل\nماذا تريد أن تفعل؟ 👇",
    "es": "✨ *FluxVAI Studio*\n¡Hola {name}! 👋  💰 *{credits}* créditos\n\n🎬 Vídeo · 🖼️ Imagen · 🎵 Audio · 📦 3D · ✏️ Editar\n¿Qué quieres hacer? 👇",
    "fr": "✨ *FluxVAI Studio*\nSalut {name} ! 👋  💰 *{credits}* crédits\n\n🎬 Vidéo · 🖼️ Image · 🎵 Audio · 📦 3D · ✏️ Modifier\nQue veux-tu faire ? 👇",
    "ru": "✨ *FluxVAI Студия*\nПривет, {name}! 👋  💰 *{credits}* кредитов\n\n🎬 Видео · 🖼️ Фото · 🎵 Аудио · 📦 3D · ✏️ Правка\nЧто хочешь сделать? 👇",
}.items():
    S[_lg]["home"] = _msg


# ── localized labels ──────────────────────────────────────────────────
_TYPE_LABELS = {
    "tr": {"video": "video", "image": "görsel", "audio": "ses", "3d": "3D model"},
    "en": {"video": "video", "image": "image", "audio": "audio", "3d": "3D model"},
    "de": {"video": "Video", "image": "Bild", "audio": "Audio", "3d": "3D-Modell"},
    "ar": {"video": "فيديو", "image": "صورة", "audio": "صوت", "3d": "نموذج 3D"},
    "es": {"video": "vídeo", "image": "imagen", "audio": "audio", "3d": "modelo 3D"},
    "fr": {"video": "vidéo", "image": "image", "audio": "audio", "3d": "modèle 3D"},
    "ru": {"video": "видео", "image": "изображение", "audio": "аудио", "3d": "3D-модель"},
}

_TYPES = {  # key -> {lang: (emoji_label, desc)}
    "video": {"tr": ("🎬 Video", "Sosyal video"), "en": ("🎬 Video", "Social video"), "de": ("🎬 Video", "Social-Video"),
              "ar": ("🎬 فيديو", "فيديو اجتماعي"), "es": ("🎬 Vídeo", "Vídeo social"), "fr": ("🎬 Vidéo", "Vidéo sociale"), "ru": ("🎬 Видео", "Соц-видео")},
    "image": {"tr": ("🖼️ Görsel", "Tek kare"), "en": ("🖼️ Image", "Single image"), "de": ("🖼️ Bild", "Einzelbild"),
              "ar": ("🖼️ صورة", "صورة واحدة"), "es": ("🖼️ Imagen", "Una imagen"), "fr": ("🖼️ Image", "Une image"), "ru": ("🖼️ Изображение", "Одно фото")},
    "imgedit": {"tr": ("✏️ Görsel Düzenle", "Fotoğrafını yükle"), "en": ("✏️ Edit Image", "Upload your photo"), "de": ("✏️ Bild bearbeiten", "Foto hochladen"),
                "ar": ("✏️ تعديل صورة", "ارفع صورتك"), "es": ("✏️ Editar imagen", "Sube tu foto"), "fr": ("✏️ Modifier l'image", "Envoie ta photo"), "ru": ("✏️ Редактировать", "Загрузи фото")},
    "audio": {"tr": ("🎵 Ses", "Seslendirme"), "en": ("🎵 Audio", "Voiceover"), "de": ("🎵 Audio", "Voiceover"),
              "ar": ("🎵 صوت", "تعليق صوتي"), "es": ("🎵 Audio", "Voz"), "fr": ("🎵 Audio", "Voix off"), "ru": ("🎵 Аудио", "Озвучка")},
    "3d": {"tr": ("📦 3D Model", "3B render"), "en": ("📦 3D Model", "3D render"), "de": ("📦 3D-Modell", "3D-Render"),
           "ar": ("📦 نموذج 3D", "تصيير 3D"), "es": ("📦 Modelo 3D", "Render 3D"), "fr": ("📦 Modèle 3D", "Rendu 3D"), "ru": ("📦 3D-модель", "3D-рендер")},
}
_TYPE_ORDER_BY_USECASE = {
    "ecommerce": ["image", "imgedit", "3d", "video", "audio"],
    "creator": ["video", "imgedit", "image", "audio", "3d"],
    "influencer": ["video", "image", "imgedit", "audio", "3d"],
    "corporate": ["video", "image", "imgedit", "3d", "audio"],
}
_DEFAULT_TYPE_ORDER = ["video", "image", "imgedit", "audio", "3d"]

_GENERAL = {"tr": "Genel", "en": "General", "de": "Allgemein", "ar": "عام", "es": "General", "fr": "Général", "ru": "Общее"}
_PLATFORMS = [("YouTube", "16:9"), ("Instagram", "9:16"), ("TikTok", "9:16"), ("LinkedIn", "1:1"), ("X", "16:9"), ("Universal", "—")]

_STYLES = {
    "tr": [("cinematic", "Sinematik"), ("realistic", "Gerçekçi"), ("animation", "Animasyon"), ("minimal", "Minimal"), ("vintage", "Retro")],
    "en": [("cinematic", "Cinematic"), ("realistic", "Realistic"), ("animation", "Animation"), ("minimal", "Minimal"), ("vintage", "Vintage")],
    "de": [("cinematic", "Filmisch"), ("realistic", "Realistisch"), ("animation", "Animation"), ("minimal", "Minimal"), ("vintage", "Vintage")],
    "ar": [("cinematic", "سينمائي"), ("realistic", "واقعي"), ("animation", "رسوم"), ("minimal", "بسيط"), ("vintage", "ريترو")],
    "es": [("cinematic", "Cinematográfico"), ("realistic", "Realista"), ("animation", "Animación"), ("minimal", "Minimalista"), ("vintage", "Vintage")],
    "fr": [("cinematic", "Cinématique"), ("realistic", "Réaliste"), ("animation", "Animation"), ("minimal", "Minimal"), ("vintage", "Vintage")],
    "ru": [("cinematic", "Кино"), ("realistic", "Реалистичный"), ("animation", "Анимация"), ("minimal", "Минимал"), ("vintage", "Ретро")],
}

_USE_CASES = {
    "tr": [("creator", "İçerik Üreticisi"), ("ecommerce", "E-ticaret"), ("influencer", "Influencer"), ("corporate", "Kurumsal"), ("skip", "Şimdilik geç")],
    "en": [("creator", "Content Creator"), ("ecommerce", "E-commerce"), ("influencer", "Influencer"), ("corporate", "Corporate"), ("skip", "Skip for now")],
    "de": [("creator", "Content-Creator"), ("ecommerce", "E-Commerce"), ("influencer", "Influencer"), ("corporate", "Unternehmen"), ("skip", "Später")],
    "ar": [("creator", "صانع محتوى"), ("ecommerce", "تجارة إلكترونية"), ("influencer", "مؤثر"), ("corporate", "شركات"), ("skip", "لاحقاً")],
    "es": [("creator", "Creador"), ("ecommerce", "E-commerce"), ("influencer", "Influencer"), ("corporate", "Empresa"), ("skip", "Más tarde")],
    "fr": [("creator", "Créateur"), ("ecommerce", "E-commerce"), ("influencer", "Influenceur"), ("corporate", "Entreprise"), ("skip", "Plus tard")],
    "ru": [("creator", "Контент-креатор"), ("ecommerce", "E-commerce"), ("influencer", "Инфлюенсер"), ("corporate", "Бизнес"), ("skip", "Позже")],
}

# Main menu = 3 buttons; (id, {lang: label})
_MENU_BTN = [
    ("nav:gen", {"tr": "🎬 Üret", "en": "🎬 Create", "de": "🎬 Erstellen", "ar": "🎬 إنشاء", "es": "🎬 Crear", "fr": "🎬 Créer", "ru": "🎬 Создать"}),
    ("nav:edit", {"tr": "✏️ Düzenle", "en": "✏️ Edit", "de": "✏️ Bearbeiten", "ar": "✏️ تعديل", "es": "✏️ Editar", "fr": "✏️ Modifier", "ru": "✏️ Изменить"}),
    ("nav:more", {"tr": "⚙️ Diğer", "en": "⚙️ More", "de": "⚙️ Mehr", "ar": "⚙️ المزيد", "es": "⚙️ Más", "fr": "⚙️ Plus", "ru": "⚙️ Ещё"}),
]
# More menu rows; (id, {lang: title})
_MORE = [
    ("act:repeat", {"tr": "🔁 Tekrar üret", "en": "🔁 Repeat last", "de": "🔁 Wiederholen", "ar": "🔁 إعادة", "es": "🔁 Repetir", "fr": "🔁 Répéter", "ru": "🔁 Повторить"}),
    ("nav:prompts", {"tr": "📝 Promptlarım", "en": "📝 My Prompts", "de": "📝 Meine Prompts", "ar": "📝 prompts", "es": "📝 Mis Prompts", "fr": "📝 Mes Prompts", "ru": "📝 Промпты"}),
    ("nav:buy", {"tr": "💳 Kredi Al", "en": "💳 Buy Credits", "de": "💳 Credits kaufen", "ar": "💳 شراء أرصدة", "es": "💳 Comprar créditos", "fr": "💳 Acheter", "ru": "💳 Купить"}),
    ("nav:balance", {"tr": "💰 Hesabım", "en": "💰 Account", "de": "💰 Konto", "ar": "💰 حسابي", "es": "💰 Cuenta", "fr": "💰 Compte", "ru": "💰 Аккаунт"}),
    ("nav:history", {"tr": "🗂️ Galerim", "en": "🗂️ Gallery", "de": "🗂️ Galerie", "ar": "🗂️ معرضي", "es": "🗂️ Galería", "fr": "🗂️ Galerie", "ru": "🗂️ Галерея"}),
    ("nav:lang", {"tr": "🌐 Dil", "en": "🌐 Language", "de": "🌐 Sprache", "ar": "🌐 اللغة", "es": "🌐 Idioma", "fr": "🌐 Langue", "ru": "🌐 Язык"}),
    ("nav:help", {"tr": "ℹ️ Yardım", "en": "ℹ️ Help", "de": "ℹ️ Hilfe", "ar": "ℹ️ مساعدة", "es": "ℹ️ Ayuda", "fr": "ℹ️ Aide", "ru": "ℹ️ Помощь"}),
]
# post-result quick actions (3 buttons)
_QUICK = [
    ("act:repeat", {"tr": "🔁 Tekrar", "en": "🔁 Repeat", "de": "🔁 Nochmal", "ar": "🔁 إعادة", "es": "🔁 Repetir", "fr": "🔁 Répéter", "ru": "🔁 Повтор"}),
    ("nav:gen", {"tr": "🎬 Yeni", "en": "🎬 New", "de": "🎬 Neu", "ar": "🎬 جديد", "es": "🎬 Nuevo", "fr": "🎬 Nouveau", "ru": "🎬 Новый"}),
    ("nav:menu", {"tr": "📋 Menü", "en": "📋 Menu", "de": "📋 Menü", "ar": "📋 القائمة", "es": "📋 Menú", "fr": "📋 Menu", "ru": "📋 Меню"}),
]

_HELP = {
    "tr": "ℹ️ *Komutlar*\n/menu /uret /duzenle /promptlarim /sablonlar /tekrar /kredi /bakiye /gecmis /dil /iptal /yardim",
    "en": "ℹ️ *Commands*\n/menu /create /edit /prompts /templates /repeat /buy /balance /history /lang /cancel /help",
    "de": "ℹ️ *Befehle*\n/menu /create /edit /prompts /templates /repeat /buy /balance /history /lang /cancel /help",
    "ar": "ℹ️ *الأوامر*\n/menu /create /edit /prompts /templates /repeat /buy /balance /history /lang /cancel /help",
    "es": "ℹ️ *Comandos*\n/menu /create /edit /prompts /templates /repeat /buy /balance /history /lang /cancel /help",
    "fr": "ℹ️ *Commandes*\n/menu /create /edit /prompts /templates /repeat /buy /balance /history /lang /cancel /help",
    "ru": "ℹ️ *Команды*\n/menu /create /edit /prompts /templates /repeat /buy /balance /history /lang /cancel /help",
}


# ── API ───────────────────────────────────────────────────────────────
def _L(lang: str) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


def t(lang: str, key: str) -> str:
    lang = _L(lang)
    return S[lang].get(key) or S[DEFAULT_LANG].get(key, key)


def type_label(lang: str, gen_type: str) -> str:
    return _TYPE_LABELS[_L(lang)].get(gen_type, gen_type)


def greeting(lang, name, credits):
    return t(lang, "home").format(name=name, credits=credits)


def balance_msg(lang, credits):
    return t(lang, "balance").format(credits=credits)


def insufficient(lang, cost, balance):
    return t(lang, "insufficient").format(cost=cost, balance=balance)


def checkout_link(lang, name, url):
    return t(lang, "checkout").format(name=name, url=url)


def credits_loaded(lang, amount, new_balance):
    return t(lang, "credits_loaded").format(amount=amount, new_balance=new_balance)


def template_prefill(lang, title, prompt):
    return t(lang, "template_prefill").format(title=title, prompt=(prompt or "")[:200])


def prompt_saved(lang, title):
    return t(lang, "prompt_saved").format(title=title)


def confirm_summary(lang, gen_type, platform, prompt, style, duration, cost, balance):
    lang = _L(lang)
    dur = t(lang, "dur_fmt").format(duration=duration) if duration else ""
    return t(lang, "summary").format(label=type_label(lang, gen_type), platform=platform, style=style,
                                     dur=dur, prompt=(prompt or "")[:120], cost=cost, balance=balance)


def gen_done(lang, gen_type, credits_used, url):
    lang = _L(lang)
    used = t(lang, "used_fmt").format(n=credits_used) if credits_used else ""
    return t(lang, "gen_done").format(label=type_label(lang, gen_type), used=used, url=(f"\n🔗 {url}" if url else ""))


def gen_done_caption(lang, credits_used):
    lang = _L(lang)
    used = t(lang, "used_fmt").format(n=credits_used) if credits_used else ""
    return t(lang, "caption").format(used=used)


def language_rows():
    return [(f"lang:{code}", name, "") for code, name in LANG_NAMES.items()]


def types(lang, use_case=""):
    lang = _L(lang)
    order = _TYPE_ORDER_BY_USECASE.get(use_case, _DEFAULT_TYPE_ORDER)
    return [(f"type:{k}", _TYPES[k][lang][0], _TYPES[k][lang][1]) for k in order]


def type_quick(lang):
    lang = _L(lang)
    more = {"tr": "➕ Diğer", "en": "➕ More", "de": "➕ Mehr", "ar": "➕ المزيد", "es": "➕ Más", "fr": "➕ Plus", "ru": "➕ Ещё"}[lang]
    return [(f"type:video", _TYPES["video"][lang][0]), ("type:image", _TYPES["image"][lang][0]), ("type:more", more)]


def platforms(lang):
    lang = _L(lang)
    return [(f"plat:{pid}", _GENERAL[lang] if pid == "Universal" else ("X (Twitter)" if pid == "X" else pid), desc)
            for pid, desc in _PLATFORMS]


def styles(lang):
    return [(f"style:{sid}", label, "") for sid, label in _STYLES[_L(lang)]]


def use_cases(lang):
    return [(f"onb:{k}", label, "") for k, label in _USE_CASES[_L(lang)]]


def main_menu_buttons(lang):
    return [(bid, labels[_L(lang)]) for bid, labels in _MENU_BTN]


def main_menu_full(lang):
    """Rich, flat menu for channels without a button cap (Telegram). Direct
    type shortcuts + every action; the sender lays it out as a grid."""
    lang = _L(lang)
    lookup = {rid: labels for rid, labels in (_MORE + _MENU_BTN)}

    def lbl(rid):
        return lookup.get(rid, {}).get(lang, rid)

    return [
        ("type:video", _TYPES["video"][lang][0]), ("type:image", _TYPES["image"][lang][0]),
        ("type:audio", _TYPES["audio"][lang][0]), ("type:3d", _TYPES["3d"][lang][0]),
        ("nav:edit", lbl("nav:edit")), ("nav:history", lbl("nav:history")),
        ("nav:prompts", lbl("nav:prompts")), ("nav:buy", lbl("nav:buy")),
        ("nav:balance", lbl("nav:balance")), ("act:repeat", lbl("act:repeat")),
        ("nav:lang", lbl("nav:lang")), ("nav:help", lbl("nav:help")),
    ]


def more_menu(lang):
    return [(rid, labels[_L(lang)], "") for rid, labels in _MORE]


def quick_actions(lang):
    return [(aid, labels[_L(lang)]) for aid, labels in _QUICK]


def confirm_buttons(lang):
    lang = _L(lang)
    yes = {"tr": "✅ Üret", "en": "✅ Create", "de": "✅ Erstellen", "ar": "✅ إنشاء", "es": "✅ Crear", "fr": "✅ Créer", "ru": "✅ Создать"}[lang]
    det = {"tr": "⚙️ Detay", "en": "⚙️ Details", "de": "⚙️ Details", "ar": "⚙️ تفاصيل", "es": "⚙️ Detalles", "fr": "⚙️ Détails", "ru": "⚙️ Детали"}[lang]
    no = {"tr": "❌ İptal", "en": "❌ Cancel", "de": "❌ Abbrechen", "ar": "❌ إلغاء", "es": "❌ Cancelar", "fr": "❌ Annuler", "ru": "❌ Отмена"}[lang]
    return [("confirm:yes", yes), ("confirm:detail", det), ("confirm:no", no)]


def gallery_categories(lang):
    lang = _L(lang)
    rows = [(f"hist:{k}", _TYPES[k][lang][0], "") for k in ("video", "image", "audio", "3d")]
    rows.append(("hist:all", S[lang]["all_label"], ""))
    return rows


def account_card(lang, credits, total, processing, used):
    done = max(0, int(total) - int(processing))
    return t(lang, "account").format(credits=credits, total=total, done=done, processing=processing, used=used)


def help_text(lang):
    return _HELP[_L(lang)]


_CMD_ORDER = ["start", "menu", "create", "edit", "prompts", "templates", "buy", "balance", "history", "repeat", "lang", "help"]
_CMD_DESC = {
    "en": {"start": "Start / main menu", "menu": "Main menu", "create": "Create video/image/audio/3D",
           "edit": "Edit a photo", "prompts": "My saved prompts", "templates": "Ready templates",
           "buy": "Buy credits", "balance": "Account & balance", "history": "Gallery / history",
           "repeat": "Repeat last generation", "lang": "Change language", "help": "Help & commands"},
    "tr": {"start": "Başlat / ana menü", "menu": "Ana menü", "create": "Video/görsel/ses/3D üret",
           "edit": "Fotoğraf düzenle", "prompts": "Kayıtlı promptlarım", "templates": "Hazır şablonlar",
           "buy": "Kredi satın al", "balance": "Hesabım & bakiye", "history": "Galerim / geçmiş",
           "repeat": "Son üretimi yinele", "lang": "Dili değiştir", "help": "Yardım & komutlar"},
}
_ABOUT = {
    "tr": "FluxVAI — sohbetten AI ile video, görsel, ses ve 3D üret; fotoğraf düzenle, kredinle yönet.",
    "en": "FluxVAI — create AI video, images, audio & 3D right from chat. Edit photos, manage with credits.",
}


def bot_commands(lang):
    """For Telegram setMyCommands. Commands are ASCII (parser handles the slash form)."""
    d = _CMD_DESC.get(_L(lang), _CMD_DESC["en"])
    return [{"command": c, "description": d.get(c, c)} for c in _CMD_ORDER]


def bot_about(lang):
    return _ABOUT.get(_L(lang), _ABOUT["en"])


# ── command parser (slash commands are universal; words TR/EN) ────────
_COMMANDS = {
    "menu": {"/menu", "menu", "menü", "/start", "start", "başla", "basla", "merhaba", "hi", "hello"},
    "help": {"/help", "/yardim", "/yardım", "yardım", "yardim", "help", "komutlar", "commands"},
    "lang": {"/lang", "/dil", "dil", "language", "lang", "idioma", "sprache", "langue", "язык", "لغة"},
    "cancel": {"/cancel", "/iptal", "iptal", "cancel", "vazgeç", "vazgec", "abbrechen", "annuler", "cancelar", "отмена"},
    "create": {"/create", "/uret", "/üret", "uret", "üret", "create", "olustur", "oluştur", "crear", "créer", "erstellen"},
    "edit": {"/edit", "/duzenle", "/düzenle", "duzenle", "düzenle", "edit", "editar", "modifier", "bearbeiten"},
    "prompts": {"/prompts", "/promptlarim", "/promptlarım", "promptlarım", "promptlarim", "prompts", "promptlar"},
    "templates": {"/templates", "/sablonlar", "/şablonlar", "sablonlar", "şablonlar", "templates", "plantillas", "modèles", "vorlagen"},
    "buy": {"/buy", "/kredi", "kredi", "buy", "satınal", "satinal", "comprar", "acheter", "kaufen"},
    "balance": {"/balance", "/bakiye", "bakiye", "balance", "saldo", "solde", "guthaben", "баланс"},
    "history": {"/history", "/gecmis", "/geçmiş", "geçmiş", "gecmis", "history", "historial", "historique", "verlauf", "история"},
    "repeat": {"/repeat", "/tekrar", "tekrar", "repeat", "yine", "repetir", "répéter", "wiederholen", "повтор"},
}


def parse_command(text: str):
    low = (text or "").strip().lower()
    for cmd, aliases in _COMMANDS.items():
        if low in aliases:
            return cmd
    return None
