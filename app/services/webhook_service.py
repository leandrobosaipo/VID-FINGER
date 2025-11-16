"""Serviço de webhooks."""
import httpx
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from app.config import settings
import logging

logger = logging.getLogger(__name__)


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

