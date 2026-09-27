import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ipsakti"
)

SQLITE_URL = "sqlite:///./ipsakti.db"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default


# Connection-pool sizing.  SQLAlchemy's implicit default is pool_size=5 with
# max_overflow=10, i.e. 15 connections per process.  That, not CPU or memory, was
# the hard ceiling on concurrent requests: every RAG answer holds a session while
# embedding, reranking and calling the LLM.
#
# Sized for the threadpool that now serves the sync route handlers
# (anyio default 40 threads), with headroom for the ingestion scheduler and
# background jobs that also take sessions.
POOL_SIZE = _int_env("IPSAKTI_DB_POOL_SIZE", 20)
MAX_OVERFLOW = _int_env("IPSAKTI_DB_MAX_OVERFLOW", 40)
POOL_RECYCLE_SEC = _int_env("IPSAKTI_DB_POOL_RECYCLE", 1800)
POOL_TIMEOUT_SEC = _int_env("IPSAKTI_DB_POOL_TIMEOUT", 30)

_POOL_KWARGS = {
    "pool_pre_ping": True,  # recycle connections dropped by the server / proxy
    "pool_size": POOL_SIZE,
    "max_overflow": MAX_OVERFLOW,
    "pool_recycle": POOL_RECYCLE_SEC,  # stay under typical 30min proxy timeouts
    "pool_timeout": POOL_TIMEOUT_SEC,  # fail fast instead of hanging a worker
}

try:
    engine = create_engine(DATABASE_URL, poolclass=QueuePool, **_POOL_KWARGS)
    engine.connect()
except Exception:
    # SQLite is the offline demo / evaluation fallback, never a production
    # target: every write serialises on a single file lock.  NullPool avoids
    # handing out cached connections across threads, and the small timeout
    # makes the contention visible instead of silently queueing forever.
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False, "timeout": POOL_TIMEOUT_SEC},
        poolclass=NullPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#: True when the process fell back to the file-backed SQLite demo store.
USING_SQLITE = engine.dialect.name == "sqlite"

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
