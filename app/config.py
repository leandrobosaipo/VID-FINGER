"""Configurações da aplicação."""
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

# Tentar importar pydantic-settings com fallback robusto
try:
    from pydantic_settings import BaseSettings
except ImportError as e:
    # Se falhar, tentar importar diretamente do pydantic (versões antigas)
    try:
        from pydantic import BaseSettings
    except ImportError:
        # Último recurso: criar uma classe simples que funciona
        from pydantic import BaseModel
        
        class BaseSettings(BaseModel):
            """Fallback BaseSettings usando BaseModel."""
            class Config:
                env_file = ".env"
                case_sensitive = True


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # App
    APP_NAME: str = "VID-FINGER API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vidfinger"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/vidfinger"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    STORAGE_PATH: str = "/app/storage"
    MAX_FILE_SIZE: int = 10737418240  # 10GB
    CHUNK_SIZE: int = 5242880  # 5MB
    
    # DigitalOcean Spaces
    DO_SPACES_ENDPOINT: Optional[str] = None
    DO_SPACES_KEY: Optional[str] = None
    DO_SPACES_SECRET: Optional[str] = None
    DO_SPACES_BUCKET: Optional[str] = None
    DO_SPACES_REGION: str = "nyc3"
    OUTPUT_PREFIX: str = "vid-finger"
    UPLOAD_TO_CDN: bool = False
    
    # Webhooks
    WEBHOOK_TIMEOUT: int = 10
    WEBHOOK_RETRY_ATTEMPTS: int = 3
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Security (opcional)
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    
    # FFmpeg
    FFMPEG_PATH: str = "/usr/bin/ffmpeg"
    FFPROBE_PATH: str = "/usr/bin/ffprobe"
    
    # API Base URL (para geração de URLs completas)
    API_BASE_URL: Optional[str] = None  # Se None, será inferido do Request
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        """Inicializar Settings e validar DATABASE_URL."""
        super().__init__(**kwargs)
        self._validate_database_url()
    
    def _validate_database_url(self):
        """Valida formato de DATABASE_URL e emite warning se necessário."""
        if not self.DATABASE_URL:
            return
        
        # Verificar se está usando postgresql:// sem +asyncpg
        if self.DATABASE_URL.startswith("postgresql://") and not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            logger.warning(
                "⚠️  DATABASE_URL está usando driver síncrono (postgresql://). "
                "Para uso com async_engine, altere para postgresql+asyncpg://"
            )


settings = Settings()

