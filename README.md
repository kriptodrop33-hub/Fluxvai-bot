# FluxVAI WhatsApp Botu

Kullanıcıların **WhatsApp üzerinden** FluxVAI hesaplarıyla içerik (video / görsel / ses / 3D) üretmesini, kredilerini görmesini ve **Stripe** ile kredi satın almasını sağlayan resmi **Meta WhatsApp Cloud API** botu. Python / FastAPI ile yazılmış **ayrı bir mikroservis**tir; kullanıcı ve kredi verisinin tek doğruluk kaynağı FluxVAI backend'idir (`PROJE 1/fluxvai-emergent/backend/mock_server.py`).

```
WhatsApp ⇄ Meta Cloud API ⇄ [Bot :8090] ⇄ HTTP ⇄ [FluxVAI backend :8001]
                                  │                         │
                            sqlite (oturum)            db.json (kullanıcı+kredi)
Web ⇄ [React :3000] ── /api/whatsapp/link-code ───────────┘
Stripe ⇄ /webhook/stripe (backend) ── kredile + ── /internal/notify ─→ Bot ─→ "kredin yüklendi"
```

## Üyelik & kredi modeli

- **Bağımsız bot hesabı yoktur.** Kullanıcı önce **fluxvai.app**'te üye olur, sitede **Ayarlar → WhatsApp Botu → Kod oluştur** ile 6 haneli bir kod üretir, botla sohbete o kodu gönderir. Bot, telefon numarasını o hesaba bağlar (`/internal/wa/link`). Tek hesap, tek kredi havuzu.
- Üretim mevcut `POST /api/generate` ile yapılır → krediler backend'de atomik düşer. Kredi maliyetleri: `video 15`, `image 4`, `audio 5`, `3d 25`.
- Kredi satın alma: bot bir **Stripe Checkout linki** gönderir; ödeme tamamlanınca `POST /webhook/stripe` hesabı kredi­ler ve botu tetikleyerek kullanıcıya “yüklendi” mesajı attırır.

## Özellikler

Bot, FluxVAI sitesinin özelliklerini WhatsApp'a taşır:

- **`/start` + menü** — `/start`, `başla`, `merhaba` veya `menü` ile ana menü (🎬 Üret / 💳 Kredi Al / 💰 Bakiye).
- **Onboarding** — ilk bağlanmada "ağırlıklı ne üreteceksin?" (İçerik Üreticisi / E-ticaret / Influencer / Kurumsal). Seçim backend'e kaydedilir (`POST /api/users/me/onboarding`) → web ile senkron, kalıcı; menü/tür sıralaması buna göre kişiselleşir.
- **Üretim sihirbazı** — tip (video/görsel/ses/3D) → platform → **hazır şablon** (veya sıfırdan) → açıklama → stil → süre → onay → üret → teslim. Şablon seçilince prompt/stil/süre prefill edilir, stil/süre adımı atlanır.
- **Görsel düzenleme** — 🎬 Üret → ✏️ Görsel Düzenle → kullanıcı fotoğraf gönderir → bot Meta Graph'tan indirir, FluxVAI'ye yükler (S3) → "nasıl değiştireyim?" → üretir → sonucu **doğrudan görsel olarak** geri gönderir (`send_image`).
- **Kredi & satın alma** — bakiye, Stripe ile kredi yükleme, ödeme sonrası otomatik bildirim.
- Global komutlar: `menü`, `iptal`, `yardım`.

## Konuşma akışı (FSM)

```
UNLINKED → AWAITING_CODE → ONBOARDING → IDLE
  IDLE ─ Üret ─→ GEN_TYPE → GEN_PLATFORM → GEN_TEMPLATE → GEN_PROMPT → GEN_STYLE → GEN_DURATION → GEN_CONFIRM → GEN_PROCESSING → teslim
                 └ Görsel Düzenle → GEN_IMG_AWAIT_PHOTO → (indir+yükle) → GEN_IMG_PROMPT → GEN_CONFIRM → … → send_image
  IDLE ─ Kredi Al ─→ BUY_PACKAGE → Stripe link → BUY_AWAIT_PAYMENT → (webhook → notify) → IDLE
```

wa.me derin bağlantısı kodu otomatik gönderdiğinden, kullanıcının **ilk mesajı** kod olsa bile bağlama çalışır.

