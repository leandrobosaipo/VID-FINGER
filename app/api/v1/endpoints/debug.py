"""Endpoints de debug e troubleshooting."""
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.analysis import Analysis, AnalysisStatus
from app.models.analysis_step import AnalysisStep, StepName, StepStatus
from app.models.file import File
from app.services.analysis_processor import AnalysisProcessor
from app.services.analysis_service import AnalysisService
from app.core.cleaner import check_ffmpeg_available
from app.utils.formatters import format_success_response, format_error_response
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health/dependencies")
async def health_dependencies():
    """
    Verifica status de todas as dependências do sistema.
    
    Retorna status de:
    - FFmpeg
    - Banco de dados
    - Redis (opcional)
    - Permissões de escrita
    """
    import subprocess
    
    dependencies = {
        "ffmpeg": {
            "available": check_ffmpeg_available(),
            "path": None
        },
        "database": {
            "accessible": False,
            "error": None
        },
        "redis": {
            "available": False,
            "error": None
        },
        "storage": {
            "writable": False,
            "paths": {}
        }
    }
    
    # Verificar FFmpeg path
    try:
        result = subprocess.run(
            ["which", "ffmpeg"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            dependencies["ffmpeg"]["path"] = result.stdout.decode().strip()
    except Exception as e:
        logger.warning(f"Erro ao verificar path do FFmpeg: {e}")
    
    # Verificar banco de dados
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
            dependencies["database"]["accessible"] = True
    except Exception as e:
        dependencies["database"]["error"] = str(e)
    
    # Verificar Redis
    try:
        from app.config import settings
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        dependencies["redis"]["available"] = True
    except ImportError:
        dependencies["redis"]["error"] = "redis não instalado"
    except Exception as e:
        dependencies["redis"]["error"] = str(e)
    
    # Verificar permissões de escrita
    try:
        storage_path = Path("storage")
        output_path = Path("output")
        
        dependencies["storage"]["writable"] = True
        dependencies["storage"]["paths"] = {
            "storage": {
                "exists": storage_path.exists(),
                "writable": storage_path.exists() and storage_path.is_dir() and (storage_path / ".test_write").touch() or False
            },
            "output": {
                "exists": output_path.exists(),
                "writable": output_path.exists() and output_path.is_dir() and (output_path / ".test_write").touch() or False
            }
        }
        
        # Limpar arquivos de teste
        for path in [storage_path / ".test_write", output_path / ".test_write"]:
            if path.exists():
                path.unlink()
    except Exception as e:
        dependencies["storage"]["error"] = str(e)
    
    all_ok = (
        dependencies["ffmpeg"]["available"] and
        dependencies["database"]["accessible"] and
        dependencies["storage"]["writable"]
    )
    
    return format_success_response(
        message="Status de dependências verificado",
        data={
            "all_dependencies_ok": all_ok,
            "dependencies": dependencies
        }
    )


@router.get("/debug/analysis/{analysis_id}/status")
async def debug_analysis_status(
    analysis_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna status detalhado de uma análise para debug.
    
    Inclui:
    - Status da análise
    - Status de cada etapa
    - Arquivos gerados
    - Erros encontrados
    - Informações de debug
    """
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de análise inválido"
        )
    
    # Buscar análise
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_uuid)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análise não encontrada"
        )
    
    # Buscar etapas
    steps_result = await db.execute(
        select(AnalysisStep)
        .where(AnalysisStep.analysis_id == analysis_uuid)
        .order_by(AnalysisStep.step_name)
    )
    steps = steps_result.scalars().all()
    
    # Buscar arquivos
    files_result = await db.execute(
        select(File).where(File.analysis_id == analysis_uuid)
    )
    files = files_result.scalars().all()
    
    # Verificar arquivos no filesystem
    files_status = {}
    for file in files:
        file_path = Path(file.file_path)
        files_status[str(file.id)] = {
            "type": file.file_type.value,
            "path": file.file_path,
            "exists": file_path.exists(),
            "size": file_path.stat().st_size if file_path.exists() else 0,
            "stored": True
        }
    
    # Preparar resposta detalhada
    steps_detail = []
    for step in steps:
        steps_detail.append({
            "step_name": step.step_name.value,
            "status": step.status.value,
            "progress": step.progress,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            "error": step.error_message if hasattr(step, 'error_message') else None
        })
    
    return format_success_response(
        message="Status detalhado da análise",
        data={
            "analysis": {
                "id": str(analysis.id),
                "status": analysis.status.value,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                "error_message": analysis.error_message,
                "classification": analysis.classification,
                "confidence": analysis.confidence
            },
            "steps": steps_detail,
            "files": files_status,
            "file_ids": {
                "original_file_id": str(analysis.original_file_id) if analysis.original_file_id else None,
                "report_file_id": str(analysis.report_file_id) if analysis.report_file_id else None,
                "clean_video_id": str(analysis.clean_video_id) if analysis.clean_video_id else None
            }
        }
    )


@router.post("/debug/analysis/{analysis_id}/force-step/{step_name}")
async def debug_force_step(
    analysis_id: str,
    step_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Força avanço manual de uma etapa específica.
    
    Útil para debug e troubleshooting quando uma etapa está travada.
    """
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de análise inválido"
        )
    
    # Validar step_name
    try:
        step_enum = StepName[step_name]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Etapa inválida: {step_name}. Etapas válidas: {', '.join([s.name for s in StepName])}"
        )
    
    # Buscar análise
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_uuid)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análise não encontrada"
        )
    
    # Buscar etapa
    step_result = await db.execute(
        select(AnalysisStep)
        .where(AnalysisStep.analysis_id == analysis_uuid)
        .where(AnalysisStep.step_name == step_enum)
    )
    step = step_result.scalar_one_or_none()
    
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Etapa {step_name} não encontrada para esta análise"
        )
    
    # Forçar etapa para completed
    from datetime import datetime
    step.status = StepStatus.completed
    step.progress = 100
    if not step.started_at:
        step.started_at = datetime.utcnow()
    step.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(step)
    await db.refresh(analysis)
    
    logger.info(f"[DEBUG] Etapa {step_name} forçada para completed na análise {analysis_id}")
    
    return format_success_response(
        message=f"Etapa {step_name} forçada para completed",
        data={
            "analysis_id": analysis_id,
            "step_name": step_name,
            "status": step.status.value,
            "progress": step.progress
        }
    )


