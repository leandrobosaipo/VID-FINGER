#!/usr/bin/env python3
"""Script de teste end-to-end completo."""
import sys
import time
import requests
import json
from pathlib import Path
from typing import Optional

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


def check_server():
    """Verifica se servidor está rodando."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor está rodando")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Servidor não está rodando. Inicie com: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar servidor: {e}")
        return False
    return False


def check_dependencies():
    """Verifica dependências via endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health/dependencies", timeout=10)
        if response.status_code == 200:
            data = response.json()
            deps = data.get("data", {}).get("dependencies", {})
            all_ok = data.get("data", {}).get("all_dependencies_ok", False)
            
            print("\n📋 Status de Dependências:")
            print(f"  FFmpeg: {'✅' if deps.get('ffmpeg', {}).get('available') else '❌'}")
            print(f"  Banco de dados: {'✅' if deps.get('database', {}).get('accessible') else '❌'}")
            print(f"  Redis: {'✅' if deps.get('redis', {}).get('available') else '⚠️  (opcional)'}")
            print(f"  Storage: {'✅' if deps.get('storage', {}).get('writable') else '❌'}")
            
            if not all_ok:
                print("\n⚠️  Algumas dependências não estão OK")
                return False
            return True
    except Exception as e:
        print(f"❌ Erro ao verificar dependências: {e}")
        return False


