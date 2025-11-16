#!/usr/bin/env python3
"""Script de teste completo da API local."""
import sys
import os
import requests
import json
from pathlib import Path

# Configuração
API_BASE_URL = "http://localhost:8000"
TEST_VIDEO = "/Users/leandrobosaipo/Downloads/andando-pela-cua.mp4"

def test_health():
    """Testa health check."""
    print("=" * 60)
    print("1. Testando Health Check")
    print("=" * 60)
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_upload_init(filename, file_size, mime_type):
    """Testa inicialização de upload."""
    print("\n" + "=" * 60)
    print("2. Testando Upload Init")
    print("=" * 60)
    response = requests.post(
        f"{API_BASE_URL}/api/v1/upload/init",
        json={
            "filename": filename,
            "file_size": file_size,
            "mime_type": mime_type
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Upload ID: {data['upload_id']}")
        print(f"Chunk Size: {data['chunk_size']}")
        print(f"Total Chunks: {data['total_chunks']}")
        return data
    else:
        print(f"Error: {response.text}")
        return None

def test_upload_chunks(upload_id, file_path, chunk_size):
    """Testa upload de chunks."""
    print("\n" + "=" * 60)
    print("3. Testando Upload de Chunks")
    print("=" * 60)
    
    with open(file_path, 'rb') as f:
        chunk_num = 0
        while True:
            chunk_data = f.read(chunk_size)
            if not chunk_data:
                break
            
            response = requests.post(
                f"{API_BASE_URL}/api/v1/upload/chunk/{upload_id}",
                data={"chunk_number": chunk_num},
                files={"chunk": (f"chunk_{chunk_num}.bin", chunk_data, "application/octet-stream")}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Chunk {chunk_num}: OK - Progress: {data['progress']:.1f}%")
            else:
                print(f"Chunk {chunk_num}: ERROR - {response.text[:200]}")
                return False
            
            chunk_num += 1
    
    return True

def test_complete_upload(upload_id, webhook_url=None):
    """Testa conclusão de upload."""
    print("\n" + "=" * 60)
    print("4. Testando Complete Upload")
    print("=" * 60)
    
    params = {}
    if webhook_url:
        params["webhook_url"] = webhook_url
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/upload/complete/{upload_id}",
        params=params
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Analysis ID: {data['analysis_id']}")
        print(f"Status: {data['status']}")
        print(f"Message: {data['message']}")
        return data['analysis_id']
    else:
        print(f"Error: {response.text[:500]}")
        return None

def test_get_analysis(analysis_id):
    """Testa obtenção de status da análise."""
    print("\n" + "=" * 60)
    print("5. Testando Get Analysis Status")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE_URL}/api/v1/analysis/{analysis_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Analysis ID: {data['id']}")
        print(f"Status: {data['status']}")
        print(f"Progress: {data['progress']}%")
        print(f"Current Step: {data.get('current_step', 'N/A')}")
        print(f"\nSteps:")
        for step in data.get('steps', []):
            print(f"  - {step['name']}: {step['status']} ({step['progress']}%)")
        return True
    else:
        print(f"Error: {response.text[:300]}")
        return False

def main():
    """Executa testes completos."""
    print("\n" + "=" * 60)
    print("VID-FINGER API - Teste Local Completo")
    print("=" * 60)
    
    # Verificar se servidor está rodando
    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("\nERRO: Servidor não está rodando!")
        print("Execute: uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Verificar arquivo de teste
    if not os.path.exists(TEST_VIDEO):
        print(f"\nERRO: Arquivo de teste não encontrado: {TEST_VIDEO}")
        sys.exit(1)
    
    file_size = os.path.getsize(TEST_VIDEO)
    filename = os.path.basename(TEST_VIDEO)
    mime_type = "video/mp4"
    
    print(f"\nArquivo de teste: {TEST_VIDEO}")
    print(f"Tamanho: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    # 1. Upload init
    upload_data = test_upload_init(filename, file_size, mime_type)
    if not upload_data:
        print("\nFalha no upload init. Abortando.")
        sys.exit(1)
    
    upload_id = upload_data['upload_id']
    chunk_size = upload_data['chunk_size']
    
    # 2. Upload chunks
    if not test_upload_chunks(upload_id, TEST_VIDEO, chunk_size):
        print("\nFalha no upload de chunks. Abortando.")
        sys.exit(1)
    
    # 3. Complete upload
    analysis_id = test_complete_upload(upload_id)
    if not analysis_id:
        print("\nFalha ao completar upload. Abortando.")
        sys.exit(1)
    
    # 4. Get analysis status
    test_get_analysis(analysis_id)
    
    print("\n" + "=" * 60)
    print("✓ Testes concluídos com sucesso!")
    print("=" * 60)
    print(f"\nAnalysis ID: {analysis_id}")
    print(f"Status da análise: http://localhost:8000/api/v1/analysis/{analysis_id}")
    print(f"Documentação: http://localhost:8000/docs")

if __name__ == "__main__":
    main()

