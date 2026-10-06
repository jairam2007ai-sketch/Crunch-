import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import config_problems, get_settings
from .db import Base, SessionLocal, engine
from .deps import is_local_request
from .middleware import SecurityMiddleware, build_csp, inline_script_hashes
from .migrate import upgrade
from .models import User
from .routers import admin, ai, auth, dashboard, inventory, orders, public, refunds, setup
from .security import hash_password, password_weakness
from .seed import ensure_seed

log = logging.getLogger("crunch")
settings = get_settings()
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    errors, warnings = config_problems(settings)
    if errors:
        raise RuntimeError("Unsafe settings, so the server won't start:\n- " + "\n- ".join(errors))
    for w in warnings:
        log.warning(w)
    Base.metadata.create_all(engine)
    upgrade(engine)
    with SessionLocal() as db:
        ensure_seed(db)
        has_users = db.scalar(select(User.id).limit(1)) is not None
        if settings.owner_email and settings.owner_password:
            if has_users:
                log.warning("OWNER_PASSWORD is still set. The owner account exists, so remove it from your settings.")
            elif problem := password_weakness(settings.owner_password, settings.owner_email, settings.owner_name):
                raise RuntimeError(f"OWNER_PASSWORD isn't strong enough: {problem}")
            else:
                db.add(User(name=settings.owner_name, email=settings.owner_email.strip().lower(),
                            password_hash=hash_password(settings.owner_password), role="owner"))
                db.commit()
        elif settings.is_production and not has_users:
            # the browser setup form is switched off in production, so the owner must come from settings
            raise RuntimeError("No owner account yet. Set OWNER_EMAIL and OWNER_PASSWORD in your host's environment "
                               "settings for the first start, then remove OWNER_PASSWORD.")
    yield


# The automatic API docs are off by default and served below only to this computer.
app = FastAPI(title="Crunch Business Manager", version="1.1.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    SecurityMiddleware,
    csp=build_csp(inline_script_hashes(DIST) if DIST.is_dir() else [],
                  [o.strip() for o in settings.csp_connect_extra.split(",") if o.strip()], settings.is_production),
    hsts=settings.is_production,
    max_body=settings.max_request_bytes,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in settings.cors_list if o != "*"],
    allow_credentials=False,  # sign-in travels in the Authorization header, never in cookies
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

for r in (auth.router, public.router, orders.router, refunds.router, inventory.router, admin.router,
          dashboard.router, ai.router, setup.router):
    app.include_router(r)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # details go to the server log only; visitors never see code or stack traces
    log.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong on our side. Please try again."}, status_code=500)


@app.get("/api/health")
def health():
    return {"ok": True}


def _docs_allowed(request: Request) -> bool:
    return settings.api_docs_public or is_local_request(request)


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_json(request: Request):
    if not _docs_allowed(request):
        raise HTTPException(404, "Not Found")
    return JSONResponse(app.openapi())


@app.get("/api/docs", include_in_schema=False)
def api_docs(request: Request):
    if not _docs_allowed(request):
        raise HTTPException(404, "Not Found")
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="Crunch API")


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"], include_in_schema=False)
def api_not_found(rest: str):
    # unknown API paths answer 404 here instead of falling through to the websites
    raise HTTPException(404, "Not Found")


# Serve the built websites from the same server (one service to deploy). Only frontend/dist
# is exposed: never the source code, .env files or the database.
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="sites")
