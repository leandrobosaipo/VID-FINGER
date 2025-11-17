"""Serviço de gerenciamento de uploads."""
import uuid
from pathlib import Path
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.chunked_upload import ChunkedUploadManager
from app.utils.validators import validate_file_type, validate_file_size, sanitize_filename
from app.config import settings


class UploadService:
    """Serviço para gerenciar uploads."""
    
    @staticmethod
    def init_upload(
        filename: str,
        file_size: int,
        mime_type: str
    ) -> Tuple[str, int, int]:
        """
        Inicializa upload chunked.
        
        Args:
            filename: Nome do arquivo
            mime_type: Tipo MIME
            
        Returns:
            (upload_id, chunk_size, total_chunks)
        """
        # Validar tipo de arquivo
        is_valid, error = validate_file_type(filename, mime_type)
        if not is_valid:
            raise ValueError(error)
        
        # Validar tamanho
        is_valid, error = validate_file_size(file_size, settings.MAX_FILE_SIZE)
        if not is_valid:
            raise ValueError(error)
        
        # Gerar upload ID
        upload_id = str(uuid.uuid4())
        
        # Calcular chunks
        chunk_size = settings.CHUNK_SIZE
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # Inicializar manager
        manager = ChunkedUploadManager(upload_id)
        manager.init_upload(filename, file_size, total_chunks, mime_type)
        
        return upload_id, chunk_size, total_chunks
    
    @staticmethod
    def save_chunk(upload_id: str, chunk_number: int, chunk_data: bytes) -> Tuple[int, float]:
        """
        Salva chunk individual.
        
        Returns:
            (chunks_received, progress)
        """
        manager = ChunkedUploadManager.load_upload(upload_id)
        if not manager:
            raise ValueError(f"Upload não encontrado: {upload_id}")
        
        # Validar número do chunk
        if manager.total_chunks and chunk_number >= manager.total_chunks:
            raise ValueError(f"Chunk número inválido: {chunk_number}")
        
        # Salvar chunk
        success = manager.save_chunk(chunk_number, chunk_data)
        if not success:
            raise RuntimeError("Falha ao salvar chunk")
        
        return manager.get_received_chunks(), manager.get_progress()
    
    @staticmethod
    def complete_upload(upload_id: str, output_dir: Path) -> Tuple[Path, str]:
        """
        Finaliza upload e monta arquivo.
        
        Returns:
            (file_path, checksum)
        """
        manager = ChunkedUploadManager.load_upload(upload_id)
        if not manager:
            raise ValueError(f"Upload não encontrado: {upload_id}")
        
        if not manager.is_complete():
            raise ValueError("Upload incompleto")
        
        # Criar diretório de saída
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitizar nome do arquivo
        sanitized_name = sanitize_filename(manager.filename)
        output_path = output_dir / sanitized_name
        
        # Montar arquivo
        checksum = manager.assemble_file(output_path)
        if not checksum:
            raise RuntimeError("Falha ao montar arquivo")
        
        return output_path, checksum
    
    @staticmethod
    def get_upload_status(upload_id: str) -> Optional[dict]:
        """Obtém status do upload."""
        manager = ChunkedUploadManager.load_upload(upload_id)
        if not manager:
            return None
        
        return {
            "upload_id": upload_id,
            "filename": manager.filename,
            "file_size": manager.file_size,
            "mime_type": manager.mime_type,
            "total_chunks": manager.total_chunks,
            "chunks_received": manager.get_received_chunks(),
            "progress": manager.get_progress(),
            "is_complete": manager.is_complete()
        }
    
    @staticmethod
    def upload_file_direct(
        file_content: bytes,
        filename: str,
        mime_type: str
    ) -> str:
        """
        Faz upload direto de arquivo completo.
        
        Processa chunks internamente se necessário.
        Retorna upload_id para uso interno.
        """
        file_size = len(file_content)
        
        # Validar tipo de arquivo
        is_valid, error = validate_file_type(filename, mime_type)
        if not is_valid:
            raise ValueError(error)
        
        # Validar tamanho
        is_valid, error = validate_file_size(file_size, settings.MAX_FILE_SIZE)
        if not is_valid:
            raise ValueError(error)
        
        # Gerar upload ID
        upload_id = str(uuid.uuid4())
        
        # Calcular chunks
        chunk_size = settings.CHUNK_SIZE
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # Inicializar manager
        manager = ChunkedUploadManager(upload_id)
        manager.init_upload(filename, file_size, total_chunks, mime_type)
        
        # Salvar arquivo em chunks se necessário
        if file_size <= chunk_size:
            # Arquivo cabe em um chunk, salvar diretamente
            manager.save_chunk(0, file_content)
        else:
            # Arquivo grande - salvar em múltiplos chunks
            for i in range(0, file_size, chunk_size):
                chunk_data = file_content[i:i + chunk_size]
                chunk_number = i // chunk_size
                manager.save_chunk(chunk_number, chunk_data)
        
        return upload_id
