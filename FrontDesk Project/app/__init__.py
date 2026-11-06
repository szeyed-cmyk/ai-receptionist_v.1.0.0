import os

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import enforce_secret_key, settings
from app.database import Base, registry
from routes import router

enforce_secret_key()
app = FastAPI(title="FrontDesk AI", version="1.0.4")

if settings.demo_mode:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key + "|frontdesk-demo|" + settings.demo_seed,
        session_cookie="frontdesk_demo_session", same_site="lax",
        https_only=bool(settings.https_only), max_age=60 * 60 * 12,
    )


@app.middleware("http")
async def request_safety(request: Request, call_next):
    # Normal production sessions are validated in require_admin as before.
    # Demo code must not assume any order between early dependencies; all
    # real scoped DB access binds to verified demo role + scope in get_db.
    response: Response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=3600")
    return response

if not settings.demo_mode:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key, session_cookie="frontdesk_session",
        same_site="lax", https_only=bool(settings.https_only), max_age=60 * 60 * 12,
    )

_static = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")
elif os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


def initialise_database():
    """Create tables after route imports registered every model."""
    for db_engine in registry.engines.values():
        Base.metadata.create_all(bind=db_engine)
    if settings.demo_mode:
        from app.demo import ensure_demo_admin, seed_demo_data
        _, Bootstrap = registry.bind()
        with Bootstrap() as db:
            ensure_demo_admin(db)
            seed_demo_data(db)


app.include_router(router)
initialise_database()


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.4", "demo_mode": settings.demo_mode}
