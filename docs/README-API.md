# VID-FINGER API

API RESTful para o sistema forense de detecção de vídeos gerados por IA.

## Instalação

### Pré-requisitos

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- FFmpeg

### Instalação Local

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements-api.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações

# Executar migrações
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

### Docker Compose

```bash
# Iniciar todos os serviços
cd docker
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Parar serviços
docker-compose down
```

## Estrutura do Projeto

```
app/
├── api/v1/endpoints/    # Endpoints da API
├── core/                # Módulos de análise (reutilizados)
├── models/              # Modelos SQLAlchemy
├── services/            # Lógica de negócio
├── tasks/               # Tasks Celery
└── utils/               # Utilitários
```

## Endpoints Principais

### Upload

- `POST /api/v1/upload/init` - Inicia upload chunked
- `POST /api/v1/upload/chunk/{upload_id}` - Upload de chunk
- `POST /api/v1/upload/complete/{upload_id}` - Finaliza upload e inicia análise

### Análise

- `GET /api/v1/analysis/{analysis_id}` - Status da análise
- `GET /api/v1/analysis` - Lista análises
- `POST /api/v1/analysis/{analysis_id}/cancel` - Cancela análise

### Arquivos

- `GET /api/v1/files/{analysis_id}/{file_type}` - Download de arquivo
- `GET /api/v1/reports/{analysis_id}/report` - Download de relatório

## Documentação

Acesse `/docs` para documentação Swagger interativa.

## Desenvolvimento

```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Executar testes
pytest

# Formatar código
black app/

# Lint
ruff check app/
```

## Deploy

Ver documentação em `docs/PRD-VID-FINGER-V3.md` para instruções de deploy.

