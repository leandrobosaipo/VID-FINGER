"""Tasks Celery para análise."""
from app.tasks.celery_app import celery_app
from app.services.analysis_service import AnalysisService
from app.services.webhook_service import WebhookService
from app.core.ffprobe_reader import extract_metadata, estimate_gop_size, estimate_gop_regularity
from app.core.fingerprint_logic import calculate_fingerprint
from app.core.video_classifier import classify_video
from app.core.prnu_detector import detect_prnu
from app.core.fft_temporal import detect_diffusion_signature, analyze_temporal_jitter
from app.core.metadata_integrity import analyze_metadata_integrity
from app.core.timeline_analyzer import analyze_timeline
from app.core.cleaner import generate_clean_video
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
import uuid
from datetime import datetime
from app.models.analysis import AnalysisStatus
from app.models.analysis_step import StepName, StepStatus


@celery_app.task(bind=True, name="process_analysis")
def process_analysis(self, analysis_id: str):
    """
    Task principal que orquestra todas as etapas da análise.
    """
    import asyncio
    from app.services.analysis_processor import AnalysisProcessor
    from app.database import AsyncSessionLocal
    
    # Executar processamento assíncrono
    async def run():
        async with AsyncSessionLocal() as db:
            await AnalysisProcessor.process_analysis(analysis_id, db)
    
    # Executar em novo loop se necessário
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se já há loop rodando, criar task
            asyncio.create_task(run())
        else:
            loop.run_until_complete(run())
    except RuntimeError:
        # Criar novo loop
        asyncio.run(run())


@celery_app.task(name="extract_metadata_task")
def extract_metadata_task(analysis_id: str):
    """Extrai metadados do vídeo."""
    # TODO: Implementar
    pass


@celery_app.task(name="analyze_prnu_task")
def analyze_prnu_task(analysis_id: str):
    """Analisa PRNU."""
    # TODO: Implementar
    pass


@celery_app.task(name="analyze_fft_task")
def analyze_fft_task(analysis_id: str):
    """Analisa FFT temporal."""
    # TODO: Implementar
    pass


@celery_app.task(name="classify_video_task")
def classify_video_task(analysis_id: str):
    """Classifica vídeo."""
    # TODO: Implementar
    pass


@celery_app.task(name="generate_report_task")
def generate_report_task(analysis_id: str):
    """Gera relatório."""
    # TODO: Implementar
    pass


@celery_app.task(name="generate_clean_video_task")
def generate_clean_video_task(analysis_id: str):
    """Gera vídeo limpo."""
    # TODO: Implementar
    pass


@celery_app.task(name="upload_to_cdn_task")
def upload_to_cdn_task(analysis_id: str):
    """Upload para CDN."""
    # TODO: Implementar
    pass

