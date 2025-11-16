"""Testes de endpoints de upload."""
import pytest
from fastapi.testclient import TestClient


def test_upload_init(client: TestClient):
    """Testa inicialização de upload."""
    response = client.post(
        "/api/v1/upload/init",
        json={
            "filename": "test.mp4",
            "file_size": 1000000,
            "mime_type": "video/mp4"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "upload_id" in data
    assert "chunk_size" in data
    assert "total_chunks" in data


def test_upload_init_invalid_file_type(client: TestClient):
    """Testa inicialização com tipo de arquivo inválido."""
    response = client.post(
        "/api/v1/upload/init",
        json={
            "filename": "test.exe",
            "file_size": 1000000,
            "mime_type": "application/x-msdownload"
        }
    )
    assert response.status_code == 400


def test_upload_init_file_too_large(client: TestClient):
    """Testa inicialização com arquivo muito grande."""
    response = client.post(
        "/api/v1/upload/init",
        json={
            "filename": "test.mp4",
            "file_size": 20000000000,  # 20GB
            "mime_type": "video/mp4"
        }
    )
    assert response.status_code == 400

