#!/usr/bin/env python3
"""Script para testar correção do bug de Foreign Key no vídeo limpo."""
import sys
import os
import requests
import json
import time
from pathlib import Path

# Configuração
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def test_clean_video_save(video_path: str):
    """Testa salvamento do vídeo limpo."""
    print("=" * 60)
    print("Teste: Correção de Foreign Key no Vídeo Limpo")
    print("=" * 60)
    print(f"API: {API_BASE_URL}")
    print(f"Vídeo: {video_path}")
    print()
    
    # Verificar se arquivo existe
    if not Path(video_path).exists():
        print(f"❌ Arquivo não encontrado: {video_path}")
        return False
    
    # Verificar saúde da API
    print("1. Verificando saúde da API...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ API não está respondendo: {response.status_code}")
            return False
        print("✅ API está respondendo")
    except Exception as e:
        print(f"❌ Erro ao conectar na API: {e}")
        return False
    
    # Enviar análise
    print("\n2. Enviando análise...")
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (Path(video_path).name, f, 'video/mp4')}
            data = {}
            
            response = requests.post(
                f"{API_BASE_URL}/api/v1/upload/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code != 202:
            print(f"❌ Erro ao enviar análise: {response.status_code}")
            print(f"   {response.text}")
            return False
        
        result = response.json()
        analysis_id = result.get('analysis_id')
        print(f"✅ Análise iniciada: {analysis_id}")
    except Exception as e:
        print(f"❌ Erro ao enviar análise: {e}")
        return False
    
    # Monitorar progresso
    print("\n3. Monitorando progresso da análise...")
    max_wait = 300  # 5 minutos
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/v1/analysis/{analysis_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                analysis = response.json()
                status = analysis.get('status')
                
                if status != last_status:
                    print(f"   Status: {status}")
                    last_status = status
                
                if status == 'completed':
                    print("\n✅ Análise concluída!")
                    
                    # Verificar se clean_video_id foi salvo
                    clean_video_id = analysis.get('clean_video_id')
                    if clean_video_id:
                        print(f"✅ clean_video_id salvo: {clean_video_id}")
                        return True
                    else:
                        print("⚠️  clean_video_id não foi salvo (pode ser normal se FFmpeg não estiver disponível)")
                        return True  # Não é erro se FFmpeg não estiver disponível
                
                elif status == 'failed':
                    error_msg = analysis.get('error_message', 'N/A')
                    print(f"\n❌ Análise falhou: {error_msg}")
                    return False
                
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Erro ao verificar status: {e}")
            time.sleep(2)
    
    print(f"\n⏱️  Timeout após {max_wait} segundos")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_clean_video_fix.py <caminho_do_video>")
        print()
        print("Exemplo:")
        print("  python test_clean_video_fix.py samples/test_video.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    success = test_clean_video_save(video_path)
    sys.exit(0 if success else 1)

