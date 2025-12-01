"""Context manager para Correlation ID em requisições."""
import contextvars
from typing import Optional
import uuid

# Context variable para Correlation ID
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id',
    default=None
)


def get_correlation_id() -> Optional[str]:
    """Obtém Correlation ID da requisição atual."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Define Correlation ID para a requisição atual.
    
    Args:
        correlation_id: ID existente ou None para gerar novo
        
    Returns:
        Correlation ID (gerado ou fornecido)
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    correlation_id_var.set(correlation_id)
    return correlation_id


def clear_correlation_id():
    """Limpa Correlation ID do contexto atual."""
    correlation_id_var.set(None)


def format_log_with_context(
    context: str,
    message: str,
    analysis_id: Optional[str] = None,
    upload_id: Optional[str] = None,
    **kwargs
) -> str:
    """
    Formata mensagem de log com contexto estruturado.
    
    Args:
        context: Contexto do log (ex: REQUEST, UPLOAD, STORAGE)
        message: Mensagem principal
        analysis_id: ID da análise (opcional)
        upload_id: ID do upload (opcional)
        **kwargs: Campos adicionais para incluir
        
    Returns:
        Mensagem formatada com contexto
    """
    correlation_id = get_correlation_id()
    
    # Montar contexto
    parts = [f"[{context}]"]
    
    if correlation_id:
        parts.append(f"[CORRELATION:{correlation_id}]")
    
    if analysis_id:
        parts.append(f"[ANALYSIS:{analysis_id}]")
    
    if upload_id:
        parts.append(f"[UPLOAD_ID:{upload_id}]")
    
    # Campos adicionais
    for key, value in kwargs.items():
        if value is not None:
            parts.append(f"[{key.upper()}:{value}]")
    
    # Mensagem
    parts.append(message)
    
    return " ".join(parts)

