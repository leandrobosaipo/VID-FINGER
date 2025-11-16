# Variáveis de Ambiente - VID-FINGER API

Este documento lista todas as variáveis de ambiente necessárias para a aplicação VID-FINGER API.

## Variáveis Obrigatórias

Estas variáveis são **necessárias** para a aplicação funcionar:

### Banco de Dados PostgreSQL

```bash
# URL de conexão assíncrona (usada pela aplicação)
DATABASE_URL=postgresql+asyncpg://usuario:senha@host:porta/database

# URL de conexão síncrona (usada pelo Alembic para migrações)
DATABASE_URL_SYNC=postgresql://usuario:senha@host:porta/database
```

**Exemplo:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:minhasenha@postgres-service:5432/vidfinger
DATABASE_URL_SYNC=postgresql://postgres:minhasenha@postgres-service:5432/vidfinger
```

**Como obter no EasyPanel:**
1. Vá para o serviço PostgreSQL criado
2. Na seção "Connection" ou "Conexão", você encontrará:
   - Host
   - Porta (geralmente 5432)
   - Database name
   - Username
   - Password
3. Monte a URL no formato acima

### Redis

```bash
# URL do Redis (usado para cache e Celery)
REDIS_URL=redis://host:porta/0

# Broker do Celery (geralmente igual ao REDIS_URL)
CELERY_BROKER_URL=redis://host:porta/0

# Backend de resultados do Celery (geralmente igual ao REDIS_URL)
CELERY_RESULT_BACKEND=redis://host:porta/0
```

**Exemplo:**
```bash
REDIS_URL=redis://redis-service:6379/0
CELERY_BROKER_URL=redis://redis-service:6379/0
CELERY_RESULT_BACKEND=redis://redis-service:6379/0
```

**Como obter no EasyPanel:**
1. Vá para o serviço Redis criado
2. Na seção "Connection" ou "Conexão", você encontrará:
   - Host
   - Porta (geralmente 6379)
3. Monte a URL no formato `redis://host:porta/0`

## Variáveis Opcionais mas Recomendadas

### API Base URL

```bash
# URL pública da API (usado para gerar URLs completas de download)
API_BASE_URL=https://seu-dominio-publico.com
```

**Importante:** Configure esta variável com o domínio público fornecido pelo EasyPanel. Se não configurado, a API tentará inferir do Request, mas pode não funcionar corretamente em produção.

**Exemplo:**
```bash
API_BASE_URL=https://vid-finger.seudominio.com
```

### Segurança

```bash
# Chave secreta para segurança (gere uma chave aleatória forte)
SECRET_KEY=sua-chave-secreta-aleatoria-aqui

# Debug mode (sempre False em produção)
DEBUG=False
```

**Como gerar SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### DigitalOcean Spaces (CDN)

```bash
# Região do Spaces
DO_SPACES_REGION=nyc3

# Endpoint do Spaces
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# Nome do bucket
DO_SPACES_BUCKET=seu-bucket-name

# Access Key (obtenha no painel do DigitalOcean)
DO_SPACES_KEY=sua-access-key

# Secret Key (obtenha no painel do DigitalOcean)
DO_SPACES_SECRET=sua-secret-key

# Prefixo para organização dos arquivos
OUTPUT_PREFIX=vid-finger

# Habilitar upload automático para CDN após processamento
UPLOAD_TO_CDN=True
```

**Nota:** Se `UPLOAD_TO_CDN=False` ou as credenciais não estiverem configuradas, os arquivos serão armazenados apenas localmente.

### Storage Local

```bash
# Caminho para armazenamento local (dentro do container)
STORAGE_PATH=/app/storage

# Tamanho máximo de arquivo em bytes (10GB)
MAX_FILE_SIZE=10737418240

# Tamanho de chunk para upload em bytes (5MB)
CHUNK_SIZE=5242880
```

### Webhooks

```bash
# Timeout para webhooks em segundos
WEBHOOK_TIMEOUT=10

# Número de tentativas para webhooks
WEBHOOK_RETRY_ATTEMPTS=3
```

### FFmpeg

```bash
# Caminho do FFmpeg (geralmente /usr/bin/ffmpeg no container)
FFMPEG_PATH=/usr/bin/ffmpeg

# Caminho do FFprobe (geralmente /usr/bin/ffprobe no container)
FFPROBE_PATH=/usr/bin/ffprobe
```

### Aplicação

```bash
# Nome da aplicação
APP_NAME=VID-FINGER API

# Versão da aplicação
APP_VERSION=1.0.0
```

### JWT (Opcional - se usar autenticação)

```bash
# Chave secreta para JWT
JWT_SECRET_KEY=

# Algoritmo JWT
JWT_ALGORITHM=HS256

# Expiração do token em segundos
JWT_EXPIRATION=3600
```

## Variáveis Automáticas do EasyPanel

O EasyPanel fornece automaticamente:

- `PORT` - Porta na qual a aplicação deve escutar (geralmente 8000)
- Variáveis de conexão dos serviços (se configurados como dependências)

## Exemplo Completo de Configuração

```bash
# ============================================
# OBRIGATÓRIAS
# ============================================
DATABASE_URL=postgresql+asyncpg://postgres:senha123@postgres-service:5432/vidfinger
DATABASE_URL_SYNC=postgresql://postgres:senha123@postgres-service:5432/vidfinger
REDIS_URL=redis://redis-service:6379/0
CELERY_BROKER_URL=redis://redis-service:6379/0
CELERY_RESULT_BACKEND=redis://redis-service:6379/0

# ============================================
# RECOMENDADAS
# ============================================
API_BASE_URL=https://vid-finger.seudominio.com
SECRET_KEY=gerar-chave-aleatoria-aqui
DEBUG=False

# ============================================
# CDN (OPCIONAL)
# ============================================
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=cod5
DO_SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
DO_SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
OUTPUT_PREFIX=vid-finger
UPLOAD_TO_CDN=True

# ============================================
# STORAGE
# ============================================
STORAGE_PATH=/app/storage
MAX_FILE_SIZE=10737418240
CHUNK_SIZE=5242880

# ============================================
# APLICAÇÃO
# ============================================
APP_NAME=VID-FINGER API
APP_VERSION=1.0.0
```

## Validação

Após configurar as variáveis, você pode verificar se estão corretas acessando:

```
GET /health/dependencies
```

Este endpoint verifica:
- Acesso ao banco de dados
- Acesso ao Redis
- Disponibilidade do FFmpeg
- Permissões de escrita no storage

## Troubleshooting

### Erro: "Database connection failed"

- Verifique se `DATABASE_URL` está correto
- Verifique se o serviço PostgreSQL está rodando no EasyPanel
- Verifique se as credenciais estão corretas
- Verifique se o banco de dados existe

### Erro: "Redis connection failed"

- Verifique se `REDIS_URL` está correto
- Verifique se o serviço Redis está rodando no EasyPanel
- Verifique se a porta está correta (geralmente 6379)

### Erro: "FFmpeg not found"

- FFmpeg está incluído no Dockerfile
- Se ainda assim falhar, verifique `FFMPEG_PATH`

### URLs geradas com IP local

- Configure `API_BASE_URL` com o domínio público
- Reinicie a aplicação após configurar

