"""Formatação de respostas."""
from datetime import datetime
from typing import Optional, Dict, Any


def format_success_response(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    analysis_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Formata resposta de sucesso.
    
    Args:
        message: Mensagem humanizada
        data: Dados adicionais
        analysis_id: ID da análise (se aplicável)
    
    Returns:
        Resposta formatada
    """
    response = {
        "success": True,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if data:
        response["data"] = data
    
    if analysis_id:
        response["analysis_id"] = analysis_id
    
    return response


def format_error_response(
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Formata resposta de erro.
    
    Args:
        message: Mensagem humanizada do erro
        error_code: Código do erro
        details: Detalhes técnicos para debug
    
    Returns:
        Resposta formatada
    """
    response = {
        "success": False,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if error_code:
        response["error_code"] = error_code
    
    if details:
        response["details"] = details
    
    return response

