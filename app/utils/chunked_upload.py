"""Utilitários para upload em chunks."""
import hashlib
import os
import logging
from pathlib import Path
from typing import Dict, Optional
from app.config import settings
from app.utils.context import format_log_with_context

logger = logging.getLogger(__name__)


class ChunkedUploadManager:
    """Gerenciador de uploads em chunks."""
    
    def __init__(self, upload_id: str):
        """Inicializa gerenciador de upload."""
        self.upload_id = upload_id
        self.upload_dir = Path(settings.STORAGE_PATH) / "uploads" / upload_id
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_received: Dict[int, bool] = {}
        self.total_chunks: Optional[int] = None
        self.file_size: Optional[int] = None
        self.filename: Optional[str] = None
        self.mime_type: Optional[str] = None
    
    def init_upload(self, filename: str, file_size: int, total_chunks: int, mime_type: Optional[str] = None):
        """Inicializa upload."""
        self.filename = filename
        self.file_size = file_size
        self.total_chunks = total_chunks
        self.mime_type = mime_type
        
        logger.debug(
            format_log_with_context(
                "CHUNKED_UPLOAD",
                f"Inicializando: upload_id={self.upload_id}, dir={self.upload_dir}, filename={filename}, size={file_size}, chunks={total_chunks}",
                upload_id=self.upload_id
            )
        )
        
        # Salvar metadados
        metadata_file = self.upload_dir / "metadata.json"
        import json
        with open(metadata_file, "w") as f:
            json.dump({
                "filename": filename,
                "file_size": file_size,
                "total_chunks": total_chunks,
                "mime_type": mime_type
            }, f)
        
        logger.debug(
            format_log_with_context(
                "CHUNKED_UPLOAD",
                f"Metadados salvos: upload_id={self.upload_id}, metadata_file={metadata_file}",
                upload_id=self.upload_id
            )
        )
    
    def save_chunk(self, chunk_number: int, chunk_data: bytes) -> bool:
        """Salva chunk individual."""
        chunk_file = self.upload_dir / f"chunk_{chunk_number:05d}"
        chunk_size = len(chunk_data)
        
        logger.debug(
            format_log_with_context(
                "CHUNKED_UPLOAD",
                f"Salvando chunk: upload_id={self.upload_id}, chunk_number={chunk_number}, size={chunk_size}, file={chunk_file.name}",
                upload_id=self.upload_id
            )
        )
        
        try:
            with open(chunk_file, "wb") as f:
                f.write(chunk_data)
            
            self.chunks_received[chunk_number] = True
            
            logger.debug(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Chunk salvo: upload_id={self.upload_id}, chunk_number={chunk_number}, chunks_received={len(self.chunks_received)}/{self.total_chunks or '?'}",
                    upload_id=self.upload_id
                )
            )
            
            return True
        except Exception as e:
            logger.error(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Erro ao salvar chunk: upload_id={self.upload_id}, chunk_number={chunk_number}, error={str(e)}",
                    upload_id=self.upload_id
                ),
                exc_info=True
            )
            return False
    
    def has_chunk(self, chunk_number: int) -> bool:
        """Verifica se chunk foi recebido."""
        return chunk_number in self.chunks_received
    
    def get_received_chunks(self) -> int:
        """Retorna número de chunks recebidos."""
        return len(self.chunks_received)
    
    def get_progress(self) -> float:
        """Retorna progresso do upload (0-100)."""
        if not self.total_chunks:
            return 0.0
        return (len(self.chunks_received) / self.total_chunks) * 100.0
    
    def is_complete(self) -> bool:
        """Verifica se todos os chunks foram recebidos."""
        if not self.total_chunks:
            return False
        return len(self.chunks_received) == self.total_chunks
    
    def assemble_file(self, output_path: Path) -> Optional[str]:
        """Monta arquivo final a partir dos chunks."""
        if not self.is_complete():
            logger.warning(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Tentativa de montar arquivo incompleto: upload_id={self.upload_id}, chunks_received={len(self.chunks_received)}/{self.total_chunks or '?'}",
                    upload_id=self.upload_id
                )
            )
            return None
        
        logger.info(
            format_log_with_context(
                "CHUNKED_UPLOAD",
                f"Montando arquivo: upload_id={self.upload_id}, output_path={output_path}, chunks={self.total_chunks}",
                upload_id=self.upload_id
            )
        )
        
        try:
            # Ordenar chunks
            chunk_files = sorted([
                self.upload_dir / f"chunk_{i:05d}"
                for i in range(self.total_chunks)
            ])
            
            logger.debug(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Chunks encontrados: upload_id={self.upload_id}, count={len(chunk_files)}",
                    upload_id=self.upload_id
                )
            )
            
            # Montar arquivo
            total_bytes = 0
            with open(output_path, "wb") as outfile:
                for chunk_file in chunk_files:
                    if not chunk_file.exists():
                        logger.error(
                            format_log_with_context(
                                "CHUNKED_UPLOAD",
                                f"Chunk não encontrado: upload_id={self.upload_id}, chunk_file={chunk_file.name}",
                                upload_id=self.upload_id
                            )
                        )
                        return None
                    with open(chunk_file, "rb") as infile:
                        chunk_data = infile.read()
                        outfile.write(chunk_data)
                        total_bytes += len(chunk_data)
            
            logger.debug(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Arquivo montado: upload_id={self.upload_id}, total_bytes={total_bytes}",
                    upload_id=self.upload_id
                )
            )
            
            # Calcular checksum
            logger.debug(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Calculando checksum: upload_id={self.upload_id}",
                    upload_id=self.upload_id
                )
            )
            checksum = self._calculate_checksum(output_path)
            
            # Limpar chunks
            self.cleanup()
            
            logger.info(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Arquivo montado com sucesso: upload_id={self.upload_id}, output_path={output_path}, checksum=sha256:{checksum[:16]}...",
                    upload_id=self.upload_id
                )
            )
            
            return checksum
        except Exception as e:
            logger.error(
                format_log_with_context(
                    "CHUNKED_UPLOAD",
                    f"Erro ao montar arquivo: upload_id={self.upload_id}, error={str(e)}",
                    upload_id=self.upload_id
                ),
                exc_info=True
            )
            return None
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calcula SHA256 do arquivo."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def cleanup(self):
        """Remove chunks temporários."""
        try:
            import shutil
            shutil.rmtree(self.upload_dir)
        except Exception:
            pass
    
    @staticmethod
    def load_upload(upload_id: str) -> Optional["ChunkedUploadManager"]:
        """Carrega upload existente."""
        upload_dir = Path(settings.STORAGE_PATH) / "uploads" / upload_id
        if not upload_dir.exists():
            return None
        
        manager = ChunkedUploadManager(upload_id)
        
        # Carregar metadados
        metadata_file = upload_dir / "metadata.json"
        if metadata_file.exists():
            import json
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                manager.filename = metadata.get("filename")
                manager.file_size = metadata.get("file_size")
                manager.total_chunks = metadata.get("total_chunks")
                manager.mime_type = metadata.get("mime_type")
        
        # Carregar chunks recebidos
        for chunk_file in upload_dir.glob("chunk_*"):
            chunk_num = int(chunk_file.stem.split("_")[1])
            manager.chunks_received[chunk_num] = True
        
        return manager
