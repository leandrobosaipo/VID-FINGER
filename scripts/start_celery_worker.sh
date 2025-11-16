#!/bin/bash
# Script para iniciar Celery worker

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🚀 Iniciando Celery Worker                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar se Redis está rodando
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis não está rodando!"
    echo "   Inicie Redis com: redis-server"
    echo "   Ou instale: brew install redis (macOS)"
    exit 1
fi

echo "✅ Redis está rodando"
echo ""

# Ativar ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Ambiente virtual ativado"
else
    echo "⚠️  Ambiente virtual não encontrado"
fi

echo ""
echo "🔄 Iniciando Celery worker..."
echo "   Broker: redis://localhost:6379/0"
echo ""

# Iniciar Celery worker
celery -A app.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=solo \
    --without-gossip \
    --without-mingle \
    --without-heartbeat

