"""Validações de arquivo."""
import mimetypes
from pathlib import Path
from typing import Tuple, Optional


# Tipos MIME permitidos
ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",  # MOV
    "video/x-msvideo",  # AVI
    "video/x-matroska",  # MKV
    "video/webm",
}

# Extensões permitidas
ALLOWED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}


def validate_file_type(filename: str, mime_type: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Valida tipo de arquivo.
    
    Returns:
        (is_valid, error_message)
    """
    # Validar extensão
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensão não permitida: {file_ext}"
    
    # Validar MIME type se fornecido
    if mime_type:
        if mime_type not in ALLOWED_MIME_TYPES:
            return False, f"Tipo MIME não permitido: {mime_type}"
        
        # Verificar consistência entre extensão e MIME type
        expected_mime = mimetypes.guess_type(filename)[0]
        if expected_mime and expected_mime != mime_type:
            return False, f"MIME type inconsistente: esperado {expected_mime}, recebido {mime_type}"
    
    return True, None


def validate_file_size(file_size: int, max_size: int) -> Tuple[bool, Optional[str]]:
    """
    Valida tamanho do arquivo.
    
    Returns:
        (is_valid, error_message)
    """
    if file_size <= 0:
        return False, "Tamanho do arquivo deve ser maior que zero"
    
    if file_size > max_size:
        return False, f"Arquivo muito grande: {file_size} bytes (máximo: {max_size} bytes)"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitiza nome de arquivo."""
    # Remover caracteres perigosos
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limitar tamanho
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = Path(sanitized).stem[:max_length-10], Path(sanitized).suffix
        sanitized = f"{name}{ext}"
    
    return sanitized

