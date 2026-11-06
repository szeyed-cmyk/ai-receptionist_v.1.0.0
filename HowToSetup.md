# HowToSetup.md

Step-by-step install for a clean machine. Application code lives in `FrontDesk Project/`. Documentation, SQL, and `docker-compose.yml` live at the ZIP root.

## Archive layout and environment files

Paths below are relative to the directory you extract the archive into (called the **archive root**):

```text
.
├── .env.example                       # retained root/Compose example
├── docker-compose.yml                 # run from archive root
├── README.md
├── HowToSetup.md
├── database/
│   ├── schema.sql
│   └── seed.sql
├── docs/
└── FrontDesk Project/                 # application and local working directory
    ├── .env.example                   # exact copy of root example
    ├── .env                           # create privately; NOT in the archive
    ├── main.py
    ├── requirements.lock
    ├── Dockerfile
    ├── render.yaml
    ├── app/
    ├── routes/
    ├── templates/
    ├── static/
    └── data/                          # local SQLite bind-mount target
```

Both `.env.example` files are identical placeholder-only templates. The root copy is retained for the expected archive structure and Docker Compose; the application-folder copy makes local setup self-contained. **Both must stay synchronized and no actual `.env` secrets belong in the ZIP.**

```text
Run method                       Working directory / source       Private configuration
Local Python (Linux / Windows)   FrontDesk Project/                FrontDesk Project/.env
VPS + systemd                    /opt/frontdesk/FrontDesk Project  .env in that directory
Docker Compose                   archive root                      archive-root .env
Render                           FrontDesk Project/ source          Render Environment settings
```

`FrontDesk Project/app/config.py` sets `env_file=".env"`; Python dotenv resolves that relative path against the application's **working directory** (not against the archive root or module location). The commands below therefore enter `FrontDesk Project` before creating/loading `.env` and running `python -m app.init_db` or `uvicorn main:app`. A copy of `../.env.example` is equivalent, but `FrontDesk Project/.env.example` is already adjacent to the app.

Compose is different: run `docker compose` at the archive root. Its `env_file: .env` resolves at `docker-compose.yml`; it also substitutes variables such as `${SECRET_KEY}` and `${PORT}` from root `.env`. The image build context is `./FrontDesk Project`, with `/app/data` bind-mounted to `./FrontDesk Project/data`, but that does **not** mean copying local `.env` into the project folder for Compose. Only the root `.env` is needed for the supplied Compose file; do not copy it between the two paths.

For Render, commit the application directory's code to its service root (or set service root directory to `FrontDesk Project`), then define variables via the Render dashboard or environment groups. Root folder and working-directory selection do not make either example into a committed secret. Never commit a filled `.env`; unused `.env.example` is documentation only. The application `.dockerignore` excludes build-context `.env` files, but Compose must still be given root `.env` as documented.

**After template changes, synchronize both copies:**

```bash
# Bash, from archive root
cp .env.example "FrontDesk Project/.env.example"
cmp .env.example "FrontDesk Project/.env.example"
```

```powershell
# PowerShell, from archive root
Copy-Item .env.example ".\FrontDesk Project\.env.example"
(Get-FileHash .env.example).Hash -eq (Get-FileHash ".\FrontDesk Project\.env.example").Hash   # True
```


## Requirements

- **Python 3.12+** (required)
- pip
- Optional: Docker + Docker Compose, nginx, systemd (VPS)
- Optional: `sqlite3` CLI if you want to load `database/seed.sql` by hand

---

## A. Local install (Linux / macOS) — ordered steps

1. Unzip the archive and enter the project folder:

```bash
cd "FrontDesk Project"
```

2. Create a virtual environment:

```bash
python3.12 -m venv venv
source venv/bin/activate
```

3. Check that `requirements.lock` exists in this directory, then install its pinned dependencies:

```bash
python -m pip install --require-hashes -r requirements.lock
# python comes from the activated venv. Use pip only if you prefer:
# pip install --require-hashes -r requirements.lock
```

If a locked package is unavailable on your platform, troubleshoot the interpreter/platform first rather than silently skipping hash verification. Do not replace pinned security-sensitive versions without testing.

4. Create the private local environment file from the adjacent application template while your working directory is `FrontDesk Project`:

```bash
cp .env.example .env
```

