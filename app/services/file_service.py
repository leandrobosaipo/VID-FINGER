"""Serviço de gerenciamento de arquivos."""
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.config import settings
from app.models.file import FileType


class FileService:
    """Serviço para gerenciar arquivos."""
    
    @staticmethod
    def generate_storage_path(analysis_id: str, file_type: FileType) -> Path:
        """Gera caminho de armazenamento para arquivo."""
        base_path = Path(settings.STORAGE_PATH)
        
        if file_type == FileType.original:
            return base_path / "original" / str(analysis_id)
        elif file_type == FileType.report:
            return base_path / "reports" / str(analysis_id)
        elif file_type == FileType.clean_video:
            return base_path / "clean" / str(analysis_id)
        
        raise ValueError(f"Tipo de arquivo inválido: {file_type}")
    
    @staticmethod
    def generate_filename(original_filename: str, file_type: FileType) -> str:
        """Gera nome de arquivo único."""
        # Gerar hash único
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        
        # Manter extensão original
        ext = Path(original_filename).suffix
        
        if file_type == FileType.report:
            return f"report-{timestamp}-{unique_id}.json"
        elif file_type == FileType.clean_video:
            return f"clean-{timestamp}-{unique_id}{ext}"
        else:
            return f"{timestamp}-{unique_id}{ext}"
    
    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Calcula SHA256 do arquivo."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """Obtém tamanho do arquivo."""
        return file_path.stat().st_size

