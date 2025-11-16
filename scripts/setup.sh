#!/bin/bash
# Script de setup inicial

set -e

echo "🚀 Configurando VID-FINGER API..."

# Criar diretórios necessários
mkdir -p storage/{uploads,original,reports,clean}

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "📝 Criando .env a partir de .env.example..."
    cp .env.example .env
    echo "⚠️  Por favor, edite .env com suas configurações"
fi

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements-api.txt

# Executar migrações
echo "🗄️  Executando migrações..."
alembic upgrade head

echo "✅ Setup concluído!"
echo ""
echo "Para iniciar o servidor:"
echo "  uvicorn app.main:app --reload"

