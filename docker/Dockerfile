FROM python:3.11-slim

WORKDIR /app

# Instalar FFmpeg e dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Criar diretórios de storage
RUN mkdir -p /app/storage/{uploads,original,reports,clean}

# Expor porta
EXPOSE 8000

# Comando padrão
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

