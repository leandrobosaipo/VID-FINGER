"""Endpoints de upload."""
import mimetypes
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status, Query, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.upload_service import UploadService
from app.services.analysis_service import AnalysisService
from app.utils.formatters import format_success_response, format_error_response
from app.utils.context import get_correlation_id, format_log_with_context
from app.api.v1.schemas import (
    UploadInitResponse,
    ChunkUploadResponse,
    UploadCompleteResponse,
    AnalysisStartResponse,
    MimeType
)
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/init",
    response_model=UploadInitResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["upload"],
    summary="Iniciar upload chunked",
    description="""
    Inicia um upload chunked de vídeo.
    
    **Como usar:**
    1. Selecione o arquivo de vídeo no campo "file"
    2. (Opcional) Adicione webhook_url para receber notificações
    3. O sistema extrai automaticamente: nome, tamanho e tipo do arquivo
    
    O sistema divide o arquivo em chunks de 5MB e permite upload progressivo.
    Retorna um `upload_id` que deve ser usado nos próximos endpoints.
    
    **Limites:**
    - Tamanho máximo: 10GB
    - Tipos aceitos: MP4, MOV, AVI, MKV, WebM
    
    **Resultado esperado:**
    - Retorna `upload_id` que deve ser usado em `/upload/chunk/{upload_id}`
    - Retorna `chunk_size` (geralmente 5242880 bytes = 5MB)
    - Retorna `total_chunks` calculado automaticamente
    """
)
async def init_upload(
    file: UploadFile = File(
        ...,
        description="Arquivo de vídeo a ser analisado. Tipos aceitos: MP4, MOV, AVI, MKV, WebM. Tamanho máximo: 10GB. O sistema extrai automaticamente nome, tamanho e tipo do arquivo.",
        example="video-teste.mp4"
    ),
    webhook_url: Optional[str] = Form(
        None,
        description="URL do webhook para receber notificações de progresso (opcional). Deve ser uma URL HTTP/HTTPS válida. Você receberá eventos quando: upload completar, etapas iniciarem/completarem, análise finalizar ou falhar. Exemplos: https://seu-webhook.com/callback ou https://webhook.site/unique-id",
        example="https://webhook.site/abc123-def456-ghi789"
    )
):
    try:
        # Extrair informações do arquivo automaticamente
        filename = file.filename or "video.mp4"
        file_size = 0
        
        # Ler arquivo para obter tamanho real
        content = await file.read()
        file_size = len(content)
        
        # Detectar MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type or not mime_type.startswith('video/'):
            # Tentar detectar pela extensão
            ext = Path(filename).suffix.lower()
            mime_map = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.mkv': 'video/x-matroska',
                '.webm': 'video/webm'
            }
            mime_type = mime_map.get(ext, 'video/mp4')
        
        # Validar tipo de arquivo
        from app.utils.validators import validate_file_type
        is_valid, error = validate_file_type(filename, mime_type)
        if not is_valid:
            raise ValueError(error)
        
        # Validar tamanho
        from app.utils.validators import validate_file_size
        is_valid, error = validate_file_size(file_size, settings.MAX_FILE_SIZE)
        if not is_valid:
            raise ValueError(error)
        
        # Inicializar upload
        upload_id, chunk_size, total_chunks = UploadService.init_upload(
            filename=filename,
            file_size=file_size,
            mime_type=mime_type
        )
        
        # Salvar arquivo completo de uma vez
        # Dividir em chunks se necessário para arquivos grandes
        if file_size <= chunk_size:
            # Arquivo cabe em um chunk, salvar diretamente
            UploadService.save_chunk(upload_id, 0, content)
        else:
            # Arquivo grande - salvar em múltiplos chunks
            chunks_saved = 0
            for i in range(0, file_size, chunk_size):
                chunk_data = content[i:i + chunk_size]
                UploadService.save_chunk(upload_id, chunks_saved, chunk_data)
                chunks_saved += 1
        
        response_data = {
            "upload_id": upload_id,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "upload_url": f"/api/v1/upload/chunk/{upload_id}"
        }
        
        return UploadInitResponse(**response_data)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error_response(
                message=str(e),
                error_code="VALIDATION_ERROR"
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao inicializar upload",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.post(
    "/chunk/{upload_id}",
    response_model=ChunkUploadResponse,
    tags=["upload"],
    summary="Upload de chunk",
    description="""
    Faz upload de um chunk individual do vídeo.
    
    **Importante:**
    - Chunks podem ser enviados em qualquer ordem
    - Cada chunk deve ter no máximo 5MB
    - O último chunk pode ser menor que 5MB
    - Use o `progress` retornado para acompanhar o progresso
    """
)
async def upload_chunk(
    upload_id: str,
    chunk_number: int = Form(..., description="Número do chunk (0-indexed)"),
    chunk: UploadFile = File(..., description="Dados do chunk (máx 5MB)")
):
    try:
        # Ler dados do chunk
        chunk_data = await chunk.read()
        
        # Salvar chunk
        chunks_received, progress = UploadService.save_chunk(
            upload_id=upload_id,
            chunk_number=chunk_number,
            chunk_data=chunk_data
        )
        
        # Obter status completo
        status_info = UploadService.get_upload_status(upload_id)
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload não encontrado"
            )
        
        return ChunkUploadResponse(
            upload_id=upload_id,
            chunks_received=chunks_received,
            total_chunks=status_info["total_chunks"],
            progress=progress
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error_response(
                message=str(e),
                error_code="VALIDATION_ERROR"
            )
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message=str(e),
                error_code="UPLOAD_ERROR"
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao processar chunk",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.post(
    "/complete/{upload_id}",
    response_model=UploadCompleteResponse,
    tags=["upload"],
    summary="Finalizar upload",
    description="""
    Finaliza o upload e inicia a análise forense.
    
    **O que acontece:**
    1. Monta o arquivo final a partir dos chunks enviados
    2. Salva o arquivo em `storage/original/{analysis_id}/`
    3. Se `UPLOAD_TO_CDN=True` no .env, faz upload automático para DigitalOcean Spaces
    4. Cria registro de análise no banco de dados com status `pending`
    5. Se `webhook_url` fornecido, envia webhook de confirmação
    
    **Webhooks enviados (se webhook_url fornecido):**
    - `analysis.upload.completed` - Quando upload é finalizado (enviado imediatamente)
    - `analysis.step.started` - Quando cada etapa de análise inicia (futuro)
    - `analysis.step.completed` - Quando cada etapa completa (futuro)
    - `analysis.completed` - Quando análise completa (futuro)
    - `analysis.failed` - Se análise falhar (futuro)
    
    **Resultado esperado:**
    - Retorna `analysis_id` que pode ser usado para consultar status em `/analysis/{analysis_id}`
    - Status inicial será `pending` até que o processamento comece
    """
)
async def complete_upload(
    upload_id: str,
    webhook_url: Optional[str] = Form(
        None,
        description="URL do webhook para receber notificações de progresso (opcional). Deve ser uma URL HTTP/HTTPS válida. Você receberá eventos quando: upload completar, etapas iniciarem/completarem, análise finalizar ou falhar. Exemplos: https://seu-webhook.com/callback ou https://webhook.site/unique-id",
        example="https://webhook.site/abc123-def456-ghi789"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Finalizar upload e criar análise
        analysis_id = await AnalysisService.create_analysis_from_upload(
            upload_id=upload_id,
            webhook_url=webhook_url,
            db=db
        )
        
        # Iniciar processamento em background
        # Usar BackgroundTasks (preferencial) ou asyncio.create_task como fallback
        import logging
        import asyncio
        logger = logging.getLogger(__name__)
        logger.info(f"[UPLOAD] Iniciando processamento para análise {analysis_id}")
        
        # Tentar usar BackgroundTasks primeiro (mais confiável no FastAPI)
        try:
            background_tasks.add_task(
                AnalysisService.start_processing_background,
                str(analysis_id)
            )
            logger.info(f"[UPLOAD] Task adicionada ao BackgroundTasks para análise {analysis_id}")
        except Exception as bg_error:
            logger.warning(f"[UPLOAD] BackgroundTasks falhou ({bg_error}), usando asyncio.create_task")
            # Fallback: usar asyncio.create_task diretamente
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    AnalysisService.start_processing_background(str(analysis_id))
                )
                logger.info(f"[UPLOAD] Task criada via asyncio para análise {analysis_id}")
            except Exception as task_error:
                logger.error(f"[UPLOAD] Erro ao criar task: {task_error}", exc_info=True)
        
        return UploadCompleteResponse(
            analysis_id=str(analysis_id),
            status="pending",
            message="Upload concluído. Análise iniciada."
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error_response(
                message=str(e),
                error_code="VALIDATION_ERROR"
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao finalizar upload",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.post(
    "/analyze",
    response_model=AnalysisStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["upload"],
    summary="Análise simplificada de vídeo",
    description="""
    Endpoint único e simplificado para análise de vídeo.
    
    **Como usar:**
    1. Selecione o arquivo de vídeo no campo "file"
    2. (Opcional) Adicione webhook_url para receber notificações
    3. Execute
    
    **O que acontece:**
    - Upload do arquivo é processado automaticamente (chunks internos transparentes)
    - Análise completa é iniciada automaticamente em background
    - Retorna imediatamente com `analysis_id` para consulta
    
    **Próximos passos:**
    - Use o `status_url` retornado para consultar progresso
    - Quando análise completar, links para vídeo limpo e relatório estarão disponíveis no status
    
    **Limites:**
    - Tamanho máximo: 10GB
    - Tipos aceitos: MP4, MOV, AVI, MKV, WebM
    """
)
async def analyze_video(
    file: UploadFile = File(
        ...,
        description="Arquivo de vídeo a ser analisado. Tipos aceitos: MP4, MOV, AVI, MKV, WebM. Tamanho máximo: 10GB. O sistema processa upload e análise automaticamente.",
        example="video-teste.mp4"
    ),
    webhook_url: Optional[str] = Form(
        None,
        description="URL do webhook para receber notificações de progresso (opcional). Deve ser uma URL HTTP/HTTPS válida. Você receberá eventos quando: upload completar, etapas iniciarem/completarem, análise finalizar ou falhar.",
        example="https://webhook.site/abc123-def456-ghi789"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint simplificado para análise de vídeo.
    
    Recebe arquivo, processa upload e inicia análise automaticamente.
    """
    correlation_id = get_correlation_id()
    analysis_id_str = None
    
    try:
        # Log: Recebimento do arquivo
        filename = file.filename or "unknown"
        logger.info(
            format_log_with_context(
                "UPLOAD",
                f"Recebido arquivo: {filename} | MIME type: {file.content_type}",
            )
        )
        
        # Ler arquivo para obter tamanho
        content = await file.read()
        file_size = len(content)
        
        # Validar tamanho zero antes de continuar
        if file_size == 0:
            logger.warning(
                format_log_with_context(
                    "UPLOAD",
                    f"Arquivo recebido com tamanho zero: {filename}",
                )
            )
            raise ValueError("Tamanho do arquivo deve ser maior que zero")
        
        logger.info(
            format_log_with_context(
                "UPLOAD",
                f"Arquivo lido: {filename} ({file_size} bytes) | MIME: {file.content_type}",
            )
        )
        
        # Validar tipo de arquivo
        from app.utils.validators import validate_file_type
        is_valid, error = validate_file_type(filename, file.content_type or "")
        if not is_valid:
            logger.warning(
                format_log_with_context(
                    "UPLOAD",
                    f"Validação de tipo falhou: {error}",
                )
            )
            raise ValueError(error)
        
        logger.debug(
            format_log_with_context(
                "UPLOAD",
                f"Validação de tipo OK: {filename} ({file.content_type})",
            )
        )
        
        # Validar tamanho
        from app.utils.validators import validate_file_size
        is_valid, error = validate_file_size(file_size, settings.MAX_FILE_SIZE)
        if not is_valid:
            logger.warning(
                format_log_with_context(
                    "UPLOAD",
                    f"Validação de tamanho falhou: {error}",
                )
            )
            raise ValueError(error)
        
        logger.debug(
            format_log_with_context(
                "UPLOAD",
                f"Validação de tamanho OK: {file_size} bytes (máx: {settings.MAX_FILE_SIZE})",
            )
        )
        
        # Criar análise diretamente do arquivo
        logger.info(
            format_log_with_context(
                "UPLOAD",
                f"Iniciando criação de análise a partir de arquivo: {filename}",
                **({"webhook_url": "fornecido"} if webhook_url else {})
            )
        )
        
        analysis_id = await AnalysisService.create_analysis_from_file(
            file_content=content,
            filename=filename,
            webhook_url=webhook_url,
            db=db,
            mime_type=file.content_type
        )
        
        analysis_id_str = str(analysis_id)
        
        logger.info(
            format_log_with_context(
                "UPLOAD",
                f"Análise criada com sucesso: analysis_id={analysis_id_str}",
                analysis_id=analysis_id_str
            )
        )
        
        # Iniciar processamento em background
        import asyncio
        logger.info(
            format_log_with_context(
                "UPLOAD",
                f"Iniciando processamento em background para análise {analysis_id_str}",
                analysis_id=analysis_id_str
            )
        )
        
        # Tentar usar BackgroundTasks primeiro (mais confiável no FastAPI)
        try:
            background_tasks.add_task(
                AnalysisService.start_processing_background,
                analysis_id_str
            )
            logger.info(
                format_log_with_context(
                    "UPLOAD",
                    f"Task adicionada ao BackgroundTasks para análise {analysis_id_str}",
                    analysis_id=analysis_id_str
                )
            )
        except Exception as bg_error:
            logger.warning(
                format_log_with_context(
                    "UPLOAD",
                    f"BackgroundTasks falhou ({bg_error}), usando asyncio.create_task",
                    analysis_id=analysis_id_str
                )
            )
            # Fallback: usar asyncio.create_task diretamente
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    AnalysisService.start_processing_background(analysis_id_str)
                )
                logger.info(
                    format_log_with_context(
                        "UPLOAD",
                        f"Task criada via asyncio para análise {analysis_id_str}",
                        analysis_id=analysis_id_str
                    )
                )
            except Exception as task_error:
                logger.error(
                    format_log_with_context(
                        "UPLOAD",
                        f"Erro ao criar task: {task_error}",
                        analysis_id=analysis_id_str
                    ),
                    exc_info=True
                )
        
        # Gerar URL base (usar settings por padrão)
        base_url = settings.API_BASE_URL or "http://localhost:8000"
        status_url = f"{base_url}/api/v1/analysis/{analysis_id_str}"
        
        logger.info(
            format_log_with_context(
                "UPLOAD",
                f"Resposta preparada: analysis_id={analysis_id_str}, status_url={status_url}",
                analysis_id=analysis_id_str
            )
        )
        
        return AnalysisStartResponse(
            analysis_id=analysis_id_str,
            status="processing",
            status_url=status_url,
            message="Arquivo recebido e análise iniciada. Use status_url para acompanhar o progresso."
        )
    
    except ValueError as e:
        logger.warning(
            format_log_with_context(
                "UPLOAD",
                f"Erro de validação: {str(e)}",
                analysis_id=analysis_id_str
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=format_error_response(
                message=str(e),
                error_code="VALIDATION_ERROR"
            )
        )
    except Exception as e:
        logger.error(
            format_log_with_context(
                "UPLOAD",
                f"Erro ao processar arquivo: {type(e).__name__}: {str(e)}",
                analysis_id=analysis_id_str
            ),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao processar arquivo",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.get(
    "/status/{upload_id}",
    tags=["upload"],
    summary="Status do upload",
    description="Obtém o status atual de um upload em andamento."
)
async def get_upload_status(upload_id: str):
    status_info = UploadService.get_upload_status(upload_id)
    
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload não encontrado"
        )
    
    return format_success_response(
        message="Status do upload obtido com sucesso",
        data=status_info
    )

