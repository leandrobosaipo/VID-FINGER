"""Gerador de nomes descritivos em português brasileiro baseado em conteúdo do vídeo."""
from typing import Optional, Dict, Any
from pathlib import Path
import re
from datetime import datetime

from src.utils import format_datetime_br


def sanitize_filename(filename: str, max_length: int = 120) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres problemáticos.
    
    Args:
        filename: Nome original
        max_length: Tamanho máximo
        
    Returns:
        Nome sanitizado
    """
    # Remove caracteres especiais, mantém apenas alfanuméricos, hífens e underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\-_.]', '-', filename)
    
    # Remove hífens/underscores duplicados
    sanitized = re.sub(r'[-_]+', '-', sanitized)
    
    # Remove hífens no início e fim
    sanitized = sanitized.strip('-_.')
    
    # Limita tamanho
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('-_.')
    
    return sanitized or "video"


def combine_keywords(visual_keywords: list[str], audio_keywords: list[str], max_total: int = 4) -> list[str]:
    """
    Combina palavras-chave visuais e de áudio de forma inteligente.
    
    Args:
        visual_keywords: Palavras-chave da análise visual
        audio_keywords: Palavras-chave da transcrição
        max_total: Número máximo total de palavras-chave
        
    Returns:
        Lista combinada de palavras-chave
    """
    combined = []
    
    # Prioriza palavras-chave visuais (ambiente, movimento)
    # Adiciona palavras-chave de áudio como complemento
    for keyword in visual_keywords:
        if len(combined) < max_total:
            combined.append(keyword)
    
    # Adiciona palavras-chave de áudio que não estão nas visuais
    for keyword in audio_keywords:
        if keyword not in combined and len(combined) < max_total:
            combined.append(keyword)
    
    return combined[:max_total]


def generate_human_description(
    video_path: str,
    visual_analysis: Optional[Dict[str, Any]] = None,
    audio_analysis: Optional[Dict[str, Any]] = None
) -> str:
    """
    Gera descrição humana em português baseada em análise visual e de áudio.
    
    Args:
        video_path: Caminho do vídeo
        visual_analysis: Resultado da análise visual (opcional, None se falhou)
        audio_analysis: Resultado da transcrição (opcional, None se falhou)
        
    Returns:
        Descrição em português para usar no nome do arquivo
    """
    # Extrai palavras-chave (com fallbacks)
    visual_keywords = []
    if visual_analysis and visual_analysis.get("success"):
        visual_keywords = visual_analysis.get("keywords", [])
    elif visual_analysis and visual_analysis.get("description"):
        # Se não tem keywords mas tem descrição, usa descrição
        desc = visual_analysis.get("description", "")
        if desc and desc != "video-conteudo-desconhecido":
            visual_keywords = [desc]
    
    audio_keywords = []
    if audio_analysis and audio_analysis.get("success"):
        audio_keywords = audio_analysis.get("keywords", [])
    
    # Combina palavras-chave
    combined_keywords = combine_keywords(visual_keywords, audio_keywords, max_total=4)
    
    # Gera descrição
    if combined_keywords:
        description = "-".join(combined_keywords)
    elif visual_analysis and visual_analysis.get("description"):
        # Usa descrição visual mesmo que não tenha palavras-chave específicas
        description = visual_analysis.get("description", "video-conteudo-desconhecido")
    else:
        # Fallback: usa nome do arquivo original sanitizado
        input_name = Path(video_path).stem
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '-', input_name)
        sanitized = re.sub(r'-+', '-', sanitized).strip('-')
        description = sanitized[:30] if sanitized else "video-conteudo-desconhecido"
    
    # Limita tamanho
    description = description[:60]
    
    return description


def generate_human_filename(
    video_path: str,
    visual_analysis: Optional[Dict[str, Any]] = None,
    audio_analysis: Optional[Dict[str, Any]] = None,
    dt: Optional[Any] = None
) -> str:
    """
    Gera nome de arquivo descritivo em português brasileiro.
    
    Args:
        video_path: Caminho do vídeo
        visual_analysis: Resultado da análise visual (opcional)
        audio_analysis: Resultado da transcrição (opcional)
        dt: Objeto datetime (opcional, usa agora se None)
        
    Returns:
        Nome de arquivo formatado: [descricao]-[DD-MM-YYYY-HH-MM-SS].mp4
    """
    # Gera descrição
    description = generate_human_description(video_path, visual_analysis, audio_analysis)
    
    # Formata data/hora brasileira
    timestamp = format_datetime_br(dt)
    
    # Monta nome completo
    filename = f"{description}-{timestamp}.mp4"
    
    # Sanitiza
    filename = sanitize_filename(filename, max_length=120)
    
    return filename

