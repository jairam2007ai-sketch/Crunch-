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
_SUPABASE_DIRECT = re.compile(r"^db\.[a-z0-9]+\.supabase\.co$")

HOW_TO = ("Supabase: open your project, click Connect at the top, choose 'Session pooler', copy the "
          "postgresql:// string and replace [YOUR-PASSWORD] with your database password. "
          "Neon: open Connect, choose 'Connection string', copy the line starting with postgresql://.")


class DatabaseUrlError(RuntimeError):
    pass


def _bad(what: str) -> DatabaseUrlError:
    return DatabaseUrlError(f"DATABASE_URL {what} {HOW_TO}")


def _from_keywords(text: str) -> str | None:
    """libpq style: host=... port=... dbname=... user=... password=... sslmode=..."""
    pairs = dict(re.findall(r"(\w+)=('[^']*'|\S+)", text))
    if "host" not in pairs:
        return None
    v = {k: val.strip("'") for k, val in pairs.items()}
    user = quote(v.get("user", "postgres"), safe="")
    pw = (":" + quote(v["password"], safe="")) if "password" in v else ""
    port = f":{v['port']}" if "port" in v else ""
    query = f"?sslmode={v['sslmode']}" if "sslmode" in v else ""
    return f"postgresql://{user}{pw}@{v['host']}{port}/{v.get('dbname', 'postgres')}{query}"


def clean_database_url(raw: str) -> str:
    """Accept what people actually paste and return a SQLAlchemy URL for the psycopg driver.

    Handles Neon's psql command, quotes, spaces, the libpq key=value form, other driver names
    and symbols in the password. Explains common mistakes (a website address, an API key, the
    [YOUR-PASSWORD] placeholder). Never repeats the value, because it contains the password.
    """
    text = (raw or "").strip().strip("'\"").strip()
    if text.startswith("sqlite"):
        return text
    found = _PG_URL.search(text)
    if found:
        text = found.group(0)
    elif (kw := _from_keywords(text)) is not None:
        text = kw
    elif re.match(r"https?://", text, re.I):
        raise _bad("is a website address (https://...). That's your project's web or API address, not its database address.")
    elif text.startswith("eyJ") or text.startswith(("sb_", "sk_", "pk_")):
        raise _bad("looks like an API key, not a database address.")
    else:
        raise _bad("isn't a database address (it should start with postgresql://).")

    scheme, _, rest = text.partition("://")
    userinfo, at, hostpart = rest.rpartition("@")  # the last @ ends the sign-in details
    if at:
        user, colon, password = userinfo.partition(":")
        if "YOUR-PASSWORD" in password.upper() or password.startswith("["):
            raise DatabaseUrlError("DATABASE_URL still has the [YOUR-PASSWORD] placeholder in it. Replace it "
                                   "(brackets included) with your database password. Forgot it? In Supabase: "
                                   "Project Settings > Database > Reset database password.")
        if colon and not password:
            raise _bad("has no password in it.")
        userinfo = quote(unquote(user), safe="") + (":" + quote(unquote(password), safe="") if colon else "")
        rest = f"{userinfo}@{hostpart}"
    url = f"postgresql+psycopg://{rest}"  # whatever driver was named, this app uses psycopg
    try:
        make_url(url)
    except ArgumentError:
        raise _bad("couldn't be read as a database address.") from None
    return url


def database_host(url: str) -> str:
    try:
        return make_url(url).host or ""
    except ArgumentError:
        return ""


def explain_connection_error(exc: Exception, url: str) -> str:
    """Plain-language reason a database connection failed. Names the host, never the password."""
    detail = str(getattr(exc, "orig", None) or exc).strip().splitlines()[0][:240]
    low = detail.lower()
    host = database_host(url)
    if _SUPABASE_DIRECT.match(host):
        hint = ("You used Supabase's direct address (db.....supabase.co). It only works over IPv6, which Render "
                "doesn't support. Use the Session pooler string instead: Connect > Session pooler.")
    elif "password authentication failed" in low:
        hint = ("The database password is wrong. In Supabase: Project Settings > Database > Reset database password, "
                "then put the new password into DATABASE_URL.")
    elif "tenant or user not found" in low:
        hint = ("Copy the Session pooler string exactly: its user name looks like postgres.abcdefgh (with your project id).")
    elif "could not translate host" in low or "failed to resolve host" in low or "name or service not known" in low:
        hint = "The host name in DATABASE_URL doesn't exist. Copy the connection string again."
    elif "timeout" in low or "timed out" in low or "unreachable" in low:
        hint = "The database didn't answer. Check the project isn't paused (Supabase pauses unused free projects) and copy the string again."
    else:
        hint = "Copy the connection string again and check the database project is running."
    return f"Can't connect to the database at {host or 'the given address'} ({detail}). {hint}"


def make_engine(raw_url: str):
    url = clean_database_url(raw_url)
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    else:
        # Free Postgres plans allow few connections and close idle ones; poolers (Supabase, Neon)
        # don't support prepared statements in transaction mode, so switch those off.
        kwargs.update(pool_size=3, max_overflow=4, pool_recycle=280, pool_timeout=20,
                      connect_args={"prepare_threshold": None, "connect_timeout": 15})
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return engine


DATABASE_URL = clean_database_url(get_settings().database_url)
engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
