"""Small, safe schema upgrades for databases created by an older version (adds columns only).

For bigger changes later, switch to Alembic.
"""
from sqlalchemy import inspect, text

COLUMNS = [
    ("users", "token_version", "INTEGER NOT NULL DEFAULT 0"),
]


def upgrade(engine) -> list[str]:
    done = []
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table, column, ddl in COLUMNS:
            if table in tables and column not in {c["name"] for c in insp.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                done.append(f"{table}.{column}")
    return done
