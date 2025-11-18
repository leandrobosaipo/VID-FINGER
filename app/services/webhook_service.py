"""Serviço de webhooks."""
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.analysis import Analysis
from app.models.analysis_step import AnalysisStep, StepName, StepStatus
import logging

logger = logging.getLogger(__name__)

# Ordem fixa das etapas para cálculo de progresso
STEP_ORDER = [
    StepName.upload,
    StepName.metadata_extraction,
    StepName.prnu,
    StepName.fft,
    StepName.classification,
    StepName.cleaning,
]


class WebhookService:
    """Serviço para enviar webhooks."""
    
    @staticmethod
    async def send_webhook(
        webhook_url: str,
        event: str,
        analysis_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envia webhook HTTP POST.
        
        Args:
            webhook_url: URL do webhook
            event: Nome do evento
            analysis_id: ID da análise
            data: Dados adicionais
            
        Returns:
            True se sucesso, False caso contrário
        """
        payload = {
            "event": event,
            "analysis_id": analysis_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data or {}
        }
        
        for attempt in range(settings.WEBHOOK_RETRY_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload
                    )
                    response.raise_for_status()
                    logger.info(f"Webhook enviado com sucesso: {event} para {analysis_id}")
                    return True
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} de webhook falhou: {e}")
                if attempt < settings.WEBHOOK_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Falha ao enviar webhook após {settings.WEBHOOK_RETRY_ATTEMPTS} tentativas")
        
        return False
    
    @staticmethod
    async def send_step_started(
        webhook_url: str,
        analysis_id: str,
        step_name: str
    ):
        """Envia webhook de início de etapa."""
        return await WebhookService.send_webhook(
            webhook_url=webhook_url,
            event=f"analysis.step.started",
            analysis_id=analysis_id,
            data={"step": step_name}
        )
    
    @staticmethod
    async def send_step_completed(
        webhook_url: str,
        analysis_id: str,
        step_name: str,
        progress: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Envia webhook de conclusão de etapa."""
        return await WebhookService.send_webhook(
            webhook_url=webhook_url,
            event=f"analysis.step.completed",
            analysis_id=analysis_id,
            data={
                "step": step_name,
                "progress": progress,
                "metadata": metadata or {}
            }
        )
    
    @staticmethod
    async def send_analysis_completed(
        webhook_url: str,
        analysis_id: str,
        classification: str,
        confidence: float
    ):
        """Envia webhook de conclusão da análise."""
        return await WebhookService.send_webhook(
            webhook_url=webhook_url,
            event="analysis.completed",
            analysis_id=analysis_id,
            data={
                "classification": classification,
                "confidence": confidence
            }
        )
    
    @staticmethod
    async def send_analysis_failed(
        webhook_url: str,
        analysis_id: str,
        error_message: str
    ):
        """Envia webhook de falha da análise."""
        return await WebhookService.send_webhook(
            webhook_url=webhook_url,
            event="analysis.failed",
            analysis_id=analysis_id,
            data={"error": error_message}
        )
    
    @staticmethod
    def _calculate_step_duration(step: AnalysisStep) -> Optional[float]:
        """Calcula duração de uma etapa em segundos."""
        if step.started_at and step.completed_at:
            delta = step.completed_at - step.started_at
            return delta.total_seconds()
        elif step.started_at:
            # Etapa em andamento, calcular até agora
            delta = datetime.utcnow() - step.started_at
            return delta.total_seconds()
        return None
    
    @staticmethod
    def _get_step_result(
        step_name: StepName,
        analysis: Analysis,
        step_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai resultados específicos de cada etapa quando disponíveis.
        
        Args:
            step_name: Nome da etapa
            analysis: Objeto Analysis com dados da análise
            step_data: Dados adicionais da etapa (ex: metadados, resultados de análise)
        """
        result = {}
        
        if step_name == StepName.metadata_extraction:
            if analysis.video_metadata:
                try:
                    import json
                    if isinstance(analysis.video_metadata, str):
                        metadata = json.loads(analysis.video_metadata)
                    else:
                        metadata = analysis.video_metadata
                    result = {
                        "metadata_extracted": True,
                        "codec": metadata.get("codec_name"),
                        "duration": metadata.get("duration"),
                        "resolution": f"{metadata.get('width')}x{metadata.get('height')}",
                        "frame_rate": metadata.get("r_frame_rate")
                    }
                except Exception:
                    result = {"metadata_extracted": True}
        
        elif step_name == StepName.classification:
            if analysis.classification:
                result = {
                    "classification": analysis.classification,
                    "confidence": analysis.confidence
                }
        
        elif step_name == StepName.prnu:
            if step_data:
                result = {
                    "prnu_detected": step_data.get("prnu_detected"),
                    "confidence": step_data.get("confidence")
                }
        
        elif step_name == StepName.fft:
            if step_data:
                result = {
                    "fft_analysis_completed": True,
                    "diffusion_detected": step_data.get("diffusion_detected")
                }
        
        elif step_name == StepName.cleaning:
            if analysis.clean_video_id:
                result = {
                    "clean_video_generated": True,
                    "clean_video_id": str(analysis.clean_video_id)
                }
        
        return result if result else None
    
    @staticmethod
    async def _collect_step_statistics(
        analysis_id: str,
        db: AsyncSession,
        current_step_name: Optional[StepName] = None,
        step_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Coleta estatísticas de todas as etapas do banco de dados.
        
        Returns:
            Dicionário com estatísticas completas das etapas
        """
        import uuid
        
        # Buscar análise
        analysis_uuid = uuid.UUID(analysis_id)
        result = await db.execute(
            select(Analysis).where(Analysis.id == analysis_uuid)
        )
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            return {}
        
        # Buscar todas as etapas
        result = await db.execute(
            select(AnalysisStep)
            .where(AnalysisStep.analysis_id == analysis_uuid)
            .order_by(AnalysisStep.started_at)
        )
        steps = result.scalars().all()
        
        # Criar dicionário de etapas por nome
        steps_by_name = {step.step_name: step for step in steps}
        
        # Processar etapas na ordem definida
        completed_steps = []
        pending_steps = []
        current_step_info = None
        total_duration = 0.0
        
        for step_name in STEP_ORDER:
            step = steps_by_name.get(step_name)
            
            # Usar step_result se for a etapa atual sendo processada
            use_step_result = (step_name == current_step_name and step_result is not None)
            
            if step and step.status == StepStatus.completed:
                duration = WebhookService._calculate_step_duration(step) or 0.0
                total_duration += duration
                
                step_result_data = WebhookService._get_step_result(
                    step_name,
                    analysis,
                    step_result if use_step_result else None
                )
                
                completed_steps.append({
                    "name": step_name.value,
                    "status": step.status.value,
                    "started_at": step.started_at.isoformat() + "Z" if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() + "Z" if step.completed_at else None,
                    "duration_seconds": round(duration, 2),
                    "result": step_result_data
                })
            elif step and step.status == StepStatus.running:
                duration = WebhookService._calculate_step_duration(step) or 0.0
                
                step_result_data = WebhookService._get_step_result(
                    step_name,
                    analysis,
                    step_result if use_step_result else None
                )
                
                current_step_info = {
                    "name": step_name.value,
                    "status": step.status.value,
                    "started_at": step.started_at.isoformat() + "Z" if step.started_at else None,
                    "completed_at": None,
                    "duration_seconds": round(duration, 2),
                    "result": step_result_data
                }
            elif step_name == current_step_name and not step:
                # Etapa atual que ainda não foi criada no banco (pode acontecer no início)
                current_step_info = {
                    "name": step_name.value,
                    "status": "running",
                    "started_at": datetime.utcnow().isoformat() + "Z",
                    "completed_at": None,
                    "duration_seconds": 0.0,
                    "result": step_result if use_step_result else None
                }
            else:
                pending_steps.append(step_name.value)
        
        # Calcular estatísticas
        total_steps = len(STEP_ORDER)
        completed_count = len(completed_steps)
        running_count = 1 if current_step_info else 0
        pending_count = len(pending_steps)
        
        # Calcular progresso (incluindo etapa atual como parcialmente completa)
        progress_percentage = ((completed_count + (0.5 if running_count > 0 else 0)) / total_steps) * 100
        
        # Estimar tempo restante baseado na média de tempo por etapa
        estimated_remaining = None
        if completed_count > 0:
            avg_duration = total_duration / completed_count
            estimated_remaining = avg_duration * pending_count
        
        statistics = {
            "total_steps": total_steps,
            "completed_count": completed_count,
            "running_count": running_count,
            "pending_count": pending_count,
            "progress_percentage": round(progress_percentage, 2),
            "total_duration_seconds": round(total_duration, 2),
            "estimated_remaining_seconds": round(estimated_remaining, 2) if estimated_remaining else None
        }
        
        return {
            "current_step": current_step_info,
            "completed_steps": completed_steps,
            "pending_steps": pending_steps,
            "statistics": statistics,
            "analysis": {
                "status": analysis.status.value,
                "classification": analysis.classification,
                "confidence": analysis.confidence
            }
        }
    
    @staticmethod
    async def send_step_update(
        webhook_url: str,
        analysis_id: str,
        step_name: StepName,
        is_starting: bool,
        db: AsyncSession,
        step_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Envia webhook detalhado de atualização de etapa.
        
        Args:
            webhook_url: URL do webhook
            analysis_id: ID da análise
            step_name: Nome da etapa
            is_starting: True se está iniciando, False se está concluindo
            db: Sessão do banco de dados
            step_result: Dados específicos do resultado da etapa (opcional)
        """
        try:
            # Coletar estatísticas
            # Se está concluindo, ainda passamos o step_name para incluir resultados
            stats = await WebhookService._collect_step_statistics(
                analysis_id,
                db,
                current_step_name=step_name,
                step_result=step_result
            )
            
            # Determinar evento
            event = "analysis.step.started" if is_starting else "analysis.step.completed"
            
            # Enviar webhook
            return await WebhookService.send_webhook(
                webhook_url=webhook_url,
                event=event,
                analysis_id=analysis_id,
                data=stats
            )
        except Exception as e:
            logger.error(f"Erro ao enviar webhook de etapa {step_name}: {e}", exc_info=True)
            return False