def upload_video(video_path: Path) -> Optional[str]:
    """Faz upload de vídeo e retorna analysis_id."""
    if not video_path.exists():
        print(f"❌ Arquivo não encontrado: {video_path}")
        return None
    
    print(f"\n📤 Fazendo upload de: {video_path.name}")
    print(f"   Tamanho: {video_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (video_path.name, f, 'video/mp4')}
            response = requests.post(
                f"{API_BASE}/upload/analyze",
                files=files,
                timeout=300
            )
        
        if response.status_code == 202:
            data = response.json()
            analysis_id = data.get("data", {}).get("analysis_id") or data.get("analysis_id")
            print(f"✅ Upload concluído!")
            print(f"   Analysis ID: {analysis_id}")
            print(f"   Status URL: {data.get('data', {}).get('status_url') or data.get('status_url')}")
            return analysis_id
        else:
            print(f"❌ Erro no upload: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro ao fazer upload: {e}")
        return None


def get_analysis_status(analysis_id: str) -> Optional[dict]:
    """Obtém status da análise."""
    try:
        response = requests.get(f"{API_BASE}/analysis/{analysis_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"⚠️  Análise não encontrada: {analysis_id}")
            return None
        else:
            print(f"❌ Erro ao obter status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")
        return None


def get_debug_status(analysis_id: str) -> Optional[dict]:
    """Obtém status detalhado de debug."""
    try:
        response = requests.get(f"{API_BASE}/debug/analysis/{analysis_id}/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"⚠️  Erro ao obter debug status: {e}")
        return None


def monitor_analysis(analysis_id: str, max_wait: int = 600):
    """Monitora análise até completar ou falhar."""
    print(f"\n🔍 Monitorando análise: {analysis_id}")
    print("   Aguardando processamento...")
    
    start_time = time.time()
    last_status = None
    last_progress = -1
    
    while True:
        elapsed = int(time.time() - start_time)
        if elapsed > max_wait:
            print(f"\n⏱️  Timeout após {max_wait}s")
            return False
        
        status_data = get_analysis_status(analysis_id)
        if not status_data:
            time.sleep(2)
            continue
        
        # Extrair dados da resposta
        if "data" in status_data:
            analysis = status_data["data"].get("analysis", {}) or status_data["data"]
        else:
            analysis = status_data
        
        current_status = analysis.get("status")
        progress = analysis.get("progress", 0)
        
        # Mostrar progresso apenas se mudou
        if current_status != last_status or progress != last_progress:
            status_emoji = {
                "pending": "⏳",
                "analyzing": "🔄",
                "completed": "✅",
                "failed": "❌"
            }
            emoji = status_emoji.get(current_status, "❓")
            print(f"   [{elapsed:4d}s] {emoji} Status: {current_status} | Progresso: {progress}%")
            
            # Mostrar etapas se disponível
            steps = analysis.get("steps", [])
            if steps:
                current_step = None
                for step in steps:
                    if step.get("status") == "running":
                        current_step = step.get("name")
                        break
                if current_step:
                    print(f"            → Etapa atual: {current_step}")
        
        last_status = current_status
        last_progress = progress
        
        # Verificar se completou ou falhou
        if current_status == "completed":
            print(f"\n✅ Análise concluída em {elapsed}s!")
            
            # Mostrar resultados
            print("\n📊 Resultados:")
            print(f"   Classificação: {analysis.get('classification', 'N/A')}")
            print(f"   Confiança: {analysis.get('confidence', 0):.2%}")
            
            # Verificar arquivos
            debug_data = get_debug_status(analysis_id)
            if debug_data and "data" in debug_data:
                files = debug_data["data"].get("files", {})
                file_ids = debug_data["data"].get("file_ids", {})
                
                print("\n📁 Arquivos gerados:")
                if file_ids.get("original_file_id"):
                    print("   ✅ Arquivo original")
                if file_ids.get("report_file_id"):
                    print("   ✅ Relatório JSON")
                else:
                    print("   ❌ Relatório JSON não gerado")
                if file_ids.get("clean_video_id"):
                    print("   ✅ Vídeo limpo")
                else:
                    print("   ⚠️  Vídeo limpo não gerado (pode ser normal se FFmpeg não disponível)")
            
            return True
        
        if current_status == "failed":
            print(f"\n❌ Análise falhou após {elapsed}s")
            error_msg = analysis.get("error_message", "Erro desconhecido")
            print(f"   Erro: {error_msg}")
            
            # Mostrar status detalhado
            debug_data = get_debug_status(analysis_id)
            if debug_data and "data" in debug_data:
                steps = debug_data["data"].get("steps", [])
                print("\n📋 Status das etapas:")
                for step in steps:
                    status_emoji = {
                        "pending": "⏳",
                        "running": "🔄",
                        "completed": "✅",
                        "failed": "❌"
                    }
                    emoji = status_emoji.get(step.get("status"), "❓")
                    print(f"   {emoji} {step.get('step_name')}: {step.get('status')} ({step.get('progress')}%)")
                    if step.get("error"):
                        print(f"      Erro: {step.get('error')}")
            
            return False
        
        time.sleep(2)


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: python scripts/test_end_to_end.py <caminho_do_video>")
        print("\nExemplo:")
        print("  python scripts/test_end_to_end.py /path/to/video.mp4")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    print("=" * 70)
    print("TESTE END-TO-END - VID-FINGER")
    print("=" * 70)
    
    # 1. Verificar servidor
    if not check_server():
        sys.exit(1)
    
    # 2. Verificar dependências
    if not check_dependencies():
        print("\n⚠️  Continuando mesmo com algumas dependências não OK...")
    
    # 3. Fazer upload
    analysis_id = upload_video(video_path)
    if not analysis_id:
        sys.exit(1)
    
    # 4. Monitorar processamento
    success = monitor_analysis(analysis_id)
    
    # 5. Resultado final
    print("\n" + "=" * 70)
    if success:
        print("✅ TESTE CONCLUÍDO COM SUCESSO")
        print(f"   Analysis ID: {analysis_id}")
        print(f"   Status URL: {API_BASE}/analysis/{analysis_id}")
        print(f"   Debug URL: {API_BASE}/debug/analysis/{analysis_id}/status")
    else:
        print("❌ TESTE FALHOU")
        print(f"   Analysis ID: {analysis_id}")
        print(f"   Debug URL: {API_BASE}/debug/analysis/{analysis_id}/status")
        print(f"   Retry URL: {API_BASE}/debug/analysis/{analysis_id}/retry")
    print("=" * 70)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

