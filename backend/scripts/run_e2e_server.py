import os
import sys
from pathlib import Path

import uvicorn

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = BACKEND_ROOT / ".e2e.db"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}",
        "BACKEND_API_KEY_SECRET": "e2e-only-admin-key-not-for-production",
        "CORS_ORIGINS": '["http://127.0.0.1:13000","http://localhost:13000"]',
        "IPSAKTI_USE_BGE_M3": "0",
        "IPSAKTI_USE_RERANKER": "0",
        "IPSAKTI_LIVE_WEB": "0",
        "IPSAKTI_WEB_MAX_FETCHES": "0",
        "IPSAKTI_LLM_PROVIDER": "mock",
        "IPSAKTI_INGESTION_SCHEDULER": "0",
        "IPSAKTI_RAG_CACHE_TTL": "3600",
        "IPSAKTI_RAG_RATE_LIMIT": "1000",
        "QDRANT_URL": "http://127.0.0.1:56333",
        "REDIS_URL": "redis://127.0.0.1:56379/15",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }
)

DATABASE_PATH.unlink(missing_ok=True)

uvicorn.run("app.main:app", host="127.0.0.1", port=18000, reload=False)
