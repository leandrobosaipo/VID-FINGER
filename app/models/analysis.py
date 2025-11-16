"""Modelo Analysis."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AnalysisStatus(str, enum.Enum):
    """Status da análise."""
    pending = "pending"
    uploading = "uploading"
    analyzing = "analyzing"
    cleaning = "cleaning"
    completed = "completed"
    failed = "failed"


class Analysis(Base):
    """Modelo de análise."""
    __tablename__ = "analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    webhook_url = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    
    # Foreign keys
    original_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    report_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    clean_video_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    
    # Dados da análise
    video_metadata = Column(JSON, nullable=True)  # Renomeado de 'metadata' para evitar conflito com SQLAlchemy
    classification = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Relationships
    original_file = relationship("File", foreign_keys=[original_file_id], back_populates="analysis_as_original")
    report_file = relationship("File", foreign_keys=[report_file_id], back_populates="analysis_as_report")
    clean_video_file = relationship("File", foreign_keys=[clean_video_id], back_populates="analysis_as_clean")
    steps = relationship("AnalysisStep", back_populates="analysis", cascade="all, delete-orphan")

