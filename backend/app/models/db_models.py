import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="researcher")
    institution = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    passports = relationship("InnovationPassportDB", back_populates="owner")
    chat_history = relationship("ChatHistory", back_populates="user")

class InnovationPassportDB(Base):
    __tablename__ = "innovation_passports"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    case_title = Column(String(200), nullable=False)
    product_form = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=True)
    intended_use = Column(Text, nullable=True)
    proposed_claims = Column(JSON, default=list)
    claimed_innovation = Column(Text, nullable=True)
    process_description = Column(Text, nullable=True)
    target_markets = Column(JSON, default=list)
    business_role = Column(String(100), nullable=True)
    biological_resource_origin = Column(String(100), nullable=True)
    version = Column(Integer, default=1)
    unresolved_clarifications = Column(JSON, default=list)
    qr_code = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="passports")
    ingredients = relationship("IngredientDB", back_populates="passport", cascade="all, delete-orphan")
    evidence = relationship("EvidenceDB", back_populates="passport", cascade="all, delete-orphan")
    patent_scores = relationship("PatentScoreDB", back_populates="passport", cascade="all, delete-orphan")
    claims = relationship("ClaimDB", back_populates="passport", cascade="all, delete-orphan")

class IngredientDB(Base):
    __tablename__ = "ingredients"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False)
    raw_name = Column(String(100), nullable=False)
    canonical_id = Column(String(100), nullable=True)
    botanical_name = Column(String(200), nullable=True)
    api_monograph_id = Column(String(50), nullable=True)
    plant_part = Column(String(100), nullable=True)
    preparation_method = Column(String(100), nullable=True)
    quantity_percentage = Column(Float, default=0.0)
    origin_status = Column(String(50), default="PENDING")
    language_detected = Column(String(10), nullable=True)

    passport = relationship("InnovationPassportDB", back_populates="ingredients")

class EvidenceDB(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    evidence_type = Column(String(50), nullable=False)
    evidence_status = Column(String(50), default="MISSING")
    source_reference = Column(Text, nullable=True)
    document_path = Column(String(500), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    passport = relationship("InnovationPassportDB", back_populates="evidence")

class PatentScoreDB(Base):
    __tablename__ = "patent_scores"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False)
    novelty_score = Column(Float, default=0.0)
    inventive_step_score = Column(Float, default=0.0)
    overall_readiness = Column(Float, default=0.0)
    similar_patents = Column(JSON, default=list)
    missing_evidence = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    passport = relationship("InnovationPassportDB", back_populates="patent_scores")

class ClaimDB(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    claim_category = Column(String(50), nullable=True)
    risk_level = Column(String(20), default="LOW")
    evidence_supported = Column(Boolean, default=False)
    regulatory_note = Column(Text, nullable=True)

    passport = relationship("InnovationPassportDB", back_populates="claims")

class SupplierDB(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False)
    supplier_name = Column(String(200), nullable=False)
    geography = Column(String(100), nullable=True)
    botanical_source = Column(String(200), nullable=True)
    abs_status = Column(String(50), default="NOT_APPLICABLE")
    license_number = Column(String(100), nullable=True)
    verified = Column(Boolean, default=False)

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    confidence = Column(Float, default=0.0)
    consent_record = Column(Boolean, default=False, nullable=False)
    query_hash = Column(String(64), nullable=True, index=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="chat_history")

class OpportunityAnalysis(Base):
    """Persisted White Space Navigator result per passport."""
    __tablename__ = "opportunity_analyses"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False, index=True)
    ingredient_score = Column(Float, default=0.0)
    process_score = Column(Float, default=0.0)
    delivery_score = Column(Float, default=0.0)
    novelty_score = Column(Float, default=0.0)
    tk_score = Column(Float, default=0.0)
    evidence_score = Column(Float, default=0.0)
    market_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    status = Column(String(50), default="Moderate")
    recommendations = Column(JSON, default=list)
    snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLogEntry(Base):
    """Append-only, hash-chained audit log (DPDP accountability, B4).

    Each entry links to its predecessor via ``prev_hash``; ``entry_hash``
    covers the previous hash, timestamp, event type, actor hash and payload,
    so any tampering breaks verification. Stores hashes and metadata only —
    never raw personal data.
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(String(40), nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    actor_hash = Column(String(64), nullable=False)
    payload = Column(Text, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False, unique=True)


class LawSourceState(Base):
    """Law-Change Sentinel state: last content hash + staleness per source."""

    __tablename__ = "law_source_states"

    source_id = Column(String(64), primary_key=True)
    url = Column(String(500), nullable=False)
    content_hash = Column(String(64), nullable=True)
    last_checked_at = Column(String(40), nullable=True)
    changed_at = Column(String(40), nullable=True)
    last_status = Column(String(16), default="never", nullable=False)
    last_error = Column(String(300), default="", nullable=False)
    change_count = Column(Integer, default=0, nullable=False)
    stale = Column(Boolean, default=False, nullable=False)
    needs_reembed = Column(Boolean, default=False, nullable=False)

class WatchProfile(Base):
    """A2 - saved formulation profile monitored for new prior art."""

    __tablename__ = "watch_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=True)
    title = Column(String(200), nullable=False)
    ingredients = Column(JSON, default=list, nullable=False)
    indication = Column(String(200), default="", nullable=False)
    classical_ref = Column(String(300), default="", nullable=False)
    status = Column(String(16), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_checked_at = Column(String(40), nullable=True)


class WatchHit(Base):
    """A2 - one prior-art match found for a watch profile."""

    __tablename__ = "watch_hits"

    id = Column(String, primary_key=True, default=generate_uuid)
    profile_id = Column(String, ForeignKey("watch_profiles.id"), nullable=False, index=True)
    patent_no = Column(String(64), nullable=False)
    title = Column(String(400), default="", nullable=False)
    match_kind = Column(String(16), default="partial", nullable=False)
    overlap = Column(String(400), default="", nullable=False)
    advice = Column(String(600), default="", nullable=False)
    urgency = Column(String(8), default="LOW", nullable=False)
    source_url = Column(String(500), default="", nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())


class TrackedDeadline(Base):
    """A3 - renewal / filing deadline with a reminder ladder."""

    __tablename__ = "tracked_deadlines"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    reference = Column(String(120), default="", nullable=False)
    title = Column(String(200), default="", nullable=False)
    due_date = Column(String(20), nullable=False, index=True)
    reminder_days = Column(JSON, default=list, nullable=False)
    status = Column(String(16), default="pending", nullable=False)
    notes = Column(String(600), default="", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GeneratedDocumentDB(Base):
    """A4/A6 - generated dossier or prefilled form (DRAFT until human sign-off)."""

    __tablename__ = "generated_documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    passport_id = Column(String, ForeignKey("innovation_passports.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    kind = Column(String(24), nullable=False)
    form_code = Column(String(16), default="", nullable=False)
    doc_format = Column(String(8), default="json", nullable=False)
    status = Column(String(16), default="DRAFT", nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    citation_count = Column(Integer, default=0, nullable=False)
    missing_field_count = Column(Integer, default=0, nullable=False)
    summary = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
