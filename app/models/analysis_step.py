"""Modelo AnalysisStep."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class StepStatus(str, enum.Enum):
    """Status da etapa."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class StepName(str, enum.Enum):
    """Nome da etapa."""
    upload = "upload"
    metadata_extraction = "metadata_extraction"
    prnu = "prnu"
    fft = "fft"
    classification = "classification"
    cleaning = "cleaning"
    cdn_upload = "cdn_upload"


class AnalysisStep(Base):
    """Modelo de etapa de análise."""
    __tablename__ = "analysis_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)
    step_name = Column(SQLEnum(StepName), nullable=False)
    status = Column(SQLEnum(StepStatus), default=StepStatus.pending, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    error_message = Column(Text, nullable=True)
    step_metadata = Column(JSON, nullable=True)  # Renomeado de 'metadata' para evitar conflito com SQLAlchemy
    
    # Relationship
    analysis = relationship("Analysis", back_populates="steps")