### Medya depolama (görsel yükleme)
Kullanıcının gönderdiği fotoğraf backend'de saklanır: birincil yol **S3 / S3-uyumlu** (R2, MinIO) → presigned/public URL; `S3_BUCKET` boşsa **yerel `./data/uploads` + StaticFiles** fallback (dev). Env: `backend/.env.example` içindeki S3 bloğu. Çıktıyı WhatsApp'a `send_image` ile geri göndermek **herkese açık HTTPS URL** ister — S3/CDN bunu sağlar; yerel fallback için `UPLOADS_PUBLIC_BASE`'i public bir tünel (ngrok/Cloudflare) URL'ine ayarla.

> Not: AI henüz bağlı değil — üretim mock. "Görsel düzenleme" çıktısı şu an yüklenen görseli yansıtır (akış uçtan uca çalışsın diye). Gerçek image-to-image, generate motoruna `source_media_url` girdi olarak bağlanınca gelir; **bot tarafında değişiklik gerekmez**.

## Kurulum

```bash
cd fluxvai-wa-bot
python -m venv .venv && . .venv/Scripts/activate   # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # değerleri doldur
```

`.env` (botin tamamı için bkz `.env.example`):

| Değişken | Açıklama |
|---|---|
| `WA_VERIFY_TOKEN` | Meta webhook doğrulamasında gireceğin rastgele dize |
| `WA_APP_SECRET` | Meta App → Settings → Basic → App Secret (imza doğrulaması) |
| `WA_ACCESS_TOKEN` | **Kalıcı System User token** (24sn'lik geçici token değil!) |
| `WA_PHONE_NUMBER_ID` | WhatsApp → API Setup → Phone number ID |
| `FLUXVAI_BASE_URL` | Backend adresi (varsayılan `http://localhost:8001`) |
| `BOT_SERVICE_SECRET` | Backend'deki `BOT_SERVICE_SECRET` ile **aynı** olmalı |

### Backend tarafı (PROJE 1)

`backend/.env` içine (bkz `backend/.env.example`): `BOT_SERVICE_SECRET` (aynı), `WA_BOT_NUMBER`, `PUBLIC_BASE_URL`, `BOT_NOTIFY_URL=http://localhost:8090/internal/notify`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`. Ayrıca:

```bash
cd ../PROJE\ 1/fluxvai-emergent/backend
pip install stripe
```

## Çalıştırma (yerel)

```bash
# 1) FluxVAI backend
cd PROJE\ 1/fluxvai-emergent/backend
python -m uvicorn mock_server:app --port 8001

# 2) Bot
cd PROJE\ 3/fluxvai-wa-bot
python -m app.main          # veya: uvicorn app.main:app --port 8090

# 3) Webhook'ları dışarı aç (Meta + Stripe HTTPS ister)
ngrok http 8090             # → Meta webhook callback: https://<bot>.ngrok-free.app/webhook
stripe login
stripe listen --forward-to localhost:8001/webhook/stripe   # whsec_... → STRIPE_WEBHOOK_SECRET
```

**Meta App Dashboard → WhatsApp → Configuration → Webhook:** Callback URL = `https://<bot>.ngrok…/webhook`, Verify token = `WA_VERIFY_TOKEN`, ve **messages** alanına abone ol.

## Test

```bash
# Hızlı (backend :8001 ayakta olmalı):
python -m pytest -m "not slow" -q
# Tümü (gerçek üretim tamamlanmasını ~30sn bekler):
python -m pytest -q
```

`tests/` kapsamı: imza doğrulama, gelen mesaj ayrıştırma, sqlite dedupe/oturum, bağlama akışı, üretim sihirbazı + gerçek tamamlanma, satın alma listesi + zarif hata, `/internal/notify`, webhook GET doğrulama.

## Üretime alırken dikkat

- **Kalıcı token kullan** (`WA_ACCESS_TOKEN`); geçici tokenlar 24sn'de ölür.
- **24 saat penceresi:** Kullanıcının son mesajından 24sn sonra serbest metin gönderilemez; **onaylı template** gerekir. Geç gelen Stripe onayı için Meta'da `payment_confirmation` template'ini önceden onaylat ve `app/notify.py` içinde `send_template`'e geç.
- **Medya teslimi:** Mock backend `output_url` olarak gerçek olmayan bir CDN döner; şimdilik **link** olarak gönderiliyor. Gerçek `video`/`image` mesajı için herkese açık gerçek medya URL'si gerekir.
- **server.py (Mongo) geçişi:** Köprü endpoint'leri (`/api/whatsapp/*`, `/internal/wa/*`, `/webhook/stripe`) şu an `mock_server.py`'da. Mongo backend'i canlıya alınca aynı bloğu oraya taşı.
- `WA_APP_SECRET` boşsa webhook imza kontrolü atlanır (yalnızca yerel geliştirme).
