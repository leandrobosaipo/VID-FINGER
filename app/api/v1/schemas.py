"""Schemas Pydantic para API v1."""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class AnalysisStatus(str, Enum):
    """Status da análise."""
    pending = "pending"
    uploading = "uploading"
    analyzing = "analyzing"
    cleaning = "cleaning"
    completed = "completed"
    failed = "failed"


class StepStatus(str, Enum):
    """Status da etapa."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class FileType(str, Enum):
    """Tipo de arquivo."""
    original = "original"
    report = "report"
    clean_video = "clean_video"


class MimeType(str, Enum):
    """Tipos MIME aceitos para upload."""
    mp4 = "video/mp4"
    quicktime = "video/quicktime"
    avi = "video/x-msvideo"
    mkv = "video/x-matroska"
    webm = "video/webm"


# Upload Schemas
class UploadInitRequest(BaseModel):
    """Request para iniciar upload."""
    filename: str = Field(..., description="Nome do arquivo")
    file_size: int = Field(..., description="Tamanho em bytes", gt=0)
    mime_type: str = Field(..., description="Tipo MIME")
    webhook_url: Optional[str] = Field(None, description="URL do webhook n8n")


class UploadInitResponse(BaseModel):
    """Response de inicialização de upload."""
    upload_id: str
    chunk_size: int
    total_chunks: int
    upload_url: str


class ChunkUploadResponse(BaseModel):
    """Response de upload de chunk."""
    upload_id: str
    chunks_received: int
    total_chunks: int
    progress: float


class UploadCompleteResponse(BaseModel):
    """Response de conclusão de upload."""
    analysis_id: str
    status: str
    message: str


class AnalysisStartResponse(BaseModel):
    """Response de início de análise simplificada."""
    analysis_id: str
    status: str  # Sempre "processing"
    status_url: str
    message: str


# Analysis Schemas
class StepInfo(BaseModel):
    """Informações de uma etapa."""
    name: str
    status: StepStatus
    progress: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AnalysisResponse(BaseModel):
    """Response de status da análise."""
    id: str
    status: AnalysisStatus
    progress: int
    current_step: Optional[str] = None
    steps: List[StepInfo] = []
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    classification: Optional[str] = None
    confidence: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    clean_video_url: Optional[str] = None
    report_url: Optional[str] = None
    original_video_url: Optional[str] = None


class AnalysisListResponse(BaseModel):
    """Response de lista de análises."""
    items: List[AnalysisResponse]
    total: int
    page: int
    page_size: int


# File Schemas
class FileResponse(BaseModel):
    """Response de arquivo."""
    id: str
    file_type: FileType
    original_filename: str
    file_size: int
    mime_type: str
    cdn_url: Optional[str] = None
    cdn_uploaded: bool
    created_at: datetime

