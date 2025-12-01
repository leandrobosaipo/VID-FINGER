"""Serviço de orquestração de análise."""
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
import mimetypes
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.analysis import Analysis, AnalysisStatus
from app.models.file import File, FileType
from app.models.analysis_step import AnalysisStep, StepName, StepStatus
from app.services.upload_service import UploadService
from app.services.file_service import FileService
from app.services.storage_service import storage_service
from app.services.webhook_service import WebhookService
from app.utils.context import format_log_with_context
from app.config import settings

logger = logging.getLogger(__name__)


class AnalysisService:
    """Serviço para gerenciar análises."""
    
    @staticmethod
    async def create_analysis_from_upload(
        upload_id: str,
        webhook_url: Optional[str],
        db: AsyncSession
    ) -> uuid.UUID:
        """
        Cria análise a partir de upload completo.
        
        Returns:
            ID da análise criada
        """
        # Obter status do upload
        upload_status = UploadService.get_upload_status(upload_id)
        if not upload_status or not upload_status["is_complete"]:
            raise ValueError("Upload incompleto")
        
        # Gerar ID da análise (usado também para estruturar o caminho do arquivo)
        analysis_id = uuid.uuid4()
        
        # Finalizar upload e montar arquivo físico
        output_dir = FileService.generate_storage_path(str(analysis_id), FileType.original)
        file_path, checksum = UploadService.complete_upload(upload_id, output_dir)
        
        # Detectar MIME type e tamanho a partir dos metadados do upload
        mime_type = upload_status.get("mime_type")
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(upload_status["filename"])
        if not mime_type:
            mime_type = "video/mp4"
        file_size = upload_status.get("file_size") or FileService.get_file_size(file_path)
        
        # 1) Criar e persistir o registro do arquivo antes da análise
        original_file = File(
            id=uuid.uuid4(),
            analysis_id=None,  # será vinculado à análise após sua criação
            file_type=FileType.original,
            original_filename=upload_status["filename"],
            stored_filename=file_path.name,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            checksum=checksum
        )
        db.add(original_file)
        await db.commit()
        await db.refresh(original_file)
        logger.info(
            format_log_with_context(
                "ANALYSIS",
                f"Arquivo original persistido no banco: file_id={original_file.id}, path={original_file.file_path}, size={original_file.file_size}",
                analysis_id=str(analysis_id)
            )
        )
        
        # 2) Criar análise referenciando o arquivo já persistido
        analysis = Analysis(
            id=analysis_id,
            status=AnalysisStatus.pending,
            webhook_url=webhook_url,
            original_file_id=original_file.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        logger.info(
            format_log_with_context(
                "ANALYSIS",
                f"Análise criada e persistida no banco: analysis_id={analysis.id}, original_file_id={analysis.original_file_id}, status={analysis.status.value}",
                analysis_id=str(analysis.id)
            )
        )
        
        # 3) Criar etapas iniciais e vincular arquivo à análise
        steps = [
            AnalysisStep(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                step_name=StepName.upload,
                status=StepStatus.completed,
                progress=100,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            ),
            AnalysisStep(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                step_name=StepName.metadata_extraction,
                status=StepStatus.pending,
                progress=0
            ),
            AnalysisStep(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                step_name=StepName.prnu,
                status=StepStatus.pending,
                progress=0
            ),
            AnalysisStep(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                step_name=StepName.fft,
                status=StepStatus.pending,
                progress=0
            ),
            AnalysisStep(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                step_name=StepName.classification,
                status=StepStatus.pending,
                progress=0
            ),
            AnalysisStep(
                id=uuid.uuid4(),
                analysis_id=analysis_id,
                step_name=StepName.cleaning,
                status=StepStatus.pending,
                progress=0
            )
        ]
        for step in steps:
            db.add(step)
        
        # Atualizar vínculo do arquivo com a análise
        original_file.analysis_id = analysis.id
        db.add(original_file)
        
        await db.commit()
        
        # Upload para CDN se configurado
        if settings.UPLOAD_TO_CDN and storage_service.s3_client:
            try:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    key = storage_service.generate_key(
                        str(analysis_id),
                        "original",
                        original_file.stored_filename
                    )
                    cdn_url = storage_service.upload_file(
                        file_path_obj,
                        key,
                        content_type=original_file.mime_type,
                        analysis_id=str(analysis_id)
                    )
                    if cdn_url:
                        original_file.cdn_url = cdn_url
                        original_file.cdn_uploaded = True
                        await db.commit()
                        await db.refresh(original_file)
                        logger.info(
                            format_log_with_context(
                                "ANALYSIS",
                                f"Arquivo original enviado para CDN: url={cdn_url}",
                                analysis_id=str(analysis_id)
                            )
                        )
            except Exception as e:
                logger.error(
                    format_log_with_context(
                        "ANALYSIS",
                        f"Erro ao fazer upload para CDN: {str(e)}",
                        analysis_id=str(analysis_id)
                    ),
                    exc_info=True
                )
        
        # Enviar webhook de upload completo
        if webhook_url:
            try:
                await WebhookService.send_webhook(
                    webhook_url=webhook_url,
                    event="analysis.upload.completed",
                    analysis_id=str(analysis_id),
                    data={
                        "status": "pending",
                        "file_size": original_file.file_size,
                        "cdn_url": original_file.cdn_url if original_file.cdn_uploaded else None
                    }
                )
            except Exception as e:
                logger.error(f"Erro ao enviar webhook: {e}")
        
        # Retornar analysis_id - processamento será iniciado via BackgroundTasks no endpoint
        # Isso garante que a sessão do banco está commitada antes de iniciar processamento
        return analysis_id
    
    @staticmethod
    async def start_processing_background(analysis_id: str):
        """
        Inicia processamento em background.
        
        Esta função pode ser chamada por BackgroundTasks do FastAPI ou por Celery.
        Cria sua própria sessão de banco de dados.
        """
        from app.services.analysis_processor import AnalysisProcessor
        from app.database import AsyncSessionLocal
        
        logger.info(f"[{analysis_id}] ========================================")
        logger.info(f"[{analysis_id}] INICIANDO PROCESSAMENTO EM BACKGROUND")
        logger.info(f"[{analysis_id}] ========================================")
        
        # Tentar Celery primeiro (apenas se worker estiver rodando)
        use_celery = False
        try:
            from app.tasks.analysis_tasks import process_analysis
            from celery import current_app
            
            # Verificar se há workers ativos
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                # Há workers ativos, usar Celery
                process_analysis.delay(str(analysis_id))
                logger.info(f"✅ Task Celery iniciada para análise {analysis_id}")
                return
            else:
                logger.info(f"⚠️  Celery disponível mas sem workers ativos, usando processamento direto")
        except ImportError:
            logger.info(f"⚠️  Celery não instalado, usando processamento direto")
        except Exception as e:
            logger.warning(f"⚠️  Celery não disponível ({e}), usando processamento direto")
        
        # Fallback: processar diretamente com nova sessão
        async with AsyncSessionLocal() as processing_db:
            try:
                await AnalysisProcessor.process_analysis(str(analysis_id), processing_db)
                logger.info(f"✅ Processamento concluído para análise {analysis_id}")
            except Exception as proc_error:
                logger.error(f"❌ Erro no processamento de {analysis_id}: {proc_error}", exc_info=True)
                # Tentar salvar erro no banco
                try:
                    result = await processing_db.execute(
                        select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
                    )
                    analysis = result.scalar_one_or_none()
                    if analysis:
                        analysis.status = AnalysisStatus.failed
                        analysis.error_message = str(proc_error)
                        await processing_db.commit()
                except Exception as db_error:
                    logger.error(f"Erro ao salvar falha no banco: {db_error}")
        
        return analysis_id
    
    @staticmethod
    async def create_analysis_from_file(
        file_content: bytes,
        filename: str,
        webhook_url: Optional[str],
        db: AsyncSession,
        mime_type: Optional[str] = None
    ) -> uuid.UUID:
        """
        Cria análise diretamente a partir de conteúdo de arquivo.
        
        Processa upload internamente e inicia análise automaticamente.
        
        Args:
            file_content: Conteúdo do arquivo em bytes (já lido)
            filename: Nome do arquivo
            webhook_url: URL do webhook (opcional)
            db: Sessão do banco de dados
            mime_type: Tipo MIME do arquivo (opcional, será detectado se não fornecido)
        """
        import mimetypes
        from pathlib import Path
        
        file_size = len(file_content)
        
        # Validar tamanho
        if file_size == 0:
            logger.warning(
                format_log_with_context(
                    "ANALYSIS",
                    f"Arquivo recebido com tamanho zero: {filename}"
                )
            )
            raise ValueError("Tamanho do arquivo deve ser maior que zero")
        
        # Detectar MIME type se não fornecido
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type or not mime_type.startswith('video/'):
                ext = Path(filename).suffix.lower()
                mime_map = {
                    '.mp4': 'video/mp4',
                    '.mov': 'video/quicktime',
                    '.avi': 'video/x-msvideo',
                    '.mkv': 'video/x-matroska',
                    '.webm': 'video/webm'
                }
                mime_type = mime_map.get(ext, 'video/mp4')
        
        logger.info(
            format_log_with_context(
                "ANALYSIS",
                f"Criando análise a partir de arquivo: filename={filename}, size={file_size}, mime_type={mime_type}"
            )
        )
        
        # Fazer upload direto
        upload_id = UploadService.upload_file_direct(
            file_content=file_content,
            filename=filename,
            mime_type=mime_type
        )
        
        # Criar análise a partir do upload
        analysis_id = await AnalysisService.create_analysis_from_upload(
            upload_id=upload_id,
            webhook_url=webhook_url,
            db=db
        )
        
        return analysis_id
    
    @staticmethod
    async def get_analysis(
        analysis_id: str,
        db: AsyncSession
    ) -> Optional[Analysis]:
        """Obtém análise por ID."""
        result = await db.execute(
            select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
        )
        return result.scalar_one_or_none()
