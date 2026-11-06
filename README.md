# FrontDesk AI

**v1.0.4 · Self-hosted AI receptionist for clinics, salons and service businesses**

A premium public landing page introduces the product. Visitors can ask questions and request 60-minute appointments; your admin workspace brings bookings, conversations, knowledge and settings together.

- **Landing page:** `/` with product hero, labelled product screenshots, features and benefits
- **Visitor chat:** `/chat`
- **Admin login and workspace:** `/admin/login` → `/admin`
- **One-click demo:** available only when `DEMO_MODE=true`, for the sole real role, **admin**.

## What's included

### Public experience

- Responsive landing page with Live Demo and visitor-chat calls to action
- Visitor chat, accessible at `/chat`, with accessible error handling and suggestion chips
- Knowledge-base-grounded AI answers when a seller configures an OpenAI-compatible provider
- 60-minute bookings with business hours, holiday, overlap and duplicate-phone checks

### Business admin

- Actual KPI dashboard: today's schedule, upcoming appointments, total conversations, messages, FAQs, seven-day activity and calculated booking conversion
- Appointment filters/search; explicit confirmed/completed/cancelled status updates
- Conversation inbox with search, timestamps, thread transcript and CSRF-protected deletion
- Knowledge answers: add, edit, activate/deactivate, filter and delete
- Business hours, holiday and provider settings; bcrypt password change; encrypted API-key storage

### Deployment and security

FastAPI + SQLAlchemy + SQLite; Uvicorn; Jinja templates; local CSS/JavaScript assets.
No runtime CDN, no required external font, analytics or tracker.

- Signed Starlette sessions, sole role **admin**, authorization checked at the admin-router level and on every mutation
- CSRF validation, login/chat rate limits, a 2000-character chat cap, session-bound visitor conversations
- `SETUP_TOKEN`-protected initial setup, disabled after bootstrap; `SECRET_KEY` placeholder refused
- bcrypt password hashes (minimum 8-character new passwords); no plaintext fallback
- Fernet encryption of a configured AI key; never echo keys back into HTML
- No personal contact details in source/documentation; no timestamps or author claims baked into the public site

## Safe marketplace demo

`DEMO_MODE` **defaults to false**. Enable it **only** on a dedicated public review deployment, never a deployment containing real customer data or production credentials.

| Environment option | Public review deployment | Production |
|---|---|---|
| `SECRET_KEY` | A fresh, random secret | Your private strong secret |
| `DEMO_MODE` | `true` | `false` or unset |
| `DEMO_SEED` | Optional fixed deployment label such as `review-v1` | Not used |
| `DEMO_MAX_SESSIONS` | Optional capacity guard, default 200 | Not used |
| `HTTPS_ONLY` | `true` | `true` behind TLS |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Leave blank/ignored; demo login does not use them | Use your private account or `SETUP_TOKEN` setup |
| `AI_API_KEY`, `AI_BASE_URL` | Leave blank/ignored; no external AI calls | Configure a provider only if wanted |

Demo design:

1. A dedicated demo engine never opens the configured production `DATABASE_URL`. AI URL/key, admin bootstrap credentials and setup token are discarded from demo configuration.
2. Each demo login creates a separate signed session, independent cookie name/signing salt, and fresh fictional database. Anonymous public visitor chat also gets a sandbox scope.
3. Every reviewer receives seeded fictional appointments, conversations and FAQs; they do not see another reviewer’s additions or chats.
4. Reviewers can change appointment status, add/edit/delete **their own** FAQs, and delete only chats created in their signed admin-demo scope. Seed FAQ records and another reviewer’s records cannot be edited or deleted through the UI or direct requests.
5. **Always blocked in demo mode:** normal password login, setup registration, account/password changes, business schedule changes, AI provider/key writes and network calls to external AI. The demo receptionist uses deterministic local FAQ/booking logic; it is clearly identified as a guided demo.
6. A single worker bounds concurrent demo scopes via `DEMO_MAX_SESSIONS`. Each login without reusing the session creates a new sandbox. For an unbounded public review service, add a scheduled cleanup/reset job and a single Uvicorn worker (SQLite does not provide distributed multi-tenant service management).

**Tradeoff:** each browser session has an isolated disposable sample, not one shared review company. SQLite sandbox files under `data/demo-<seed>/` are not automatically purged (the in-process cap protects memory/excess scope creation, but disk cleanup remains an operations responsibility). Render's free ephemeral filesystem will lose demo data on redeploy/restart; this is expected for a sandbox. Production uses your own `DATABASE_URL` and requires persistent storage.

## Quick start

### Which `.env` belongs where?

Both archive templates contain the **same example placeholders**. Keep them synchronized with one another when changing them. Neither is a secret-bearing file or an automatically loaded root template.

| How you run it | Working directory | Template → private configuration |
|---|---|---|
| Local Python / Linux / Windows / VPS | `FrontDesk Project/` | `FrontDesk Project/.env.example` → `FrontDesk Project/.env` |
| Docker Compose | Unpacked archive **root**, beside `docker-compose.yml` | root `.env.example` → root `.env` |
| Render | `FrontDesk Project/` is the application source | Set variables in Render's **Environment** settings; do not commit/upload `.env` |

Local application settings use `SettingsConfigDict(env_file=".env")` and are read relative to the process **working directory**, so run from `FrontDesk Project/` beside `main.py`. An actual `.env` there contains private configuration and is not included in this ZIP. A copy of the root template at `../.env.example` is equivalent, but the project-folder copy is more convenient.

