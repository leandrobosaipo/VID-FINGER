"""Endpoints de análise."""
from fastapi import APIRouter, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from fastapi import Depends
from app.services.analysis_service import AnalysisService
from app.api.v1.schemas import AnalysisResponse, AnalysisListResponse
from app.utils.formatters import format_success_response, format_error_response
from app.config import settings
import uuid

router = APIRouter()


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Obtém status completo da análise."""
    try:
        analysis = await AnalysisService.get_analysis(analysis_id, db)
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada"
            )
        
        # Buscar steps
        from app.models.analysis_step import AnalysisStep
        steps_result = await db.execute(
            select(AnalysisStep)
            .where(AnalysisStep.analysis_id == analysis.id)
            .order_by(AnalysisStep.step_name)
        )
        steps = steps_result.scalars().all()
        
        # Formatar steps
        steps_info = []
        current_step = None
        total_progress = 0
        
        for step in steps:
            steps_info.append({
                "name": step.step_name.value,
                "status": step.status.value,
                "progress": step.progress,
                "started_at": step.started_at,
                "completed_at": step.completed_at
            })
            
            if step.status.value == "running":
                current_step = step.step_name.value
            
            total_progress += step.progress
        
        # Calcular progresso médio
        avg_progress = total_progress // len(steps) if steps else 0
        
        # Gerar URLs base
        if request:
            base_url = str(request.base_url).rstrip('/')
        else:
            base_url = settings.API_BASE_URL or "http://localhost:8000"
        
        # URLs para arquivos
        original_video_url = f"{base_url}/api/v1/files/{analysis_id}/original"
        clean_video_url = None
        report_url = None
        
        if analysis.clean_video_id:
            clean_video_url = f"{base_url}/api/v1/files/{analysis_id}/clean_video"
        
        if analysis.report_file_id:
            report_url = f"{base_url}/api/v1/reports/{analysis_id}/report"
        
        return AnalysisResponse(
            id=str(analysis.id),
            status=analysis.status.value,
            progress=avg_progress,
            current_step=current_step,
            steps=steps_info,
            created_at=analysis.created_at,
            started_at=analysis.started_at,
            completed_at=analysis.completed_at,
            classification=analysis.classification,
            confidence=analysis.confidence
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao obter análise",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Lista análises com paginação."""
    try:
        from app.models.analysis import Analysis
        
        # Query base
        query = select(Analysis)
        
        # Filtro por status
        if status_filter:
            query = query.where(Analysis.status == status_filter)
        
        # Contar total
        count_query = select(func.count()).select_from(Analysis)
        if status_filter:
            count_query = count_query.where(Analysis.status == status_filter)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Paginação
        offset = (page - 1) * page_size
        query = query.order_by(Analysis.created_at.desc()).offset(offset).limit(page_size)
        
        # Executar query
        result = await db.execute(query)
        analyses = result.scalars().all()
        
        # Formatar respostas
        items = []
        for analysis in analyses:
            # Gerar URLs base
            base_url = settings.API_BASE_URL or "http://localhost:8000"
            original_video_url = f"{base_url}/api/v1/files/{str(analysis.id)}/original"
            clean_video_url = f"{base_url}/api/v1/files/{str(analysis.id)}/clean_video" if analysis.clean_video_id else None
            report_url = f"{base_url}/api/v1/reports/{str(analysis.id)}/report" if analysis.report_file_id else None
            
            items.append(AnalysisResponse(
                id=str(analysis.id),
                status=analysis.status.value,
                progress=0,  # TODO: Calcular progresso real
                current_step=None,
                steps=[],
                created_at=analysis.created_at,
                started_at=analysis.started_at,
                completed_at=analysis.completed_at,
                classification=analysis.classification,
                confidence=analysis.confidence,
                clean_video_url=clean_video_url,
                report_url=report_url,
                original_video_url=original_video_url
            ))
        
        return AnalysisListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao listar análises",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.post("/{analysis_id}/reprocess", tags=["analysis"])
async def reprocess_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocessa uma análise pendente ou falha.
    
    Útil para análises que ficaram em "pending" antes da implementação
    do processamento automático.
    """
    try:
        from app.services.analysis_processor import AnalysisProcessor
        import asyncio
        
        # Verificar se análise existe
        analysis = await AnalysisService.get_analysis(analysis_id, db)
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada"
            )
        
        # Verificar se pode reprocessar
        if analysis.status.value == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Análise já está em processamento"
            )
        
        # Iniciar processamento em background
        asyncio.create_task(AnalysisProcessor.process_analysis(analysis_id, db))
        
        return format_success_response(
            message="Reprocessamento iniciado",
            data={"analysis_id": analysis_id, "status": "processing"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=format_error_response(
                message="Erro ao iniciar reprocessamento",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)}
            )
        )


@router.post("/{analysis_id}/cancel", tags=["analysis"])
async def cancel_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancela análise em andamento."""
    # TODO: Implementar cancelamento via Celery
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Funcionalidade em desenvolvimento"
    )
