"""Utilitários legados do projeto original."""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def validate_file(file_path: str) -> tuple[bool, Optional[str]]:
    """Valida se o arquivo existe e é acessível."""
    if not file_path:
        return False, "Caminho do arquivo não fornecido"
    
    path = Path(file_path)
    
    if not path.exists():
        return False, f"Arquivo não encontrado: {file_path}"
    
    if not path.is_file():
        return False, f"O caminho não é um arquivo: {file_path}"
    
    if not os.access(path, os.R_OK):
        return False, f"Sem permissão de leitura: {file_path}"
    
    return True, None


def format_datetime_br(dt: Optional[datetime] = None) -> str:
    """Formata data/hora em padrão brasileiro para nomes de arquivo."""
    if dt is None:
        dt = datetime.now()
    
    return dt.strftime("%d-%m-%Y-%H-%M-%S")


def generate_clean_filename(
    input_file: str,
    visual_analysis: Optional[dict] = None,
    audio_analysis: Optional[dict] = None
) -> str:
    """Gera nome descritivo humano em português brasileiro para arquivo limpo."""
    from app.core.human_name_generator import generate_human_filename
    
    return generate_human_filename(input_file, visual_analysis, audio_analysis)

