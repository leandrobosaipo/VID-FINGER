"""Endpoints de arquivos."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import uuid
from app.database import get_db
from app.api.v1.schemas import FileType
from app.models.analysis import Analysis
from app.models.file import File

router = APIRouter()


@router.get("/{analysis_id}/{file_type}", tags=["files"])
async def get_file(
    analysis_id: str,
    file_type: FileType,
    db: AsyncSession = Depends(get_db)
):
    """
    Download de arquivo da análise.
    
    **Tipos disponíveis:**
    - `original`: Arquivo de vídeo original enviado
    - `clean_video`: Vídeo limpo (sem fingerprints de IA) - disponível após análise completa
    - `report`: Relatório JSON (use `/reports/{analysis_id}/report` para JSON formatado)
    
    **Exemplo de uso:**
    - `/api/v1/files/{analysis_id}/original` - Download do vídeo original
    - `/api/v1/files/{analysis_id}/clean_video` - Download do vídeo limpo
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
        
        # Determinar qual arquivo buscar baseado no tipo
        file_id = None
        if file_type == FileType.original:
            file_id = analysis.original_file_id
        elif file_type == FileType.clean_video:
            file_id = analysis.clean_video_id
            if not file_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vídeo limpo ainda não foi gerado. Análise pode estar em andamento."
                )
        elif file_type == FileType.report:
            file_id = analysis.report_file_id
            if not file_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Relatório ainda não foi gerado. Análise pode estar em andamento."
                )
        
        if not file_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Arquivo do tipo {file_type.value} não encontrado"
            )
        
        # Buscar arquivo
        result = await db.execute(
            select(File).where(File.id == file_id)
        )
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo não encontrado"
            )
        
        # Verificar se arquivo existe
        file_path = Path(file_record.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo não encontrado no sistema de arquivos"
            )
        
        # Retornar arquivo
        return FileResponse(
            path=str(file_path),
            filename=file_record.original_filename,
            media_type=file_record.mime_type or "application/octet-stream"
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
            detail=f"Erro ao obter arquivo: {str(e)}"
        )

