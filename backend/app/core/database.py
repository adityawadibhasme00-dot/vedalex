import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ipsakti"
)

SQLITE_URL = "sqlite:///./ipsakti.db"

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    engine.connect()
except Exception:
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# (table, column, ddl_type) — applied idempotently on startup so existing SQLite
# databases created before a column was added keep working without manual reset.
_MISSING_COLUMN_MIGRATIONS = [
    ("innovation_passports", "unresolved_clarifications", "JSON"),
]

def init_db():
    Base.metadata.create_all(bind=engine)
    _apply_column_migrations()

def _apply_column_migrations():
    try:
        with engine.connect() as conn:
            for table, column, col_type in _MISSING_COLUMN_MIGRATIONS:
                has_table = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_name = :t"
                    ),
                    {"t": table},
                ).scalar() if engine.dialect.name != "sqlite" else _has_sqlite_table(conn, table)
                if not has_table:
                    continue
                columns = [
                    row[1].lower()
                    for row in conn.execute(text(f"PRAGMA table_info({table})"))
                ] if engine.dialect.name == "sqlite" else [
                    row[0].lower()
                    for row in conn.execute(
                        text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
                        {"t": table},
                    )
                ]
                if column not in columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
    except Exception as e:
        print(f"Column migration skipped: {e}")

def _has_sqlite_table(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = :t"),
        {"t": table},
    ).scalar()
    return bool(row)
