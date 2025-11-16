#!/usr/bin/env python3
"""Script para testar upload e processamento completo."""
import requests
import time
import json
import sys
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_upload_and_process(video_path: str):
    """Testa upload e aguarda processamento completo."""
    print(f"\n{'='*70}")
    print("TESTE DE UPLOAD E PROCESSAMENTO COMPLETO")
    print(f"{'='*70}\n")
    
    # Verificar se arquivo existe
    video_file = Path(video_path)
    if not video_file.exists():
        print(f"❌ Erro: Arquivo não encontrado: {video_path}")
        return False
    
    print(f"📁 Arquivo: {video_path}")
    print(f"📊 Tamanho: {video_file.stat().st_size / 1024 / 1024:.2f} MB\n")
    
    # 1. Fazer upload
    print("1️⃣ Fazendo upload do vídeo...")
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (video_file.name, f, 'video/mp4')}
            response = requests.post(
                f"{API_BASE}/api/v1/upload/analyze",
                files=files,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            analysis_id = result.get('analysis_id')
            print(f"✅ Upload concluído!")
            print(f"   Analysis ID: {analysis_id}")
            print(f"   Status URL: {result.get('status_url')}\n")
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return False
    
    # 2. Monitorar processamento
    print("2️⃣ Monitorando processamento...")
    max_wait = 600  # 10 minutos máximo
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{API_BASE}/api/v1/analysis/{analysis_id}",
                timeout=10
            )
            response.raise_for_status()
            analysis = response.json()
            
            status = analysis.get('status')
            progress = analysis.get('progress', 0)
            
            # Mostrar mudanças de status
            if status != last_status:
                print(f"\n   Status: {status} (Progresso: {progress}%)")
                last_status = status
                
                # Mostrar etapas
                steps = analysis.get('steps', [])
                for step in steps:
                    step_status = step.get('status')
                    step_name = step.get('name')
                    step_progress = step.get('progress', 0)
                    if step_status == 'running':
                        print(f"   ⏳ {step_name}: {step_progress}%")
                    elif step_status == 'completed':
                        print(f"   ✅ {step_name}: {step_progress}%")
                    elif step_status == 'failed':
                        print(f"   ❌ {step_name}: FALHOU")
            
            # Verificar se completou
            if status == 'completed':
                print(f"\n✅✅✅ PROCESSAMENTO CONCLUÍDO! ✅✅✅\n")
                print(f"   Classificação: {analysis.get('classification')}")
                print(f"   Confiança: {analysis.get('confidence', 0) * 100:.2f}%")
                print(f"   Relatório: {analysis.get('report_url', 'N/A')}")
                print(f"   Vídeo Limpo: {analysis.get('clean_video_url', 'N/A')}")
                return True
            
            # Verificar se falhou
            if status == 'failed':
                print(f"\n❌ PROCESSAMENTO FALHOU!\n")
                print(f"   Erro: {analysis.get('error_message', 'N/A')}")
                return False
            
            time.sleep(2)  # Aguardar 2 segundos antes de verificar novamente
            
        except Exception as e:
            print(f"⚠️ Erro ao verificar status: {e}")
            time.sleep(5)
    
    print(f"\n⏱️ Timeout: Processamento não completou em {max_wait}s")
    return False

def get_detailed_status(analysis_id: str):
    """Obtém status detalhado via endpoint de debug."""
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/debug/analysis/{analysis_id}/status",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao obter status detalhado: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/test_upload_complete.py <caminho_do_video>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    success = test_upload_and_process(video_path)
    
    if not success:
        print("\n⚠️ Processamento não completou. Verifique logs do servidor.")
        sys.exit(1)
    else:
        print("\n✅ Teste concluído com sucesso!")
        sys.exit(0)