@router.post("/debug/analysis/{analysis_id}/retry")
async def debug_retry_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocessa uma análise do início.
    
    Útil para tentar novamente após correções ou para debug.
    """
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de análise inválido"
        )
    
    # Buscar análise
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_uuid)
    )
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análise não encontrada"
        )
    
    # Resetar análise para pending
    analysis.status = AnalysisStatus.pending
    analysis.started_at = None
    analysis.completed_at = None
    analysis.error_message = None
    
    # Resetar todas as etapas para pending (exceto upload)
    steps_result = await db.execute(
        select(AnalysisStep).where(AnalysisStep.analysis_id == analysis_uuid)
    )
    steps = steps_result.scalars().all()
    
    from datetime import datetime
    for step in steps:
        if step.step_name != StepName.upload:
            step.status = StepStatus.pending
            step.progress = 0
            step.started_at = None
            step.completed_at = None
    
    await db.commit()
    await db.refresh(analysis)
    
    # Iniciar processamento usando BackgroundTasks do FastAPI
    # Nota: Como estamos em um endpoint, precisamos usar BackgroundTasks
    # Mas como não temos acesso direto aqui, vamos usar a função diretamente
    # que já cria sua própria sessão de banco
    from fastapi import BackgroundTasks
    import asyncio
    
    try:
        # Usar a função start_processing_background que já gerencia sua própria sessão
        # Criar task em background sem bloquear
        try:
            loop = asyncio.get_running_loop()
            # Criar task em background
            loop.create_task(
                AnalysisService.start_processing_background(str(analysis_id))
            )
            logger.info(f"[DEBUG] Task de processamento criada para análise {analysis_id}")
        except RuntimeError:
            # Não há loop rodando, criar novo
            import asyncio
            asyncio.create_task(
                AnalysisService.start_processing_background(str(analysis_id))
            )
            logger.info(f"[DEBUG] Processamento agendado para análise {analysis_id}")
    except Exception as e:
        logger.error(f"[DEBUG] Erro ao iniciar processamento: {e}", exc_info=True)
    
    logger.info(f"[DEBUG] Análise {analysis_id} resetada e reprocessamento iniciado")
    
    return format_success_response(
        message="Análise resetada e reprocessamento iniciado",
        data={
            "analysis_id": analysis_id,
            "status": "pending",
            "message": "Processamento será iniciado em background"
        }
    )

