"""Serviço de armazenamento em CDN (DigitalOcean Spaces)."""
import boto3
from botocore.config import Config
from pathlib import Path
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Serviço para upload em DigitalOcean Spaces."""
    
    def __init__(self):
        """Inicializa cliente S3 para DigitalOcean Spaces."""
        if not all([
            settings.DO_SPACES_ENDPOINT,
            settings.DO_SPACES_KEY,
            settings.DO_SPACES_SECRET,
            settings.DO_SPACES_BUCKET
        ]):
            self.s3_client = None
            logger.warning("DigitalOcean Spaces não configurado")
            return
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.DO_SPACES_ENDPOINT,
            aws_access_key_id=settings.DO_SPACES_KEY,
            aws_secret_access_key=settings.DO_SPACES_SECRET,
            config=Config(
                signature_version='s3v4',
                region_name=settings.DO_SPACES_REGION,
                s3={'addressing_style': 'path'}
            )
        )
        self.bucket = settings.DO_SPACES_BUCKET
    
    def upload_file(
        self,
        file_path: Path,
        key: str,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload arquivo para Spaces.
        
        Args:
            file_path: Caminho do arquivo local
            key: Chave S3 (caminho no bucket)
            content_type: Tipo de conteúdo (opcional)
            
        Returns:
            URL pública do arquivo ou None se falhar
        """
        if not self.s3_client:
            logger.warning("S3 client não disponível")
            return None
        
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Upload com multipart para arquivos grandes
            self.s3_client.upload_file(
                str(file_path),
                self.bucket,
                key,
                ExtraArgs=extra_args
            )
            
            # Gerar URL pública
            url = f"{settings.DO_SPACES_ENDPOINT}/{self.bucket}/{key}"
            logger.info(f"Arquivo enviado para CDN: {key}")
            return url
        
        except Exception as e:
            logger.error(f"Erro ao fazer upload para CDN: {e}")
            return None
    
    def generate_key(self, analysis_id: str, file_type: str, filename: str) -> str:
        """Gera chave S3 para arquivo."""
        prefix = settings.OUTPUT_PREFIX
        return f"{prefix}/analyses/{analysis_id}/{file_type}/{filename}"


# Instância global
storage_service = StorageService()

