from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.db_models import generate_uuid


class InnolabProjectDB(Base):
    __tablename__ = "innolab_projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(300), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    status = Column(String(40), nullable=False, default="draft")  # draft|active|archived
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    sensitivity = Column(String(30), nullable=False, default="standard")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    members = relationship("InnolabProjectMemberDB", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("InnolabRunDB", back_populates="project", cascade="all, delete-orphan")


class InnolabProjectMemberDB(Base):
    __tablename__ = "innolab_project_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("innolab_projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String(40), nullable=False, default="viewer")  # owner|editor|reviewer|viewer
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("InnolabProjectDB", back_populates="members")


class InnolabRunDB(Base):
    __tablename__ = "innolab_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("innolab_projects.id"), nullable=False)
    initiator_id = Column(String, ForeignKey("users.id"), nullable=False)
    run_type = Column(String(60), nullable=False)  # workflow|passport|export_template
    status = Column(String(30), nullable=False, default="pending")  # pending|running|needs_review|completed|failed|cancelled
    current_step = Column(String(120), nullable=True)
    feature_flags_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)

    project = relationship("InnolabProjectDB", back_populates="runs")
    steps = relationship("InnolabRunStepDB", back_populates="run", cascade="all, delete-orphan", order_by="InnolabRunStepDB.seq")


class InnolabRunStepDB(Base):
    __tablename__ = "innolab_run_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=False)
    seq = Column(Integer, nullable=False)
    agent_slug = Column(String(60), nullable=False)
    status = Column(String(30), nullable=False, default="pending")  # pending|running|completed|failed|blocked
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    run = relationship("InnolabRunDB", back_populates="steps")


class InnolabInputDB(Base):
    __tablename__ = "innolab_inputs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("innolab_projects.id"), nullable=False)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=True)
    kind = Column(String(30), nullable=False)  # idea|formulation|label|ingredient|country|question
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, default="en")
    threat_flags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabDocumentDB(Base):
    __tablename__ = "innolab_documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("innolab_projects.id"), nullable=False)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=True)
    filename = Column(String(300), nullable=False)
    media_type = Column(String(120), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    source = Column(String(30), nullable=False, default="upload")  # upload|provider|system
    status = Column(String(30), nullable=False, default="received")  # received|sanitized|chunked|embedded|failed
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabChunkDB(Base):
    __tablename__ = "innolab_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("innolab_documents.id"), nullable=False)
    seq = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_estimate = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabSourceCitationDB(Base):
    __tablename__ = "innolab_source_citations"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=False)
    agent_slug = Column(String(60), nullable=False)
    kind = Column(String(30), nullable=False)  # statute|rule|case|patent|litigation|clinical|article|document|provider
    label = Column(String(255), nullable=False)
    url = Column(String(600), nullable=True)
    snippet = Column(Text, nullable=True)
    ref = Column(String(255), nullable=True)
    provider = Column(String(60), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabEvidenceDB(Base):
    __tablename__ = "innolab_evidence"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=False)
    agent_slug = Column(String(60), nullable=False)
    kind = Column(String(30), nullable=False)  # novelty|inventive_step|regulatory|evidence_quality|claim
    finding = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="info")  # info|warning|critical
    status = Column(String(30), nullable=False, default="unverified")  # unverified|verified_min|verified|disputed|void
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabClaimDB(Base):
    __tablename__ = "innolab_claims"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    category = Column(String(60), nullable=True)
    status = Column(String(30), nullable=False, default="draft")  # draft|under_review|approved|rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabClaimEvidenceLinkDB(Base):
    __tablename__ = "innolab_claim_evidence_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    claim_id = Column(String, ForeignKey("innolab_claims.id"), nullable=False)
    evidence_id = Column(String, ForeignKey("innolab_evidence.id"), nullable=False)
    strength = Column(String(30), nullable=True)  # direct|strong|moderate|weak|contradicts
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabReviewDB(Base):
    __tablename__ = "innolab_reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=False)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(30), nullable=False, default="open")  # open|approved|changes_requested
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InnolabExportDB(Base):
    __tablename__ = "innolab_exports"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=False)
    format = Column(String(20), nullable=False)  # pdf|docx|xlsx|json
    status = Column(String(30), nullable=False, default="pending")  # pending|ready|failed
    filename = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabProviderDB(Base):
    __tablename__ = "innolab_providers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(120), nullable=False, unique=True)
    slug = Column(String(60), nullable=False, unique=True)
    kind = Column(String(40), nullable=False)  # public_data|patsnap|uspto|wipo|mock
    base_url = Column(String(300), nullable=True)
    api_key_env = Column(String(120), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    mode = Column(String(20), nullable=False, default="mock")  # mock|live
    last_status = Column(String(20), nullable=False, default="idle")  # idle|ok|error|not_configured
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabUsageLogDB(Base):
    __tablename__ = "innolab_usage_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("innolab_runs.id"), nullable=True)
    agent_slug = Column(String(60), nullable=True)
    provider = Column(String(60), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    credits = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabAuditEventDB(Base):
    __tablename__ = "innolab_audit_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    project_id = Column(String, ForeignKey("innolab_projects.id"), nullable=True)
    action = Column(String(80), nullable=False)
    resource = Column(String(120), nullable=True)
    detail = Column(JSON, nullable=True)
    ip_address = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InnolabFeatureFlagDB(Base):
    __tablename__ = "innolab_feature_flags"

    flag = Column(String(80), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
