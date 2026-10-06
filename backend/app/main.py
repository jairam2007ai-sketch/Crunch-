from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import DEV_SECRET, get_settings
from .db import Base, SessionLocal, engine
from .models import User
from .security import hash_password
from .routers import admin, ai, auth, dashboard, inventory, orders, public, refunds, setup
from .seed import ensure_seed

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.is_production and settings.jwt_secret == DEV_SECRET:
        raise RuntimeError("Set JWT_SECRET to a long random value before running in production.")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_seed(db)
        if settings.owner_email and len(settings.owner_password) >= 8 and not db.scalar(select(User.id).limit(1)):
            db.add(User(name=settings.owner_name, email=settings.owner_email.strip().lower(),
                        password_hash=hash_password(settings.owner_password), role="owner"))
            db.commit()
    yield


app = FastAPI(title="Crunch Business Manager", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, public.router, orders.router, refunds.router, inventory.router, admin.router,
          dashboard.router, ai.router, setup.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}


# Optional: serve the built websites from the same server (one service to deploy).
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="sites")