This creates `FrontDesk Project/.env`; the ZIP must contain only `.env.example`, not a filled `.env`. `cp ../.env.example .env` is also correct because both copies are identical. `../.env.example` is **not** loaded automatically by a local app run here.

5. Edit `.env` and set required secrets:

```bash
# Generate SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Generate SETUP_TOKEN:
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

Put both values into `.env`. Optionally set `ADMIN_USERNAME` / `ADMIN_PASSWORD` to skip the setup form (when set, `/admin/setup` is disabled). Set `HTTPS_ONLY=true` behind HTTPS.

6. Create the data directory and initialize the database:

```bash
mkdir -p data
python -m app.init_db
```

Optional demo data (fictional clinic):

```bash
sqlite3 data/ai_receptionist.db < ../database/schema.sql
sqlite3 data/ai_receptionist.db < ../database/seed.sql
```

(The app also creates tables automatically on first start.)

7. Start the server from this `FrontDesk Project` directory:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
# alternatively: python main.py (uses PORT if supplied)
```

Leave the activated venv and working directory unchanged; do not `cd` to the ZIP root before starting locally.

Behind a reverse proxy, add trusted forwarded headers:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips='127.0.0.1'
```

8. Open http://localhost:8000

---

## B. Windows PowerShell local install (`py`)

Run **PowerShell**, not Command Prompt. These commands require Python launcher (`py`) 3.12+ and use a project-local venv named `venv`.

1. From the unpacked **archive root**, enter the application folder:

```powershell
py -0p
Set-Location ".\FrontDesk Project"
```

`py -0p` lists installed Python versions/paths. Ensure one is 3.12+ as required. Confirm `Test-Path .env.example`, `Test-Path requirements.lock`, and `Test-Path main.py` each return `$true`; this prevents creating `.env` in the wrong directory.

2. Create and activate the virtual environment:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
```

Do not use `source` or Command Prompt's `activate.bat` in PowerShell. `py` creates the requested Python 3.12 venv; after activation, `python` explicitly selects that venv for installation and runtime, so dependencies do not land in the system interpreter. In each new PowerShell session, activate the same `venv` again before running the app.

3. Install dependencies, create `.env`, and generate placeholders for your private values:

```powershell
python -m pip install --require-hashes -r requirements.lock
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"  # paste as SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"  # paste as SETUP_TOKEN
```

This is `FrontDesk Project\.env`, not `..\.env` (the latter is for Compose only). The neighboring `.env.example` was already copied from the ZIP root template and must have the same content. `Copy-Item ..\.env.example .env` is equivalent. After copying, edit `.env` in your preferred editor—for example, `notepad .env`—and paste the generated values. Leave `ADMIN_*` blank to use browser setup, or use explicit private admin bootstrap instead. Set `HTTPS_ONLY=true` only behind HTTPS.

4. Initialize and run using the activated venv:

```powershell
python -c "import sys; assert sys.version_info >= (3, 12)"
New-Item -ItemType Directory -Force data | Out-Null
python -m app.init_db
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The `data` folder is created only on your machine; no DB is packaged. Open `http://localhost:8000`; the visitor chat is `/chat` and admin login is `/admin/login`.

Optional PowerShell **local** review settings use separate demo-only data. Keep real admin/AI/bootstrap credentials blank and review `../docs/DEMONSTRATION.md` first:

```powershell
# Optional: from FrontDesk Project for a dedicated local review only.
$env:DEMO_MODE = "true"
$env:DEMO_SEED = "local-review"
$env:HTTPS_ONLY = "false"
# Set a fresh development SECRET_KEY, e.g. a generated value:
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

These values apply to this PowerShell session only, not to a committed `.env`. Real admin/setup/AI credentials and a real database are not used. Clear the overrides (`Remove-Item Env:DEMO_MODE` and likewise for `DEMO_SEED`, `HTTPS_ONLY`, `SECRET_KEY`) before switching back to ordinary local configuration in that session. Never expose `DEMO_MODE=true` on production data.

## C. First admin login / demo account

### Option 1 — browser setup (requires SETUP_TOKEN)

1. Visit http://localhost:8000/admin/setup
2. Enter username, password (min 8 characters; avoid weak passwords), and the `SETUP_TOKEN` from `.env`.
3. You are redirected to the dashboard.

### Option 2 — environment bootstrap

Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `FrontDesk Project/.env` before starting a local/VPS installation, or in archive-root `.env` for supplied Compose. `/admin/setup` is disabled. Log in at `/admin/login`; the password is hashed into the database on first successful login.

### Dedicated public review demo (Vibe96 / Render)

The app contains exactly one role: **admin**. v1.0.4 can issue that role only in the isolated, explicitly enabled sandbox. Do not create public-facing credentials on a production instance.

For a **separate demo-only Render service** (recommended), deploy the contents of `FrontDesk Project/` and set the following names in **Render → Environment**, not in a committed or uploaded `.env`:

```
SECRET_KEY=<generate-a-fresh-random-value>
DEMO_MODE=true
DEMO_SEED=review-v1
HTTPS_ONLY=true
```

Leave `ADMIN_*`, `SETUP_TOKEN` and `AI_*` unset for that public demo. Production DSN/AI provider/admin credentials are not used; no AI provider or setup token is required for viewing the sandbox. Use the landing-page root (`https://<service>.onrender.com/`) as the live-demo URL. The Live Demo button opens `/admin/login`, which includes **Enter Admin demo**. Each signed review session starts with independent fictional data and may explore status and own-FAQ/chat changes. The server forbids production login and sensitive settings, keys, setup or account changes in this deployment. `/chat` is the visitor experience.

If you edit an existing Render service already holding customer data or a real AI key, **do not turn on demo mode there**. Deploy a fresh demo service without those secrets instead. For production leave `DEMO_MODE=false`, retain private `ADMIN_USERNAME`/`ADMIN_PASSWORD` or `SETUP_TOKEN`, and mount persistent storage for the chosen SQLite `DATABASE_URL`. Do not copy demo DB files over production.

Demo note: SQLite per-session sandboxes are intentionally disposable. They are not automatically deleted; the worker knows up to `DEMO_MAX_SESSIONS` (default 200) scopes. Single-worker deployment is mandatory for the per-worker cap; extra external disk cleanup is required for a long-running service. Render free's ephemeral filesystem may reset at restart/redeploy. Read `docs/DEMONSTRATION.md` for isolation, capacity and workflow tradeoffs.

### Private password-protected deployment (not the public one-click demo)

1. Deploy with `SECRET_KEY`, `SETUP_TOKEN` (or `ADMIN_USERNAME`/`ADMIN_PASSWORD`), and `HTTPS_ONLY=true`.
2. Optional private `ADMIN_*` bootstrap (avoid reusing real credentials):

```
ADMIN_USERNAME=demo
ADMIN_PASSWORD=<choose-a-strong-demo-password>
```

3. With `DEMO_MODE=false`, confirm `/admin/login` accepts those credentials and the dashboard loads.
4. If you choose that separate private deployment path, provide your newly chosen private review credentials only through the appropriate marketplace review-credentials field. This does not replace or weaken the recommended isolated one-click demo; never reuse personal or production credentials.
5. In **Settings**, add your own AI Base URL / API Key / Model, business name, hours.
6. Add FAQs under **Knowledge**.

Change the password later under **Admin → Settings → Change Admin Password**.

---

## D. Docker Compose (from ZIP root)

```bash
cp .env.example .env
# set SECRET_KEY and SETUP_TOKEN (and optional ADMIN_*) in .env
docker compose up --build
```

- Compose reads `.env` at the ZIP root (`env_file: .env`) and forwards `AI_*`, `PORT`, `SETUP_TOKEN`, etc.
- Demo flags are forwarded by Compose. Demo and production must be separate deployments; never both use production data.
- Business defaults come from `app/config.py`. Compose checks the required `${SECRET_KEY}` and supplies other development/empty defaults as shown in `docker-compose.yml`. Example files are not automatically loaded by the container.
- App: http://localhost:8000
- Database file: `FrontDesk Project/data/ai_receptionist.db` (bind-mounted)
- Image build context: `./FrontDesk Project`
- Image installs from `requirements.lock` with `--require-hashes`
- The app creates tables on startup (`Base.metadata.create_all` in `app/__init__.py`)
- Start command inside the image: `uvicorn main:app --host 0.0.0.0 --port 8000`

---

