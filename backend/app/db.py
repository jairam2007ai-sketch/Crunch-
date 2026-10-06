import re
from urllib.parse import quote, unquote

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings


class Base(DeclarativeBase):
    pass


_PG_URL = re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^\s'\"]+")
BAD_URL = ("DATABASE_URL isn't a valid database address. In Neon, open Connect, choose 'Connection string', "
           "and copy the line that starts with postgresql:// (not the psql command, and without quotes). "
           "Paste only that into DATABASE_URL.")


def clean_database_url(raw: str) -> str:
    """Accept what people actually paste: Neon's psql command, quotes, spaces, or a password with
    symbols like @ or #. Returns a SQLAlchemy URL using the psycopg driver. Never echoes the URL,
    because it contains the database password."""
    text = (raw or "").strip().strip("'\"").strip()
    if text.startswith("sqlite"):
        return text
    found = _PG_URL.search(text)
    if not found:
        raise RuntimeError(BAD_URL)
    text = found.group(0)
    scheme, _, rest = text.partition("://")
    # the last @ separates the sign-in details from the host; encode symbols in the user and password
    userinfo, at, hostpart = rest.rpartition("@")
    if at:
        user, colon, password = userinfo.partition(":")
        userinfo = quote(unquote(user), safe="") + (":" + quote(unquote(password), safe="") if colon else "")
        rest = f"{userinfo}@{hostpart}"
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+psycopg"
    url = f"{scheme}://{rest}"
    try:
        make_url(url)
    except ArgumentError:
        raise RuntimeError(BAD_URL) from None
    return url


def make_engine(raw_url: str):
    url = clean_database_url(raw_url)
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
