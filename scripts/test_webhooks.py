#!/usr/bin/env python3
"""Script para testar webhooks por etapa."""
import sys
import os
import requests
import json
import time
from pathlib import Path

# Configuração
API_BASE_URL = "http://localhost:8000"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://webhook.site/unique-id")

def test_webhook_analysis(video_path: str, webhook_url: str):
    """Testa análise com webhook."""
    print("=" * 60)
    print("Teste de Webhooks por Etapa")
    print("=" * 60)
    print(f"API: {API_BASE_URL}")
    print(f"Webhook URL: {webhook_url}")
    print(f"Vídeo: {video_path}")
    print()
    
    # Verificar se arquivo existe
    if not Path(video_path).exists():
        print(f"❌ Arquivo não encontrado: {video_path}")
        return False
    
    # Enviar análise com webhook
    print("📤 Enviando análise com webhook...")
    try:
        with open(video_path, 'rb') as f:
            files = {'file': (Path(video_path).name, f, 'video/mp4')}
            data = {'webhook_url': webhook_url}
            
            response = requests.post(
                f"{API_BASE_URL}/api/v1/upload/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code == 202:
            result = response.json()
            analysis_id = result.get('analysis_id')
            print(f"✅ Análise iniciada: {analysis_id}")
            print()
            print("📊 Webhooks serão enviados para:")
            print(f"   {webhook_url}")
            print()
            print("🔍 Eventos esperados:")
            print("   1. analysis.started")
            print("   2. analysis.step.started (metadata_extraction)")
            print("   3. analysis.step.completed (metadata_extraction)")
            print("   4. analysis.step.started (prnu)")
            print("   5. analysis.step.completed (prnu)")
            print("   6. analysis.step.started (fft)")
            print("   7. analysis.step.completed (fft)")
            print("   8. analysis.step.started (classification)")
            print("   9. analysis.step.completed (classification)")
            print("   10. analysis.step.started (report_generation)")
            print("   11. analysis.step.completed (report_generation)")
            print("   12. analysis.step.started (cleaning)")
            print("   13. analysis.step.completed (cleaning)")
            print("   14. analysis.completed")
            print()
            print("💡 Acesse o webhook URL para ver os eventos em tempo real")
            print()
            print("📝 Para monitorar o status da análise:")
            print(f"   curl {API_BASE_URL}/api/v1/analysis/{analysis_id}")
            return True
        else:
            print(f"❌ Erro ao enviar análise: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_webhooks.py <caminho_do_video> [webhook_url]")
        print()
        print("Exemplo:")
        print("  python test_webhooks.py samples/test_video.mp4")
        print("  python test_webhooks.py samples/test_video.mp4 https://webhook.site/abc123")
        print()
        print("Ou defina WEBHOOK_URL como variável de ambiente:")
        print("  export WEBHOOK_URL=https://webhook.site/abc123")
        print("  python test_webhooks.py samples/test_video.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    webhook_url = sys.argv[2] if len(sys.argv) > 2 else WEBHOOK_URL
    
    success = test_webhook_analysis(video_path, webhook_url)
    sys.exit(0 if success else 1)

