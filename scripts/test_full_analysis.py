#!/usr/bin/env python3
"""Script para testar análise completa."""
import sys
import requests
import time
from pathlib import Path

API_URL = "http://localhost:8000"
TEST_VIDEO = "/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"

if len(sys.argv) > 1:
    TEST_VIDEO = sys.argv[1]

print("╔══════════════════════════════════════════════════════════════╗")
print("║     🧪 TESTE COMPLETO DE ANÁLISE                            ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()

# Verificar se arquivo existe
if not Path(TEST_VIDEO).exists():
    print(f"❌ Arquivo não encontrado: {TEST_VIDEO}")
    sys.exit(1)

print(f"📹 Arquivo: {TEST_VIDEO}")
print()

# 1. Upload e análise
print("1️⃣  Enviando arquivo...")
with open(TEST_VIDEO, 'rb') as f:
    files = {'file': (Path(TEST_VIDEO).name, f, 'video/mp4')}
    response = requests.post(f"{API_URL}/api/v1/upload/analyze", files=files)

if response.status_code != 202:
    print(f"❌ Erro no upload: {response.status_code}")
    print(response.text)
    sys.exit(1)

data = response.json()
analysis_id = data['analysis_id']
print(f"✅ Analysis ID: {analysis_id}")
print()

# 2. Monitorar processamento
print("2️⃣  Monitorando processamento...")
print()

start_time = time.time()
last_status = None

while True:
    response = requests.get(f"{API_URL}/api/v1/analysis/{analysis_id}")
    if response.status_code != 200:
        print(f"❌ Erro ao obter status: {response.status_code}")
        break
    
    data = response.json()
    status = data.get('status')
    progress = data.get('progress', 0)
    
    if status != last_status:
        elapsed = time.time() - start_time
        print(f"[{elapsed:.1f}s] Status: {status} ({progress}%)")
        last_status = status
    
    if status == 'completed':
        elapsed = time.time() - start_time
        print()
        print("="*60)
        print("✅ ANÁLISE COMPLETA!")
        print("="*60)
        print(f"Tempo total: {elapsed:.1f}s")
        print()
        print("📊 Resultados:")
        print(f"  Classification: {data.get('classification')}")
        print(f"  Confidence: {data.get('confidence')}")
        print()
        print("📁 Arquivos:")
        print(f"  Clean Video: {data.get('clean_video_url')}")
        print(f"  Report: {data.get('report_url')}")
        print(f"  Original: {data.get('original_video_url')}")
        break
    
    if status == 'failed':
        elapsed = time.time() - start_time
        print()
        print("="*60)
        print("❌ ANÁLISE FALHOU")
        print("="*60)
        print(f"Tempo: {elapsed:.1f}s")
        print(f"Erro: {data.get('error_message', 'N/A')}")
        break
    
    time.sleep(2)