The root `.env.example` remains part of the archive structure and is the template for Compose. Compose explicitly reads root `./.env`, forwards settings to the container, and resolves `${PORT}` there. Its build context is `./FrontDesk Project`, so it is distinct from a local project-folder `.env`.

Render does not require a committed `.env` (and private `.env` files must never be committed). When deploying the `FrontDesk Project/` contents, the matching `.env.example` is a reference only; define the same variable names through Render.

**When editing an example:** update both copies and compare them before packaging. On Linux/macOS run `cmp .env.example "FrontDesk Project/.env.example"` from the archive root. In PowerShell confirm that `Get-FileHash` for both paths returns the same hash. Keep any real values in separately created `.env` files. `.env` is excluded by `.gitignore` and the project's `.dockerignore`.

### Linux / macOS

Unzip the delivery and run the following from the unpacked **archive root**:

```bash
cd "FrontDesk Project"
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"  # paste output as SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"  # paste output as SETUP_TOKEN
mkdir -p data
python -m app.init_db
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Edit `FrontDesk Project/.env` before initialization to paste the generated `SECRET_KEY` and `SETUP_TOKEN` values, or use private `ADMIN_USERNAME` / `ADMIN_PASSWORD` bootstrap instead of the setup token.

### Windows PowerShell

From the unpacked **archive root**, enter the project, create the required Python 3.12 environment, and activate it:

```powershell
Set-Location ".\FrontDesk Project"
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -c "import sys; assert sys.version_info >= (3, 12)"
python -m pip install --require-hashes -r requirements.lock
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"  # paste as SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"  # paste as SETUP_TOKEN
New-Item -ItemType Directory -Force data | Out-Null
python -m app.init_db
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

`py` creates the Python 3.12 venv. After PowerShell activation, `python` explicitly uses the correct venv, not the system interpreter. Edit the newly created `.env` before initialization to add your generated `SECRET_KEY` and `SETUP_TOKEN`, or private `ADMIN_*`. Open `http://localhost:8000`; setup is `/admin/setup` with the token. Visitor chat is `/chat`, not `/`. In each new PowerShell session, activate the same venv again before the runtime commands.

### Optional local UI review demo

From `FrontDesk Project/`, create a private `.env` from its local template and set `SECRET_KEY` to a fresh development value plus `DEMO_MODE=true`, `DEMO_SEED=local-review`, and `HTTPS_ONLY=false`. Keep `ADMIN_*`, `SETUP_TOKEN`, and `AI_*` blank; use no real customer database. A Linux/macOS environment override also works:

```bash
DEMO_MODE=true DEMO_SEED=local-review HTTPS_ONLY=false \
SECRET_KEY=local-development-only-change-in-production \
uvicorn main:app --host 0.0.0.0 --port 8000
```

See the isolated-review limits above. Public review demo and production must be separate deployments; leave `DEMO_MODE=false` for production.

## Render review deployment

Upload/copy the contents of **`FrontDesk Project/`**, not the documentation root, into the Render service source (Render `rootDir: .`; Build `pip install --require-hashes -r requirements.lock`; Start `uvicorn main:app --host 0.0.0.0 --port $PORT`). Configure these values in **Render → Environment** (or its supported environment-group workflow). Do **not** commit a filled `.env`; the application-folder `.env.example` is only a synchronized reference:

```
SECRET_KEY=<a-new-random-value>
DEMO_MODE=true
DEMO_SEED=review-v1
HTTPS_ONLY=true
# no AI key needed or used
```

The marketplace **Live Demo URL is the site root**, e.g. `https://<your-service>.onrender.com/`. The "Live demo" button opens `/admin/login`, where the only actual role, **Admin**, has a one-click button. `/chat` is the visitor interface. After review/deploy, check `/health`, landing, admin login/button, dashboard, appointments, conversations, knowledge, settings, and chat. No deployment is included in this ZIP and no live environment is modified by installing it.

Use `DEMO_MODE=false` and a persistent database when deploying with real customer data. Do not expose one-click login on production. See `HowToSetup.md` for detailed Windows, VPS, Docker and upgrade instructions.

## Source layout

```
README.md, HowToSetup.md, CLAUDE.md, CHANGELOG.md, LICENSE-NOTE.md
.env.example              # archive/Compose template; keep synchronized
docker-compose.yml        # run at archive root; explicit env_file: ./.env
/database/schema.sql and seed.sql
/docs/overview.md, SECURITY.md, DEMONSTRATION.md, screenshots/
FrontDesk Project/
  main.py, routes/{public,auth,admin}.py
  .env.example            # matching local-app template, same root content
  data/                   # create/use locally, no generated DB shipped
  app/{config,database,models,security,auth,demo,demo_ai,...}.py
  templates/       shared admin shell + all visitor/admin pages
  static/          local assets and labelled product screenshots
  tests/           original security/booking + landing/isolation/workflow tests
  requirements.txt, requirements.lock, Dockerfile, render.yaml
```

`docs/screenshots/` are earlier **v1.0.3 product examples**, not claimed captures of the new v1.0.4 admin skin. Landing assets include a previous visitor-workflow example and the actual v1.0.4 admin demo dashboard, both labelled as fictional data.

## Tests / dependency audit

```bash
cd "FrontDesk Project"
pip install -r requirements-dev.txt
pytest -q
pip-audit -r requirements.lock
```

All prior 22 tests are retained; 16 new tests cover landing/local assets, real metrics, management/search/validation, demo auth, isolation, ownership, setup protected writes, booking/no-network behavior and cross-mode cookies. Final results are recorded in `CHANGELOG.md`.

## Licence

Single-site licence. See [LICENSE-NOTE.md](LICENSE-NOTE.md). No real personal contacts or API keys are embedded in this package.
