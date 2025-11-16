"""Utilitários para validação e formatação."""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def validate_file(file_path: str) -> tuple[bool, Optional[str]]:
    """
    Valida se o arquivo existe e é acessível.
    
    Args:
        file_path: Caminho para o arquivo de vídeo
        
    Returns:
        Tupla (sucesso, mensagem_erro)
    """
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


def generate_output_filename(
    input_file: str,
    classification: Optional[str] = None,
    metadata: Optional[dict] = None
) -> str:
    """
    Gera nome de arquivo de saída SEO-friendly com timestamp.
    
    Args:
        input_file: Caminho do arquivo de entrada
        classification: Classificação do vídeo (opcional)
        metadata: Metadados do vídeo (opcional)
        
    Returns:
        Nome do arquivo de saída formatado
    """
    from src.core.video_content_analyzer import generate_seo_friendly_name, sanitize_filename
    
    # Gera nome SEO-friendly baseado em conteúdo
    seo_base = generate_seo_friendly_name(input_file, classification, metadata)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    filename = sanitize_filename(f"{seo_base}-forensic-report-{timestamp}.json")
    return filename


def format_duration(seconds: Optional[float]) -> Optional[str]:
    """
    Formata duração em segundos para formato legível.
    
    Args:
        seconds: Duração em segundos
        
    Returns:
        String formatada (HH:MM:SS) ou None
    """
    if seconds is None:
        return None
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_datetime_br(dt: Optional[datetime] = None) -> str:
    """
    Formata data/hora em padrão brasileiro para nomes de arquivo.
    
    Args:
        dt: Objeto datetime (usa agora se None)
        
    Returns:
        String formatada: DD-MM-YYYY-HH-MM-SS
    """
    if dt is None:
        dt = datetime.now()
    
    return dt.strftime("%d-%m-%Y-%H-%M-%S")


def copy_file_to_output(
    source_path: str,
    output_dir: str,
    subdir: str = "",
    custom_filename: Optional[str] = None
) -> Path:
    """
    Copia arquivo para diretório de saída com nome opcional.
    
    Args:
        source_path: Caminho do arquivo original
        output_dir: Diretório base de saída
        subdir: Subdiretório dentro de output_dir (ex: 'original', 'reports', 'clean')
        custom_filename: Nome customizado para o arquivo (opcional)
        
    Returns:
        Caminho do arquivo copiado
    """
    source = Path(source_path)
    output_base = Path(output_dir)
    
    if subdir:
        output_path = output_base / subdir
    else:
        output_path = output_base
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Usa nome customizado ou nome original
    if custom_filename:
        dest_file = output_path / custom_filename
    else:
        dest_file = output_path / source.name
    
    shutil.copy2(source, dest_file)
    
    return dest_file


def ensure_output_dirs(output_dir: str) -> dict[str, Path]:
    """
    Garante que todos os diretórios de saída existem.
    
    Args:
        output_dir: Diretório base de saída
        
    Returns:
        Dicionário com caminhos dos diretórios criados
    """
    base = Path(output_dir)
    dirs = {
        "original": base / "original",
        "reports": base / "reports",
        "clean": base / "clean"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs


def generate_clean_filename(
    input_file: str,
    visual_analysis: Optional[dict] = None,
    audio_analysis: Optional[dict] = None
) -> str:
    """
    Gera nome descritivo humano em português brasileiro para arquivo limpo.
    
    Args:
        input_file: Caminho do arquivo de entrada
        visual_analysis: Resultado da análise visual (opcional)
        audio_analysis: Resultado da transcrição (opcional)
        
    Returns:
        Nome do arquivo limpo descritivo: [descricao]-[DD-MM-YYYY-HH-MM-SS].mp4
    """
    from src.core.human_name_generator import generate_human_filename
    
    return generate_human_filename(input_file, visual_analysis, audio_analysis)

