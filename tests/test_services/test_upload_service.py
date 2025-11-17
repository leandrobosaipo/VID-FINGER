"""Testes para UploadService."""
from app.services.upload_service import UploadService
from app.config import settings


def test_init_upload_persists_mime_type(tmp_path, monkeypatch):
    """UploadService deve manter o mime_type no status do upload."""
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    
    upload_id, chunk_size, total_chunks = UploadService.init_upload(
        filename="sample-video.mp4",
        file_size=1024,
        mime_type="video/mp4"
    )
    
    status = UploadService.get_upload_status(upload_id)
    assert status is not None
    assert status["mime_type"] == "video/mp4"
    assert status["filename"] == "sample-video.mp4"
