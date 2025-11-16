#!/usr/bin/env python3
"""Script de teste com upload para CDN."""
import sys
import os
import requests
import json
from pathlib import Path

# Configuração
API_BASE_URL = "http://localhost:8000"
TEST_VIDEO = sys.argv[1] if len(sys.argv) > 1 else "/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"

def test_upload_with_cdn():
    """Testa upload completo com CDN."""
    print("=" * 60)
    print("TESTE DE UPLOAD COM CDN (DigitalOcean Spaces)")
    print("=" * 60)
    
    # Verificar arquivo
    if not os.path.exists(TEST_VIDEO):
        print(f"ERRO: Arquivo não encontrado: {TEST_VIDEO}")
        return
    
    file_size = os.path.getsize(TEST_VIDEO)
    filename = os.path.basename(TEST_VIDEO)
    
    print(f"\nArquivo: {filename}")
    print(f"Tamanho: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
    
    # 1. Init upload
    print("\n1. Iniciando upload...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/upload/init",
        json={
            "filename": filename,
            "file_size": file_size,
            "mime_type": "video/mp4"
        }
    )
    
    if response.status_code != 201:
        print(f"ERRO: {response.text}")
        return
    
    data = response.json()
    upload_id = data['upload_id']
    chunk_size = data['chunk_size']
    print(f"✓ Upload ID: {upload_id}")
    print(f"  Chunks: {data['total_chunks']}")
    
    # 2. Upload chunks
    print("\n2. Fazendo upload de chunks...")
    with open(TEST_VIDEO, 'rb') as f:
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
                progress = response.json()['progress']
                print(f"  Chunk {chunk_num}: {progress:.1f}%")
            else:
                print(f"ERRO no chunk {chunk_num}: {response.text[:200]}")
                return
            
            chunk_num += 1
    
    # 3. Complete upload (com webhook de teste)
    print("\n3. Finalizando upload (com CDN e webhook)...")
    webhook_url = "https://webhook.site/unique-id"  # URL de teste
    response = requests.post(
        f"{API_BASE_URL}/api/v1/upload/complete/{upload_id}",
        params={"webhook_url": webhook_url}
    )
    
    if response.status_code != 200:
        print(f"ERRO: {response.text[:500]}")
        return
    
    data = response.json()
    analysis_id = data['analysis_id']
    print(f"✓ Análise criada: {analysis_id}")
    print(f"  Status: {data['status']}")
    
    # 4. Verificar status
    print("\n4. Verificando status da análise...")
    response = requests.get(f"{API_BASE_URL}/api/v1/analysis/{analysis_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data['status']}")
        print(f"  Progresso: {data['progress']}%")
        
        # Verificar se arquivo foi enviado para CDN
        print("\n5. Verificando upload para CDN...")
        # Buscar informações do arquivo no banco
        print("  (Verifique o log do servidor para ver se o upload para CDN foi feito)")
        print("  (Se UPLOAD_TO_CDN=True no .env, o arquivo deve estar no Spaces)")
    
    print("\n" + "=" * 60)
    print("✓ Teste concluído!")
    print("=" * 60)
    print(f"\nAnalysis ID: {analysis_id}")
    print(f"Swagger UI: {API_BASE_URL}/docs")
    print(f"Status: {API_BASE_URL}/api/v1/analysis/{analysis_id}")

if __name__ == "__main__":
    test_upload_with_cdn()