## E. Ubuntu VPS (venv + systemd + nginx)

Assumes Ubuntu 22.04+, a non-root user with sudo, and a domain pointed at the server.

### 1. System packages

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip nginx sqlite3
```

### 2. App files

```bash
sudo mkdir -p /opt/frontdesk
sudo chown "$USER":"$USER" /opt/frontdesk
# copy the unzipped archive into /opt/frontdesk so that
# /opt/frontdesk/FrontDesk Project/ and /opt/frontdesk/database/ exist
cd "/opt/frontdesk/FrontDesk Project"
python3.12 -m venv venv
source venv/bin/activate
pip install --require-hashes -r requirements.lock
cp .env.example .env
# equivalent: cp ../.env.example .env
# edit .env: SECRET_KEY, SETUP_TOKEN, HTTPS_ONLY=true, optional ADMIN_*
mkdir -p data
python -m app.init_db
```

### 3. systemd unit

Create `/etc/systemd/system/frontdesk.service`:

```ini
[Unit]
Description=FrontDesk AI
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/frontdesk/FrontDesk Project
EnvironmentFile=/opt/frontdesk/FrontDesk Project/.env
ExecStart=/opt/frontdesk/FrontDesk Project/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo chown -R www-data:www-data /opt/frontdesk
sudo systemctl daemon-reload
sudo systemctl enable --now frontdesk
```

### 4. nginx reverse proxy

Create `/etc/nginx/sites-available/frontdesk`:

```nginx
server {
    listen 80;
    server_name your.domain.example;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/frontdesk /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# then obtain TLS (example): sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx
```

Set `HTTPS_ONLY=true` in `.env` after TLS is active, then `sudo systemctl restart frontdesk`.

---

## F. Render (demo hosting)

1. Push a repo whose contents are the `FrontDesk Project/` folder (so `main.py` is at the repo root), **or** set Render Root Directory to `FrontDesk Project`.
2. Build: `pip install -r requirements.txt` (or lockfile with hashes if supported).
3. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`
4. Set variable names through Render's **Environment** settings, not a committed `.env`. Production uses `SECRET_KEY`, `SETUP_TOKEN` (or `ADMIN_USERNAME` + `ADMIN_PASSWORD`), `HTTPS_ONLY`, optional `DATABASE_URL`, `AI_*` and `BUSINESS_NAME`. A dedicated public demo uses the isolated-demo block in section C (`DEMO_MODE=true`, fresh `SECRET_KEY`, blank admin/setup/AI credentials). Do not upload `.env` to this service.
5. Deploy and check `/health`, landing, login, dashboard and chat. For a normal private deployment, use admin setup/bootstrap and optionally add your provider in Settings. For isolated demo, use the one-click **Admin demo** and do not add production keys/accounts; protected settings writes are intentionally blocked.

A sample `render.yaml` is inside `FrontDesk Project/`. It defines build/start paths and variable names (`sync: false` values must still be supplied privately). Its `DEMO_MODE` default is false for production; the dedicated public-demo opt-in remains manual. Keep both `.env.example` files byte-for-byte synchronized if changing their documented variables.

---

## G. Branding changes

| What | Where |
|------|--------|
| Business name | Admin → Settings, or `BUSINESS_NAME` in `.env` |
| Avatar image | Replace `FrontDesk Project/static/avatar.jpg` |
| Chat / admin colors and layout | Edit Jinja templates under `FrontDesk Project/templates/` (Tailwind utility classes) |
| Page title | `templates/chat.html`, `templates/admin.html`, etc. |
| Default hours / holidays | Admin → Settings (`opening_hour`, `closing_hour`, `closed_days`, `holiday_dates`) |
| FAQs the AI uses | Admin → Knowledge |

---

## H. Booking rules (buyers)

- Hours and closed weekdays are configurable (defaults: Mon–Sat 09:00–18:00, closed Sunday).
- Holiday dates (`YYYY-MM-DD` list) are rejected by the booking tool.
- Overlapping 60-minute slots are rejected.
- Duplicate phone: one confirmed appointment per phone number.

## J. Example AI providers

| Provider | AI Base URL | Example Model |
|----------|-----------------------------|-------------------------|
| Groq | https://api.groq.com/openai/v1 | `openai/gpt-oss-20b` |
| OpenAI | https://api.openai.com/v1 | `gpt-4o-mini` |
| OpenRouter | https://openrouter.ai/api/v1 | `google/gemini-flash-1.5` |
| Together AI | https://api.together.xyz/v1 | Various open models |
| Local (Ollama) | http://localhost:11434/v1 | `llama3.2` |

## K. Production notes

- Generate and set `SECRET_KEY` before going live. The app **refuses to start** with the placeholder.
- Set `SETUP_TOKEN` (or use `ADMIN_PASSWORD` bootstrap) before exposing the site.
- Use a reverse proxy and HTTPS; set `HTTPS_ONLY=true`.
- Do not commit or share your real `.env`, API keys, or `*.db` files.
- Admin auth uses a signed session cookie (`frontdesk_session`) with `role=admin`. A plain `admin=true` cookie is rejected.
- AI API keys are encrypted at rest (Fernet derived from `SECRET_KEY`).
- See [docs/SECURITY.md](docs/SECURITY.md) for the full route/guard table.


## L. Upgrade v1.0.3 → v1.0.4 (existing live service)

1. Back up the existing app directory and production SQLite `*.db` before replacing any file. Test the backup restore procedure first.
2. Confirm root links have changed: `/` is now the landing page; the familiar public chat moved to `/chat`. Update any embedded visitor-chat links accordingly.
3. Copy **application files** from the v1.0.4 `FrontDesk Project/` (templates, static, app, routes, main and requirements) into your new review/staging instance; do not overwrite your database with a ZIP data file.
4. Update dependencies from `requirements.lock` and run **all tests** on a staging copy before replacing production files.
5. Production: set `DEMO_MODE=false`, preserve `DATABASE_URL`, keep `SECRET_KEY` stable or old sessions will invalidate, and use HTTPS plus a trusted reverse-proxy allowlist.
6. Public review use: start a separate clean Render service with `DEMO_MODE=true`, no real credentials, and fresh secret. For long-running public demos, assign one worker and arrange storage cleanup.
7. Test normal admin authentication, every management form, live-chat/booking, and new mobile layout with browser tests on staging before switching a production URL. No deployment migrations beyond existing tables are required for the UI; demo scope DBs are automatically created separately.

## M. Render troubleshooting

- **Root is chat or 404:** redeploy the v1.0.4 `FrontDesk Project` content and verify `routes/public.py` contains both landing `/` and chat `/chat`. Clear any platform cache only through standard deployment mechanisms.
- **No one-click demo button:** explicitly set `DEMO_MODE=true` on the *dedicated clean review* service and restart. This behaviour is intentionally absent in production.
- **Login redirects to setup:** production DB has no admin hash. Configure `SETUP_TOKEN` or use private `ADMIN_*`; this does not apply to demo mode.
- **App seeded but another reviewer's chat is missing:** intended isolation. Each signed review session has an independent fictional store.
- **AI replies are deterministic:** intended in demo mode to avoid costs and secret exposure. Production uses your own provider settings with the API key encrypted at rest.
- **Client IP rate limits:** `request.client.host` is used. On Render, run `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'` only where Render terminates all inbound traffic. For nginx, restrict to the proxy address rather than using '*'.
- **Free filesystem disappears:** demo data is disposable. Use persistent storage for production; do not rely on Render free SQLite persistence.
- **Both examples drifted:** copy either `.env.example` over the other and run the comparison commands in the initial layout section. Never merge a filled `.env` into an example.
- **Local `.env` is not found / placeholder SECRET_KEY is rejected:** run `pwd` / `Get-Location` first. From `FrontDesk Project`, confirm `Test-Path main.py`, `Test-Path .env`, then restart. The dotenv path is resolved against the invocation working directory, not the ZIP-root Compose `.env`. Activating venv does not itself change directory.
- **Render needs secrets:** fill Render Environment settings rather than committing/uploading `.env`. The dedicated demo discards configured production DSN/admin/bootstrap/AI values before engine creation but still requires a fresh secret and clean isolated deployment.
- **Archive contains old screenshots:** `docs/screenshots/` are intentionally marked as v1.0.3 product examples for documentation. The landing page uses the actual new admin demo-dashboard screenshot plus a retained visitor-workflow example. The outdated pricing/duration showcase has been removed.
