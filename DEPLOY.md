# Deploy → GitHub + Railway

The bot is a single repo that runs **two services** off one codebase, selected by `BOT_MODE`:
`telegram` (long-polling, no public URL) and `whatsapp` (Cloud API webhook, uses Railway's domain).
Both bind to Railway's `$PORT` automatically (via `run.py`).

> ⚠️ The bot needs a reachable **FluxVAI backend** (`FLUXVAI_BASE_URL`). Until `fluxvai.app` is
> live, set it to wherever `mock_server.py` is hosted. With no backend, the bot answers `/start`
> and the language picker, then shows "service starting" — linking/generation need the backend.

## 1) Push to GitHub
```bash
cd "PROJE 3/fluxvai-wa-bot"
git init && git add . && git commit -m "FluxVAI bot"
gh repo create fluxvai-bot --private --source=. --push   # or create a repo on github.com and:
# git remote add origin https://github.com/<user>/fluxvai-bot.git && git branch -M main && git push -u origin main
```
`.env`, `data/`, `__pycache__` are git-ignored — no secrets are pushed.

## 2) Railway — Telegram service
1. railway.app → **New Project → Deploy from GitHub repo** → pick the repo.
2. It auto-builds (Nixpacks, Python 3.12, `run.py`). Healthcheck: `/health`.
3. **Variables** (Service → Variables):

| Variable | Value |
|---|---|
| `BOT_MODE` | `telegram` |
| `TELEGRAM_BOT_TOKEN` | from @BotFather |
| `FLUXVAI_BASE_URL` | your backend URL (https) |
| `BOT_SERVICE_SECRET` | same long random string as the backend |

→ Deploy. Logs should show `Telegram bot: @yourbot` + `long-polling started`.
**Only one process may poll Telegram** — make sure no local bot is running, or you'll get HTTP 409.

## 3) Railway — WhatsApp service (optional, second service)
1. In the same project: **New → GitHub Repo** → same repo (a second service).
2. **Variables**:

| Variable | Value |
|---|---|
| `BOT_MODE` | `whatsapp` |
| `WA_VERIFY_TOKEN` | any string (also entered in Meta) |
| `WA_APP_SECRET` | Meta App → Settings → Basic |
| `WA_ACCESS_TOKEN` | **permanent** System User token |
| `WA_PHONE_NUMBER_ID` | WhatsApp → API Setup |
| `FLUXVAI_BASE_URL` / `BOT_SERVICE_SECRET` | same as Telegram |

3. Railway gives a public domain (`https://<svc>.up.railway.app`). In **Meta → WhatsApp →
   Configuration → Webhook**: Callback `https://<svc>.up.railway.app/webhook`, Verify token =
   `WA_VERIFY_TOKEN`, then subscribe to **messages**. (No tunnel needed — Railway is the URL.)

## 4) Backend → bot link
When `fluxvai.app` (or your backend host) is live, set `FLUXVAI_BASE_URL` on both services to it
and ensure the backend's `BOT_SERVICE_SECRET` matches. Redeploy. Done.

## Notes
- **Sessions** live in sqlite under `./data` (ephemeral on Railway). To survive redeploys, add a
  Railway **Volume** mounted at `/data` and set `BOT_DB_PATH=/data/bot.sqlite3`,
  `TELEGRAM_DB_PATH=/data/telegram.sqlite3`. Optional — sessions are transient.
- **Local dev** still works: `pip install -r requirements.txt`, set `.env`, `python run.py`.
- Tests: `python -m pytest -q` (needs a backend on `:8001`).
