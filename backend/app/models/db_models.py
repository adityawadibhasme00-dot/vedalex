from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

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
