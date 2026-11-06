# CHANGELOG.md

## 1.0.4

### Vibe96 marketplace UI/resubmission work

- New `/` product landing page: responsive hero, Live Demo button to `/admin/login`, visitor-chat CTA, real supplied product screenshots, benefits, features and self-hosted positioning. No invented testimonials, figures or contacts. Public chat moved to `/chat`.
- Rebuilt admin UI into one cohesive responsive system with accessible navigation, business header, safe mobile sidebar, local Tailwind build and custom CSS, common tables/forms/statuses. No runtime external CDN/tracking/font dependency.
- Dashboard backed by actual SQL metrics: today/upcoming/total bookings, conversations, messages, FAQ total, seven-day conversation activity, calculated conversation-to-booking conversion, current bookings/inbox.
- Appointments management adds search, status filters, explicit allowed-status saves and counts. Conversations add searchable inbox and message/visitor context; original protected deletion retained.
- Knowledge base enables adding, editing, activation/draft state, search and category. Settings adds controlled hours/holiday validation and an 8-character password minimum.
- Improved logged-out admin login and SETUP_TOKEN setup presentation. Auth/CSRF/session protections preserved.

### Isolated review demo

- Optional `DEMO_MODE` only. One-click **Admin demo** on login represents the application's only real role, admin; no invented user role.
- Discards production DSN, AI credentials and admin bootstrap/secrets for the demo engine. Independent signed demo cookie and secret namespace prevent replay of production cookies.
- New signed session contains an opaque scope; isolated fictional fixtures under `data/demo-<seed>/` mean each review session has its own data, including anonymous demo chat. Does not open production `DATABASE_URL`.
- FAQ creation/editing/deletion and chat deletion restricted to this signed session's ownership; seed/other reviewer records are protected. Fictional appointment status updates enabled with CSRF and allowlist.
- Demo account, provider, schedule and setup operations blocked server-side even for admin+valid CSRF. Local deterministic FAQ/booking prevents external AI/network charges/secrets; this is a guided demonstration, not a claim of external AI capability.
- Demo capacity guard defaults 200 scopes per worker and is documented as non-distributed. Demo SQLite files are disposable and need operator cleanup; Render ephemeral FS resets are expected for the review installation only.

### Delivery maintenance

- Retained ZIP-root `.env.example` for archive layout and Docker Compose; added byte-identical `FrontDesk Project/.env.example` for adjacent local-app setup. Updated Linux/macOS, Windows PowerShell, VPS, Compose and Render instructions to distinguish working directories and private `.env` destinations. No application behavior changed.

- Landing showcase now uses the actual v1.0.4 admin demo dashboard (`static/admin-demo-dashboard.png`) supplied after browser QA. Removed the stale cleaning-price/45-minute example from the landing; updated alt, caption and provenance. No application behavior changed.

- Security headers added; static asset caching; all assets served locally with Tailwind licence notice.
- Updated `README.md`, `HowToSetup.md`, `CLAUDE.md`, `.env.example`, `render.yaml`, `docker-compose.yml`, `docs/overview.md`, `docs/DEMONSTRATION.md`, `docs/SECURITY.md` (roles, route guards, demo tradeoffs, VPS/Docker/Render env and upgrades).
- Archive screenshot folder gets provenance readme: older v1.0.3 product images are not presented as new admin captures.
- Removed generated DB/caches from release ZIP; preserved original v1.0.3 source/ZIP separately. No user contact info in code/docs.

### Verification (v1.0.4)

```
$ python -m pytest -q
......................................
38 passed

$ pip-audit -r requirements.lock
No known vulnerabilities found
```

All 22 earlier tests plus 16 new tests (landing/local assets, real metrics/management, knowledge edit, appointment validation, settings validation, one-click auth, production DSN/credential isolation, privilege protections, local network-free demo, reviewer ownership, demo booking, cross-mode stale cookies, capacity limit and unauthenticated guards). One subprocess/local uvicorn smoke check verifies landing/login/health and does not create a configured production test DSN. Browser QA passed the landing CTAs, one-click admin demo, management pages and opening-hours FAQ without console errors; the dashboard screenshot was replaced accordingly. No unrelated functionality was changed by later documentation/template updates. Automated HTML/test-client checks cannot verify pixel layout or JavaScript click behavior.

Warnings are deprecation notices (SQLAlchemy `datetime.utcnow` and the pinned Starlette TestClient adapter) with no failing assertions. No live deployment, submission, upload, or external AI call was performed.

## 1.0.3

- Public `POST /chat` binds conversations to a signed visitor session (`visitor_token`); foreign / guessed `conversation_id` values return 403
- Chat per-IP rate limit (`request.client.host`) and 2000-character message cap; documented as intentional public endpoint in `docs/SECURITY.md` and README
- `/admin/setup` requires `SETUP_TOKEN`; disabled when an admin exists or `ADMIN_PASSWORD` bootstrap is set
- Login rate limit uses `request.client.host`; documented uvicorn `--proxy-headers --forwarded-allow-ips`
- Removed plaintext password fallback; bcrypt only (passlib removed)
- `SECRET_KEY` placeholder/empty refuses startup outside `FRONTDESK_TESTING=1`
- AI API key encrypted at rest (Fernet derived from `SECRET_KEY`)
- Schema/models: FK cascades, indexes on FK / `updated_at` / `(customer_phone, appointment_time)`; paginated conversations & appointments with `selectinload`; deletes return 404 when missing
- Shared CSRF / rate-limit / template helpers; `app/templating.py`, `app/chat_service.py`, `app/crypto.py`
- Dockerfile installs from `requirements.lock` with `--require-hashes`; added `.dockerignore`
- docker-compose uses root `.env`, forwards `AI_*` / `PORT` / `SETUP_TOKEN`; no business-default fallbacks baked in
- HowToSetup: Python 3.12+, ordered steps, VPS + Docker + Windows, demo admin creation, SECRET_KEY generation
- pip-audit recorded below; dependency pins refreshed (bcrypt, cryptography; passlib dropped)

### Vulnerability audit (1.0.3)

```
$ pip-audit -r requirements.lock
No known vulnerabilities found
```

Pinned runtime set includes fastapi 0.162.0, uvicorn 0.40.0, cryptography 50.0.2,
python-multipart 0.0.31, python-dotenv 1.2.2, bcrypt 4.3.0 (passlib removed).

## 1.0.2

- Reorganized for Vibe96 archive layout: docs and `database/` at ZIP root; all application code inside `FrontDesk Project/`
- Split routes into `routes/public.py`, `routes/auth.py`, `routes/admin.py` with `require_admin` in `app/security.py`
- Admin router declares `dependencies=[Depends(require_admin)]`; every mutating admin handler also lists `Depends(require_admin)`
- Session stores `user` + `role=admin`; role also recorded in settings as `admin_role`
- Added `docs/SECURITY.md` route/guard table and richer `database/seed.sql` demo data
- HowToSetup covers Ubuntu VPS (systemd + nginx), Docker Compose, and Windows (`py`)
- Added mutating-route authorization test; pinned lockfile refreshed

## 1.0.1

- Replaced forgeable `admin=true` cookie with signed Starlette session
- CSRF on admin POST forms; login rate limit; constant-time username compare
- Warns when `SECRET_KEY` is still the default placeholder
- Business hours: Mon–Sat 09:00–18:00, closed Sunday; holidays and hours from settings
- Booking rejects overlap, closed days, holidays, outside hours, and duplicate phone
- Added pytest suite

## 1.0.0

- Web chat, knowledge base, appointment booking, admin dashboard
