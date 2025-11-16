"""Script para configurar lifecycle policy no DigitalOcean Spaces."""
import sys
from pathlib import Path

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.spaces_lifecycle import lifecycle_service

if __name__ == "__main__":
    print("Configurando lifecycle policy no DigitalOcean Spaces...")
    print(f"Bucket: {lifecycle_service.bucket}")
    print(f"Prefix: vid-finger/")
    print(f"Expiração: 7 dias")
    
    success = lifecycle_service.setup_lifecycle_policy(expiration_days=7)
    
    if success:
        print("✓ Lifecycle policy configurada com sucesso!")
        
        # Verificar política atual
        rules = lifecycle_service.get_lifecycle_policy()
        if rules:
            print(f"\nPolíticas ativas: {len(rules)}")
            for rule in rules:
                print(f"  - {rule.get('ID')}: {rule.get('Status')}")
    else:
        print("✗ Falha ao configurar lifecycle policy")
        print("Verifique as credenciais e permissões do Spaces")
        sys.exit(1)

