"""DATABASE_URL is pasted by hand into a host's settings page; accept the common shapes and
explain the common mistakes without ever repeating the password."""
import pytest
from sqlalchemy.engine import make_url

from app.db import DatabaseUrlError, clean_database_url, explain_connection_error

NEON = "postgresql://neondb_owner:npg_AbC123@ep-cool-sun-a1b2c3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
POOLER = "postgresql://postgres.abcdefghijkl:Tasty-Chips-42@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"


@pytest.mark.parametrize("pasted", [
    NEON, f"  {NEON}\n", f"'{NEON}'", f'"{NEON}"', f"psql '{NEON}'", f"DATABASE_URL={NEON}",
    NEON.replace("postgresql://", "jdbc:postgresql://"), NEON.replace("postgresql://", "postgresql+asyncpg://"),
])
def test_neon_shapes_all_work(pasted):
    url = make_url(clean_database_url(pasted))
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "ep-cool-sun-a1b2c3.ap-southeast-1.aws.neon.tech"
    assert url.password == "npg_AbC123"
    assert url.query["sslmode"] == "require"


def test_supabase_session_pooler():
    url = make_url(clean_database_url(POOLER))
    assert url.username == "postgres.abcdefghijkl" and url.port == 5432 and url.password == "Tasty-Chips-42"


def test_libpq_keyword_form():
    url = make_url(clean_database_url("host=ep-x.neon.tech port=5432 dbname=neondb user=me password='p w' sslmode=require"))
    assert url.host == "ep-x.neon.tech" and url.username == "me" and url.password == "p w" and url.database == "neondb"


def test_old_postgres_scheme_and_symbols_in_password():
    url = make_url(clean_database_url("postgres://user:p@ss#w/rd?@db.example.com:6543/postgres"))
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss#w/rd?" and url.host == "db.example.com" and url.port == 6543


def test_already_encoded_password_is_not_double_encoded():
    assert make_url(clean_database_url("postgresql://u:p%40ss@h/db")).password == "p@ss"


def test_sqlite_is_left_alone():
    assert clean_database_url("sqlite:///./crunch.db") == "sqlite:///./crunch.db"


@pytest.mark.parametrize("pasted,says", [
    ("https://abcdefghijkl.supabase.co", "website address"),
    ("https://console.neon.tech/app/projects/x", "website address"),
    ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret123", "API key"),
    ("postgresql://postgres.abc:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres", "[YOUR-PASSWORD]"),
    ("neon.tech", "should start with postgresql://"),
    ("", "should start with postgresql://"),
])
def test_common_mistakes_are_named(pasted, says):
    with pytest.raises(DatabaseUrlError) as e:
        clean_database_url(pasted)
    assert says in str(e.value) and "secret123" not in str(e.value)


class FakeDriverError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.orig = msg


def test_connection_errors_get_plain_hints():
    direct = clean_database_url("postgresql://postgres:Secret99@db.abcdefghijkl.supabase.co:5432/postgres")
    msg = explain_connection_error(FakeDriverError("connection is bad: Network is unreachable"), direct)
    assert "IPv6" in msg and "Session pooler" in msg and "Secret99" not in msg
    msg = explain_connection_error(FakeDriverError('FATAL: password authentication failed for user "postgres"'),
                                   clean_database_url(POOLER))
    assert "password is wrong" in msg and "Tasty-Chips-42" not in msg
