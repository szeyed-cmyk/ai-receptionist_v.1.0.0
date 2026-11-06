# CLAUDE.md

Guide for AI coding tools working on this codebase.

## Project

FrontDesk AI — self-hosted AI receptionist. Visitors chat, get answers from a knowledge base, and book 60-minute appointments. Admins manage knowledge, settings, conversations, and appointments.

## Stack

- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy 2.0 + SQLite
- Jinja2 templates
- Starlette SessionMiddleware (signed admin session, role=`admin`)
- OpenAI-compatible AI providers (configured in Admin → Settings)
- bcrypt for password hashes; cryptography (Fernet) for AI key at rest

## Folder map (ZIP root)

```
README.md, HowToSetup.md, CLAUDE.md, CHANGELOG.md, LICENSE-NOTE.md, .env.example
docker-compose.yml
database/schema.sql, database/seed.sql
docs/                  overview, SECURITY.md, screenshots
FrontDesk Project/     <-- all application code lives here
  main.py              ASGI entry: uvicorn main:app
  routes/
    public.py          landing GET /, chat GET /chat, POST /chat
    auth.py            login / setup / opt-in isolated demo / logout
    admin.py           all /admin/* pages; router + mutating Depends(require_admin)
  app/
    security.py        require_admin, CSRF, rate limits, setup token
    auth.py            bcrypt hash/verify (no plaintext fallback)
    config.py          pydantic-settings; refuses placeholder SECRET_KEY
    templating.py      shared Jinja2Templates (absolute path)
    chat_service.py    session-bound chat orchestration
    crypto.py          Fernet encrypt/decrypt for AI API key
    database.py        prod engine + opt-in scoped demo DBs
    demo.py            local fictional fixtures, demo setup credential
    demo_ai.py         no-network guided demo chat
    models.py          Setting, KnowledgeItem, Conversation, Message, Appointment
    ai_service.py      LLM client + book_appointment_tool
    init_db.py         create tables
  .env.example         exact copy of ZIP-root placeholder template; no actual .env
  templates/, static/, tests/, data/, Dockerfile, render.yaml, requirements*.txt
```

## Conventions

- Working directory for install/run/tests is `FrontDesk Project/`.
- Start: `uvicorn main:app --host 0.0.0.0 --port 8000`
- AI Base URL / API Key / Model are stored in the `settings` table via Admin → Settings.
- Do not hardcode API keys or personal contact details.
- Default hours: Mon–Sat 09:00–18:00; closed Sunday; holidays configurable.
- Appointments are 60-minute slots; overlap and duplicate phone numbers are rejected.
- Admin auth is a signed session with `role=admin` — never a plain `admin=true` cookie.
- Public mutating allowlist includes `POST /chat` plus CSRF-guarded login/setup/demo login. Chat is session-bound + rate-limited. Setup needs SETUP_TOKEN. Everything else that mutates data goes through `routes/admin.py`.

## How to run tests

```bash
cd "FrontDesk Project"
python -m venv venv && source venv/bin/activate   # Windows: py -m venv venv
pip install -r requirements-dev.txt
pytest -q
```

## Environment template synchronization

Keep root `.env.example` and `FrontDesk Project/.env.example` byte-for-byte identical (`cmp` from the ZIP root). Root `.env` is for Compose; project `.env` is local/VPS; Render uses Environment settings. `app/config.py` resolves relative `env_file=".env"` against the process working directory. See `HowToSetup.md` for the tree and Linux/PowerShell commands.

## Do not

- Ship `.env` or `*.db` with real keys.
- Include `venv`, `__pycache__`, `.git`, `build`, or `dist` in the release ZIP.
- Put personal contact emails, phones, or developer names in the package.

## Version 1.0.4 additions

- Shared responsive `base.html`/`static/app.css`; Tailwind browser JS is a local MIT distribution in `static/vendor/` (no runtime CDN).
- Public `/` landing; visitor `/chat`; admin management pages use the same shell. Never restore a root alias to chat if you add routes.
- Database registry produces one production engine or scoped demo SQLite files. Demo settings are blanked before engine construction. Keep this ordering.
- `DEMO_MODE` defaults false and must never point to production data. One-click sign-in is CSRF-protected and generates the only existing role, admin, with an isolated synthetic sandbox.
- Demo knowledge/chat mutations are limited to per-signed-session ownership. `block_demo_sensitive_action` always prevents provider, hours, account and setup changes. Never introduce a generic demo admin credential or generic delete shortcut.
- Use only per-worker explicit demo login scope. Do not pass user filename paths or accept role parameters from the request.
- Existing documented images under `docs/screenshots/` are v1.0.3 examples, not new v1.0.4 admin UI screenshots. The current landing admin demo dashboard is `FrontDesk Project/static/admin-demo-dashboard.png`, a supplied browser-QA capture labelled as fictional demonstration data. Add future current screenshots only after visual browser verification of the new screens.
