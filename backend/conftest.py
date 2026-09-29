import importlib
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="ipsakti-pytest-"))
_TEST_DATABASE = _TEST_ROOT / "ipsakti-test.db"
_TEST_DATABASE_URL = f"sqlite+pysqlite:///{_TEST_DATABASE.as_posix()}"
_TEST_QDRANT_URL = os.environ.get("TEST_QDRANT_URL", "")
_TEST_QDRANT_LOCAL_PATH = os.environ.get(
    "QDRANT_LOCAL_PATH",
    "" if _TEST_QDRANT_URL else str(_TEST_ROOT / "qdrant"),
)
_TEST_PASSWORD = "TestPass123!"

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", _TEST_DATABASE_URL),
        "BACKEND_API_KEY_SECRET": "pytest-only-admin-key-not-for-production",
        "CORS_ORIGINS": '["http://127.0.0.1:13000","http://localhost:13000"]',
        "IPSAKTI_USE_BGE_M3": "0",
        "IPSAKTI_USE_RERANKER": "0",
        "IPSAKTI_LIVE_WEB": "0",
        "IPSAKTI_WEB_MAX_FETCHES": "0",
        "IPSAKTI_LLM_PROVIDER": "mock",
        "IPSAKTI_INGESTION_SCHEDULER": "0",
        "IPSAKTI_RAG_DEFAULT": "combined",
        "IPSAKTI_RAG_CACHE_TTL": "3600",
        "IPSAKTI_RAG_RATE_LIMIT": "1000",
        "QDRANT_URL": _TEST_QDRANT_URL or "http://127.0.0.1:56333",
        "QDRANT_LOCAL_PATH": _TEST_QDRANT_LOCAL_PATH,
        "REDIS_URL": os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:56379/15"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }
)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    store_module = sys.modules.get("app.rag.qdrant_store")
    if store_module is not None:
        store = store_module.QdrantVectorStore
        if store._client is not None:
            try:
                store._client.close()
            except Exception:
                pass
            store._client = None
        store._instance = None
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def test_root() -> Path:
    return _TEST_ROOT


@pytest.fixture
def test_data_dir() -> Path:
    return Path(__file__).parent / "tests" / "fixtures"


@pytest.fixture
def passport_payload(test_data_dir: Path):
    with (test_data_dir / "passport.json").open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def rag_documents(test_data_dir: Path):
    with (test_data_dir / "rag_documents.json").open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def disclosure_file(test_data_dir: Path) -> Path:
    return test_data_dir / "disclosure.txt"


@pytest.fixture
def adversarial_document_file(test_data_dir: Path) -> Path:
    return test_data_dir / "adversarial_disclosure.txt"


@pytest.fixture
def db_session() -> Iterator:
    from app.core.database import Base, SessionLocal, engine

    importlib.import_module("app.models.db_models")
    importlib.import_module("app.models.innolab_models")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    from app.auth.jwt_auth import get_password_hash
    from app.core.database import SessionLocal
    from tests.factories import UserFactory

    user = UserFactory()
    user.hashed_password = get_password_hash(_TEST_PASSWORD)
    db = SessionLocal()
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    finally:
        db.close()
    return user


@pytest.fixture
def other_user(db_session):
    from app.auth.jwt_auth import get_password_hash
    from app.core.database import SessionLocal
    from tests.factories import UserFactory

    user = UserFactory()
    user.hashed_password = get_password_hash(_TEST_PASSWORD)
    db = SessionLocal()
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    finally:
        db.close()
    return user


@pytest.fixture
def admin_user(db_session):
    from app.auth.jwt_auth import get_password_hash
    from app.core.database import SessionLocal
    from tests.factories import UserFactory

    user = UserFactory(role="admin")
    user.hashed_password = get_password_hash(_TEST_PASSWORD)
    db = SessionLocal()
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    finally:
        db.close()
    return user


@pytest.fixture
def auth_headers(test_user) -> dict[str, str]:
    from app.auth.jwt_auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': test_user.id})}"}


@pytest.fixture
def other_auth_headers(other_user) -> dict[str, str]:
    from app.auth.jwt_auth import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': other_user.id})}"}


@pytest.fixture
def api_client(db_session):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client(api_client, auth_headers):
    api_client.headers.update(auth_headers)
    return api_client


@pytest.fixture
def test_passport(db_session, passport_payload):
    from app.services.passport_engine import PassportEngine

    PassportEngine._passports_store.clear()
    intake_keys = {
        "product_type",
        "category",
        "target_markets",
        "extraction_method",
        "solvent",
        "temperature",
        "time",
        "processing_steps",
        "proposed_claims",
    }
    intake = {key: passport_payload[key] for key in intake_keys if key in passport_payload}
    passport = PassportEngine.create_from_intake(
        raw_text=passport_payload["raw_text"],
        user_lang=passport_payload.get("user_lang", "en"),
        title=passport_payload.get("case_title", "Test Formulation"),
        intake=intake,
    )
    yield passport
    PassportEngine._passports_store.clear()


@pytest.fixture
def test_password() -> str:
    return _TEST_PASSWORD
