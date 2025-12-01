"""Serviço de armazenamento em CDN (DigitalOcean Spaces)."""
import boto3
from botocore.config import Config
from pathlib import Path
from typing import Optional
from app.config import settings
import logging
from app.utils.context import format_log_with_context

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
            logger.warning(
                format_log_with_context(
                    "STORAGE",
                    "DigitalOcean Spaces não configurado: faltando credenciais"
                )
            )
            return
        
        logger.info(
            format_log_with_context(
                "STORAGE",
                f"Inicializando cliente S3: endpoint={settings.DO_SPACES_ENDPOINT}, bucket={settings.DO_SPACES_BUCKET}, region={settings.DO_SPACES_REGION}"
            )
        )
        
        try:
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
            
            logger.info(
                format_log_with_context(
                    "STORAGE",
                    f"Cliente S3 inicializado com sucesso: bucket={self.bucket}"
                )
            )
        except Exception as e:
            self.s3_client = None
            logger.error(
                format_log_with_context(
                    "STORAGE",
                    f"Erro ao inicializar cliente S3: {str(e)}"
                ),
                exc_info=True
            )
    
    def upload_file(
        self,
        file_path: Path,
        key: str,
        content_type: Optional[str] = None,
        analysis_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload arquivo para Spaces.
        
        Args:
            file_path: Caminho do arquivo local
            key: Chave S3 (caminho no bucket)
            content_type: Tipo de conteúdo (opcional)
            analysis_id: ID da análise (para logs)
            
        Returns:
            URL pública do arquivo ou None se falhar
        """
        if not self.s3_client:
            logger.warning(
                format_log_with_context(
                    "STORAGE",
                    "S3 client não disponível - upload cancelado",
                    analysis_id=analysis_id
                )
            )
            return None
        
        # Obter tamanho do arquivo
        file_size = file_path.stat().st_size if file_path.exists() else 0
        
        logger.info(
            format_log_with_context(
                "STORAGE",
                f"Iniciando upload para CDN: file_path={file_path}, key={key}, size={file_size} bytes, content_type={content_type}",
                analysis_id=analysis_id
            )
        )
        
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Callback para progresso (se arquivo for grande)
            def upload_progress(bytes_transferred):
                if file_size > 0:
                    progress = (bytes_transferred / file_size) * 100
                    logger.debug(
                        format_log_with_context(
                            "STORAGE",
                            f"Upload em progresso: {progress:.1f}% ({bytes_transferred}/{file_size} bytes)",
                            analysis_id=analysis_id
                        )
                    )
            
            # Upload com multipart para arquivos grandes
            logger.debug(
                format_log_with_context(
                    "STORAGE",
                    f"Executando upload_file: bucket={self.bucket}, key={key}",
                    analysis_id=analysis_id
                )
            )
            
            self.s3_client.upload_file(
                str(file_path),
                self.bucket,
                key,
                ExtraArgs=extra_args,
                Callback=upload_progress if file_size > 5 * 1024 * 1024 else None  # Só callback para arquivos > 5MB
            )
            
            # Gerar URL pública
            url = f"{settings.DO_SPACES_ENDPOINT}/{self.bucket}/{key}"
            
            logger.info(
                format_log_with_context(
                    "STORAGE",
                    f"Upload concluído com sucesso: key={key}, url={url}",
                    analysis_id=analysis_id
                )
            )
            
            return url
        
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(
                format_log_with_context(
                    "STORAGE",
                    f"Erro no upload para CDN: {error_type} - {error_msg} | key={key}",
                    analysis_id=analysis_id
                ),
                exc_info=True
            )
            return None
    
    def generate_key(self, analysis_id: str, file_type: str, filename: str) -> str:
        """Gera chave S3 para arquivo."""
        prefix = settings.OUTPUT_PREFIX
        return f"{prefix}/analyses/{analysis_id}/{file_type}/{filename}"


# Instância global
storage_service = StorageService()

