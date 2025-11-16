#!/usr/bin/env python3
"""Script para monitorar processamento de análises."""
import sys
import time
import requests
from datetime import datetime
from typing import Optional

API_BASE_URL = "http://localhost:8000"


def get_analysis_status(analysis_id: str) -> Optional[dict]:
    """Obtém status da análise."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/analysis/{analysis_id}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erro ao obter status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None


def format_status(status: str) -> str:
    """Formata status com emoji."""
    status_map = {
        "pending": "⏳ Pending",
        "running": "🔄 Running",
        "completed": "✅ Completed",
        "failed": "❌ Failed"
    }
    return status_map.get(status, status)


def monitor_analysis(analysis_id: str, interval: int = 2):
    """Monitora análise até completar."""
    print(f"\n{'='*60}")
    print(f"🔍 Monitorando Análise: {analysis_id}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    last_status = None
    
    while True:
        data = get_analysis_status(analysis_id)
        
        if not data:
            print("❌ Não foi possível obter status. Tentando novamente...")
            time.sleep(interval)
            continue
        
        status = data.get("status", "unknown")
        progress = data.get("progress", 0)
        current_step = data.get("current_step")
        steps = data.get("steps", [])
        
        # Mostrar mudanças de status
        if status != last_status:
            elapsed = time.time() - start_time
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {format_status(status)} ({elapsed:.1f}s)")
            last_status = status
        
        # Mostrar progresso
        if progress > 0:
            bar_length = 30
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"   Progresso: [{bar}] {progress}%", end="\r")
        
        # Mostrar step atual
        if current_step:
            print(f"\n   📍 Etapa atual: {current_step}")
        
        # Mostrar detalhes dos steps
        if steps:
            print("\n   📊 Etapas:")
            for step in steps:
                step_name = step.get("name", "unknown")
                step_status = step.get("status", "pending")
                step_progress = step.get("progress", 0)
                
                status_icon = {
                    "pending": "⏳",
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌"
                }.get(step_status, "❓")
                
                print(f"      {status_icon} {step_name}: {step_progress}%")
        
        # Verificar se completou ou falhou
        if status == "completed":
            elapsed = time.time() - start_time
            print(f"\n\n{'='*60}")
            print(f"✅ Análise Completa! Tempo total: {elapsed:.1f}s")
            print(f"{'='*60}\n")
            
            # Mostrar links
            clean_video_url = data.get("clean_video_url")
            report_url = data.get("report_url")
            original_video_url = data.get("original_video_url")
            
            if clean_video_url:
                print(f"📹 Vídeo Limpo: {clean_video_url}")
            if report_url:
                print(f"📄 Relatório: {report_url}")
            if original_video_url:
                print(f"🎬 Original: {original_video_url}")
            
            classification = data.get("classification")
            confidence = data.get("confidence")
            if classification:
                print(f"\n🎯 Classificação: {classification}")
                if confidence:
                    print(f"   Confiança: {confidence*100:.1f}%")
            
            break
        
        if status == "failed":
            elapsed = time.time() - start_time
            error_message = data.get("error_message", "Erro desconhecido")
            print(f"\n\n{'='*60}")
            print(f"❌ Análise Falhou após {elapsed:.1f}s")
            print(f"   Erro: {error_message}")
            print(f"{'='*60}\n")
            break
        
        time.sleep(interval)


def list_pending_analyses():
    """Lista análises pendentes."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/analysis?page=1&page_size=10")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            pending = [item for item in items if item.get("status") in ["pending", "running"]]
            
            if pending:
                print(f"\n📋 Encontradas {len(pending)} análises pendentes/em execução:\n")
                for item in pending:
                    print(f"   • {item['id']} - {format_status(item['status'])}")
                return [item['id'] for item in pending]
            else:
                print("\n✅ Nenhuma análise pendente encontrada.")
                return []
        else:
            print(f"❌ Erro ao listar análises: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return []


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python scripts/monitor_analysis.py <analysis_id>  # Monitorar análise específica")
        print("  python scripts/monitor_analysis.py --list         # Listar análises pendentes")
        print("  python scripts/monitor_analysis.py --all           # Monitorar todas pendentes")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_pending_analyses()
    elif sys.argv[1] == "--all":
        pending_ids = list_pending_analyses()
        if pending_ids:
            print("\n⚠️  Monitorando todas as análises pendentes...")
            for analysis_id in pending_ids:
                monitor_analysis(analysis_id)
                print("\n" + "-"*60 + "\n")
    else:
        analysis_id = sys.argv[1]
        monitor_analysis(analysis_id)


if __name__ == "__main__":
    main()

