"""DATABASE_URL is pasted by hand into a host's settings page; accept the common shapes."""
import pytest
from sqlalchemy.engine import make_url

from app.db import clean_database_url

NEON = "postgresql://neondb_owner:npg_AbC123@ep-cool-sun-a1b2c3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


@pytest.mark.parametrize("pasted", [
    NEON,
    f"  {NEON}\n",
    f"'{NEON}'",
    f'"{NEON}"',
    f"psql '{NEON}'",
    f"DATABASE_URL={NEON}",
])
def test_neon_shapes_all_work(pasted):
    url = make_url(clean_database_url(pasted))
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "ep-cool-sun-a1b2c3.ap-southeast-1.aws.neon.tech"
    assert url.password == "npg_AbC123"
    assert url.query["sslmode"] == "require"


def test_old_postgres_scheme_and_symbols_in_password():
    url = make_url(clean_database_url("postgres://user:p@ss#w/rd?@db.example.com:6543/postgres"))
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss#w/rd?"
    assert url.host == "db.example.com" and url.port == 6543


def test_already_encoded_password_is_not_double_encoded():
    assert make_url(clean_database_url("postgresql://u:p%40ss@h/db")).password == "p@ss"


def test_sqlite_is_left_alone():
    assert clean_database_url("sqlite:///./crunch.db") == "sqlite:///./crunch.db"


@pytest.mark.parametrize("pasted", ["neon.tech", "host=ep-x user=u password=secret123", ""])
def test_unusable_values_explain_without_leaking(pasted):
    with pytest.raises(RuntimeError) as e:
        clean_database_url(pasted)
    assert "postgresql://" in str(e.value) and "secret123" not in str(e.value)
