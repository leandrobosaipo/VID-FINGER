"""Modelo File."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class FileType(str, enum.Enum):
    """Tipo de arquivo."""
    original = "original"
    report = "report"
    clean_video = "clean_video"


class File(Base):
    """Modelo de arquivo."""
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Pode ser nulo no momento da criação do arquivo.
    # Em alguns fluxos (como upload simplificado), o arquivo é persistido antes da análise existir.
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=True)
    file_type = Column(SQLEnum(FileType), nullable=False)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String, nullable=False)
    cdn_url = Column(String, nullable=True)
    cdn_uploaded = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    checksum = Column(String, nullable=False)  # SHA256
    
    # Relationships
    analysis = relationship("Analysis", foreign_keys=[analysis_id])
    analysis_as_original = relationship("Analysis", foreign_keys="Analysis.original_file_id", back_populates="original_file")
    analysis_as_report = relationship("Analysis", foreign_keys="Analysis.report_file_id", back_populates="report_file")
    analysis_as_clean = relationship("Analysis", foreign_keys="Analysis.clean_video_id", back_populates="clean_video_file")
