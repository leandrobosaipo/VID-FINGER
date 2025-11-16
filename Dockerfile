FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependências Python
COPY requirements-api.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-api.txt

# Copiar código da aplicação
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/

# Criar diretórios de storage
RUN mkdir -p /app/storage/{uploads,original,reports,clean} && \
    chmod -R 755 /app/storage

# Criar usuário não-root para segurança
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expor porta
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

# Comando de start (usa PORT do ambiente ou 8000 como padrão)
# Executa migrações antes de iniciar o servidor
CMD ["sh", "-c", "alembic upgrade head && python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

