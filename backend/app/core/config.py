import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "IP-SAKTI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ipsakti.in",
        "*"
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
    
    # Backend API Secret (never sent to frontend)
    BACKEND_API_KEY_SECRET: str = "ipsakti_secure_production_secret_key_2026"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
