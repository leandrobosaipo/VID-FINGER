"""Configuração de lifecycle policy para DigitalOcean Spaces."""
import boto3
from botocore.exceptions import ClientError
from app.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class SpacesLifecycleService:
    """Serviço para configurar lifecycle policy no Spaces."""
    
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
            config=boto3.session.Config(
                signature_version='s3v4',
                region_name=settings.DO_SPACES_REGION,
                s3={'addressing_style': 'path'}
            )
        )
        self.bucket = settings.DO_SPACES_BUCKET
    
    def setup_lifecycle_policy(self, expiration_days: int = 7):
        """
        Configura política de lifecycle para deletar arquivos após N dias.
        
        Args:
            expiration_days: Número de dias até expiração (padrão: 7)
        """
        if not self.s3_client:
            logger.warning("S3 client não disponível")
            return False
        
        prefix = settings.OUTPUT_PREFIX
        
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'vid-finger-auto-delete',
                    'Status': 'Enabled',
                    'Filter': {
                        'Prefix': f'{prefix}/'
                    },
                    'Expiration': {
                        'Days': expiration_days
                    }
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration=lifecycle_config
            )
            logger.info(f"Lifecycle policy configurada: arquivos em '{prefix}/' serão deletados após {expiration_days} dias")
            return True
        except ClientError as e:
            logger.error(f"Erro ao configurar lifecycle policy: {e}")
            return False
    
    def get_lifecycle_policy(self):
        """Obtém política de lifecycle atual."""
        if not self.s3_client:
            return None
        
        try:
            response = self.s3_client.get_bucket_lifecycle_configuration(Bucket=self.bucket)
            return response.get('Rules', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                logger.info("Nenhuma lifecycle policy configurada")
                return []
            logger.error(f"Erro ao obter lifecycle policy: {e}")
            return None


# Instância global
lifecycle_service = SpacesLifecycleService()

