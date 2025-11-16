"""Endpoints de relatórios."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import uuid
import json
from app.database import get_db
from app.models.analysis import Analysis
from app.models.file import File, FileType

router = APIRouter()


@router.get("/{analysis_id}/report", tags=["reports"])
async def get_report(
    analysis_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download do relatório JSON da análise.
    
    Retorna o relatório forense completo em formato JSON com:
    - Classificação do vídeo (REAL_CAMERA, AI_HEVC, etc.)
    - Confiança da classificação
    - Análise PRNU, FFT, Metadados
    - Timeline frame a frame
    - Ferramentas detectadas
    """
    try:
        # Buscar análise
        analysis_uuid = uuid.UUID(analysis_id)
        result = await db.execute(
            select(Analysis).where(Analysis.id == analysis_uuid)
        )
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada"
            )
        
        # Buscar arquivo de relatório
        if not analysis.report_file_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relatório ainda não foi gerado. Análise pode estar em andamento."
            )
        
        result = await db.execute(
            select(File).where(File.id == analysis.report_file_id)
        )
        report_file = result.scalar_one_or_none()
        
        if not report_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo de relatório não encontrado"
            )
        
        # Verificar se arquivo existe
        file_path = Path(report_file.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo de relatório não encontrado no sistema de arquivos"
            )
        
        # Retornar JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        return JSONResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="{report_file.original_filename}"'
            }
        )
    
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de análise inválido"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter relatório: {str(e)}"
        )

