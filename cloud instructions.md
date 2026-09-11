# IP-SAKTI Sahayak — Cloud Deployment & Production Infrastructure Guide

> **Theme**: *"IP-SAKTI Sahayak — A multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes."*

---

## 1. Cloud Architecture Overview

IP-SAKTI Sahayak is designed for deployment on modern cloud platforms with **strict compliance with India's Digital Personal Data Protection Act, 2023 (DPDP Act)** and enterprise data residency requirements.

```
+-----------------------------------------------------------------------------------------------+
|                                      CLOUD INFRASTRUCTURE                                      |
|                                                                                               |
|  [ CloudFront / CDN + WAF ]                                                                    |
|           │                                                                                   |
|           ▼                                                                                   |
|  [ ALB / Reverse Proxy (SSL / Rate Limiting / TLS 1.3) ]                                      |
|           │                                                                                   |
|     ┌─────┴──────────────────────────────┐                                                    |
|     ▼                                    ▼                                                    |
|  [ Next.js Frontend Cluster ]      [ FastAPI Backend Monolith Cluster ]                       |
|  (Node.js 20+ Container)           (Python 3.11 Gunicorn/Uvicorn Workers)                     |
|                                          │                                                    |
|                    ┌─────────────────────┼─────────────────────┐                              |
|                    ▼                     ▼                     ▼                              |
|           [ PostgreSQL + pgvector ] [ MinIO / S3 ]   [ Isolated Sandbox ]                     |
|           (Relational + Vectors)   (Encrypted Docs) (Text/PDF Extraction)                     |
+-----------------------------------------------------------------------------------------------+
```

---

## 2. Docker Compose (Local & Production-Ready Setup)

The system includes a production-grade multi-container compose configuration:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ipsakti_backend
    restart: always
    environment:
      - ENVIRONMENT=production
      - HOST=0.0.0.0
      - PORT=8000
      - CORS_ORIGINS=http://localhost:3000,https://ipsakti.in
      - DATABASE_URL=postgresql://ipsakti_user:secure_pwd@postgres:5432/ipsakti_db
      - LLM_PROVIDER=anthropic_or_gemini
      - API_KEY_SECRET=${BACKEND_API_KEY_SECRET}
      - DPDP_CONSENT_AUDIT_LOG=/data/audit_logs/dpdp_consent.log
    ports:
      - "8000:8000"
    volumes:
      - backend_data:/data
    depends_on:
      - postgres

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ipsakti_frontend
    restart: always
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
      - NODE_ENV=production
    ports:
      - "3000:3000"
    depends_on:
      - backend

  postgres:
    image: pgvector/pgvector:pg16
    container_name: ipsakti_postgres
    restart: always
    environment:
      - POSTGRES_USER=ipsakti_user
      - POSTGRES_PASSWORD=secure_pwd
      - POSTGRES_DB=ipsakti_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  backend_data:
  postgres_data:
```

---

## 3. Data Protection & DPDP Act 2023 Compliance Architecture

1. **Data Localization (India First)**:
   - Primary database and file storage instances reside in `ap-south-1` (Mumbai) or `me-central-1`.
   - Private proprietary Ayurvedic formulations and batch records never leave domestic boundaries without explicit user consent.
2. **Strict Encryption Standards**:
   - TLS 1.3 in transit with AES-256-GCM encryption at rest for all database volumes and object stores.
3. **Consent Logging & Grievance Redressal**:
   - Every passport creation, external AI routing, and expert handoff logs a cryptographic hash of the user consent agreement.
   - Designated Grievance Officer details are embedded in compliance endpoints (`/api/v1/compliance/grievance`).

---

## 4. Multi-Cloud Deployment Blueprints

### AWS Architecture
- **Compute**: AWS ECS Fargate or EKS with Auto-Scaling Groups.
- **Database**: AWS Aurora PostgreSQL Serverless with `pgvector`.
- **Storage**: AWS S3 with Object Lock and SSE-KMS Customer Managed Keys.
- **Edge**: AWS CloudFront + AWS WAF (rate limiting, OWASP Top 10 rule set).

### GCP Architecture
- **Compute**: Google Cloud Run (Backend & Frontend services).
- **Database**: Cloud SQL for PostgreSQL with vector extension.
- **Storage**: Cloud Storage (Regional bucket in `asia-south1`).
- **AI Gateway**: Vertex AI private VPC endpoint.

---

## 5. CI/CD & Automated Deployment Pipeline

1. **Lint & Security Scan**: Run `flake8`, `mypy`, `npm run lint`, and `bandit` on backend/frontend code.
2. **Adversarial Red-Team Gate**: Execute `pytest backend/tests/test_sandboxing.py` to ensure prompt injection filtering survives code updates.
3. **Gold-Case Benchmark Gate**: Run `python backend/app/evals/benchmark_runner.py`. If Unsupported Claim Rate (UCR) exceeds 0.05, build fails automatically.
4. **Zero-Downtime Rolling Update**: Deploy to staging, verify health checks at `/api/v1/health`, then promote to production.
