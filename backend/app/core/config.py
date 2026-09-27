import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "IP-SAKTI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS — wildcard "*" is removed; it defeats allow_credentials and the
    # origin allow-list.  Set CORS_ORIGINS as a comma-separated env var for
    # production deployments.
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ipsakti.in",
    ]
    
    # Latency & Cost SLOs (Section 7.2.3)
    P95_LATENCY_CACHED_MAX_SEC: float = 12.0
    P95_LATENCY_FRESH_MAX_SEC: float = 45.0
    MAX_TOKEN_CEILING_EXTRACTION: int = 1200
    MAX_TOKEN_CEILING_RETRIEVAL: int = 2500
    MAX_TOKEN_CEILING_EXPLANATION: int = 1800
    
    # DPDP Act Grievance Contact
    GRIEVANCE_OFFICER_NAME: str = "Aditya Sharma (Compliance Lead)"
    GRIEVANCE_OFFICER_EMAIL: str = "grievance@ipsakti.in"
    DATA_LOCALIZATION_REGION: str = "ap-south-1 (Mumbai, India)"
    DPDP_RETENTION_DAYS: int = 90
    
    # Backend API Secret — must be overridden via BACKEND_API_KEY_SECRET env var
    # in production.  A random value is generated per-process if unset so that
    # committed defaults can never be used as a shared secret.
    BACKEND_API_KEY_SECRET: str = ""

    # Innovation Lab feature flags — maps "agent.<slug>" (and "innolab.*") to
    # enabled/disabled.  When empty, every agent defaults to its registry value.
    FEATURE_FLAGS: dict[str, bool] = {}

    def __init__(self, **values):
        super().__init__(**values)
        if not self.BACKEND_API_KEY_SECRET:
            self.BACKEND_API_KEY_SECRET = secrets.token_hex(32)
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
