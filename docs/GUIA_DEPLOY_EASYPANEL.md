# Guia Passo a Passo Completo - Deploy no EasyPanel

Este guia fornece instruções detalhadas passo a passo para fazer deploy da aplicação VID-FINGER API no EasyPanel usando Dockerfile.

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Passo 1: Criar Serviços PostgreSQL e Redis](#passo-1-criar-serviços-postgresql-e-redis)
3. [Passo 2: Criar Projeto no EasyPanel](#passo-2-criar-projeto-no-easypanel)
4. [Passo 3: Configurar Variáveis de Ambiente](#passo-3-configurar-variáveis-de-ambiente)
5. [Passo 4: Configurar Domínio e Porta](#passo-4-configurar-domínio-e-porta)
6. [Passo 5: Fazer Deploy](#passo-5-fazer-deploy)
7. [Passo 6: Verificar e Testar](#passo-6-verificar-e-testar)
8. [Troubleshooting](#troubleshooting)

---

## Pré-requisitos

Antes de começar, certifique-se de ter:

- ✅ Conta no EasyPanel configurada e acessível
- ✅ Credenciais do DigitalOcean Spaces (se usar CDN)
- ✅ Domínio configurado (opcional, mas recomendado)

---

## Passo 1: Criar Serviços PostgreSQL e Redis

### 1.1 Criar PostgreSQL

1. No painel do EasyPanel, clique em **"New Service"** ou **"Novo Serviço"**
2. Selecione **"PostgreSQL"**
3. Configure:
   - **Service Name**: `vidfinger-postgres`
   - **Version**: `15` ou superior
   - **Database Name**: `vidfinger`
   - **Username**: `postgres` (ou outro de sua escolha)
   - **Password**: Gere uma senha forte e **ANOTE-A**
4. Clique em **"Create"** ou **"Criar"**
5. Aguarde o serviço ser criado (pode levar alguns minutos)

### 1.2 Obter Informações de Conexão do PostgreSQL

1. Vá para a página do serviço `vidfinger-postgres` criado
2. Procure pela seção **"Connection"**, **"Conexão"** ou **"Connection String"**
3. **ANOTE** as seguintes informações:
   ```
   Host: [exemplo: vidfinger-postgres.easypanel.internal]
   Port: [geralmente 5432]
   Database: vidfinger
   Username: postgres
   Password: [a senha que você configurou]
   ```

### 1.3 Criar Redis

1. No painel do EasyPanel, clique em **"New Service"** ou **"Novo Serviço"**
2. Selecione **"Redis"**
3. Configure:
   - **Service Name**: `vidfinger-redis`
   - **Version**: `7` ou superior
4. Clique em **"Create"** ou **"Criar"**
5. Aguarde o serviço ser criado

### 1.4 Obter Informações de Conexão do Redis

1. Vá para a página do serviço `vidfinger-redis` criado
2. Procure pela seção **"Connection"** ou **"Conexão"**
3. **ANOTE** as seguintes informações:
   ```
   Host: [exemplo: vidfinger-redis.easypanel.internal]
   Port: [geralmente 6379]
   ```

---

## Passo 2: Criar Projeto no EasyPanel

### 2.1 Criar Novo Projeto

1. No painel do EasyPanel, clique em **"New Project"** ou **"Novo Projeto"**
2. Selecione **"Git Repository"** como fonte
3. Configure:
   - **Repository URL**: `https://github.com/leandrobosaipo/VID-FINGER.git`
   - **Branch**: `main`
   - **Build Method**: **Dockerfile** (será detectado automaticamente)
4. Clique em **"Create"** ou **"Criar"**

### 2.2 Verificar Detecção do Dockerfile

O EasyPanel deve detectar automaticamente o `Dockerfile` na raiz do repositório. Você verá algo como:

```
Build Method: Dockerfile detected
```

Se não detectar, verifique se o arquivo `Dockerfile` está na raiz do repositório GitHub.

---

## Passo 3: Configurar Variáveis de Ambiente

### 3.1 Acessar Configurações de Variáveis

1. No projeto criado, vá para **"Environment Variables"** ou **"Variáveis de Ambiente"**
2. Clique em **"Add Variable"** ou **"Adicionar Variável"**

### 3.2 Configurar Variáveis Obrigatórias

Adicione as seguintes variáveis **uma por uma**:

#### Banco de Dados PostgreSQL

**DATABASE_URL**:
```
postgresql+asyncpg://[username]:[password]@[host]:[port]/[database]
```

**Exemplo** (substitua com seus valores reais):
```
DATABASE_URL=postgresql+asyncpg://postgres:minhasenha123@vidfinger-postgres.easypanel.internal:5432/vidfinger
```

**DATABASE_URL_SYNC**:
```
postgresql://[username]:[password]@[host]:[port]/[database]
```

**Exemplo**:
```
DATABASE_URL_SYNC=postgresql://postgres:minhasenha123@vidfinger-postgres.easypanel.internal:5432/vidfinger
```

#### Redis

**REDIS_URL**:
```
redis://[host]:[port]/0
```

**Exemplo**:
```
REDIS_URL=redis://vidfinger-redis.easypanel.internal:6379/0
```

**CELERY_BROKER_URL** (geralmente igual ao REDIS_URL):
```
CELERY_BROKER_URL=redis://vidfinger-redis.easypanel.internal:6379/0
```

**CELERY_RESULT_BACKEND** (geralmente igual ao REDIS_URL):
```
CELERY_RESULT_BACKEND=redis://vidfinger-redis.easypanel.internal:6379/0
```

### 3.3 Configurar Variáveis Recomendadas

#### API Base URL

**IMPORTANTE**: Configure esta variável **APÓS** configurar o domínio público (Passo 4).

```
API_BASE_URL=https://seu-dominio-publico.com
```

Por enquanto, você pode deixar vazio ou usar um placeholder. Atualizaremos depois.

#### Segurança

```
SECRET_KEY=[gere uma chave aleatória]
DEBUG=False
```

**Como gerar SECRET_KEY**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Aplicação

```
APP_NAME=VID-FINGER API
APP_VERSION=1.0.0
```

#### Storage

```
STORAGE_PATH=/app/storage
MAX_FILE_SIZE=10737418240
CHUNK_SIZE=5242880
```

#### FFmpeg (já configurado no Dockerfile, mas pode especificar)

```
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe
```

### 3.4 Configurar Variáveis Opcionais (CDN)

Se você quiser usar DigitalOcean Spaces para CDN:

```
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=cod5
DO_SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
DO_SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
OUTPUT_PREFIX=vid-finger
UPLOAD_TO_CDN=True
```

**Nota**: Substitua as credenciais acima pelas suas credenciais reais do DigitalOcean Spaces.

---

## Passo 4: Configurar Domínio e Porta

### 4.1 Configurar Porta

1. No projeto, vá para **"Settings"** ou **"Configurações"**
2. Procure por **"Port"** ou **"Porta"**
3. Configure: `8000` (ou deixe o padrão do EasyPanel)
4. **Anote** a porta configurada

### 4.2 Configurar Domínio Público

1. No projeto, vá para **"Domains"** ou **"Domínios"**
2. Você pode:
   - **Opção A**: Usar o domínio fornecido pelo EasyPanel (ex: `vid-finger.easypanel.app`)
   - **Opção B**: Adicionar seu próprio domínio personalizado

3. **Anote** o domínio público configurado

### 4.3 Atualizar API_BASE_URL

1. Volte para **"Environment Variables"**
2. Encontre a variável `API_BASE_URL`
3. Atualize com o domínio público que você configurou:
   ```
   API_BASE_URL=https://vid-finger.easypanel.app
   ```
   (ou seu domínio personalizado)

---

## Passo 5: Fazer Deploy

### 5.1 Iniciar Deploy

1. No projeto, clique em **"Deploy"** ou **"Deploy Now"**
2. Aguarde o build iniciar

### 5.2 Monitorar Build

1. Vá para a aba **"Logs"** ou **"Build Logs"**
2. Você verá o processo de build:
   - Clonando repositório
   - Construindo imagem Docker
   - Instalando dependências
   - Executando migrações (no start)

### 5.3 Aguardar Conclusão

O build pode levar alguns minutos. Aguarde até ver:
```
Build completed successfully
Application started
```

---

## Passo 6: Verificar e Testar

### 6.1 Verificar Health Check

1. Acesse: `https://seu-dominio-publico.com/health`
2. Você deve ver:
   ```json
   {
     "status": "healthy",
     "version": "1.0.0"
   }
   ```

### 6.2 Verificar Dependências

1. Acesse: `https://seu-dominio-publico.com/health/dependencies`
2. Você deve ver:
   ```json
   {
     "all_dependencies_ok": true,
     "dependencies": {
       "database": { "accessible": true },
       "redis": { "available": true },
       "ffmpeg": { "available": true }
     }
   }
   ```

### 6.3 Verificar Documentação Swagger

1. Acesse: `https://seu-dominio-publico.com/docs`
2. Você deve ver a documentação interativa da API

### 6.4 Testar Upload

1. Use a interface Swagger ou um cliente HTTP
2. Faça um POST para `/api/v1/upload/analyze`
3. Envie um arquivo de vídeo
4. Verifique se a análise inicia corretamente

---

## Troubleshooting

### Erro: "No start command could be found"

**Solução**: O Dockerfile deve estar na raiz do repositório. Verifique se o arquivo `Dockerfile` existe e foi commitado.

### Erro: "Database connection failed"

**Solução**:
1. Verifique se o serviço PostgreSQL está rodando
2. Verifique se `DATABASE_URL` está correto
3. Verifique se está usando o host interno do EasyPanel (ex: `vidfinger-postgres.easypanel.internal`)
4. Verifique se as credenciais estão corretas

### Erro: "Redis connection failed"

**Solução**:
1. Verifique se o serviço Redis está rodando
2. Verifique se `REDIS_URL` está correto
3. Verifique se está usando o host interno do EasyPanel

### Erro: "Migration failed"

**Solução**:
1. Verifique se `DATABASE_URL_SYNC` está correto
2. Verifique se o banco de dados existe
3. Verifique se o usuário tem permissões para criar tabelas

### Aplicação não responde

**Solução**:
1. Verifique os logs no EasyPanel
2. Verifique se a porta está configurada corretamente
3. Verifique se o domínio está apontando para o serviço correto

### URLs geradas com IP local

**Solução**:
1. Configure `API_BASE_URL` com o domínio público
2. Reinicie a aplicação após configurar
3. Verifique se o domínio está configurado corretamente

---

## Checklist Final

Antes de considerar o deploy completo, verifique:

- [ ] PostgreSQL criado e rodando
- [ ] Redis criado e rodando
- [ ] Todas as variáveis de ambiente configuradas
- [ ] `API_BASE_URL` configurado com domínio público
- [ ] Domínio público configurado e funcionando
- [ ] Health check retorna `healthy`
- [ ] Dependencies check retorna `all_dependencies_ok: true`
- [ ] Swagger docs acessível
- [ ] Upload de vídeo funcionando

---

## Próximos Passos

Após o deploy bem-sucedido:

1. **Monitorar Logs**: Acompanhe os logs da aplicação regularmente
2. **Configurar Backup**: Configure backup automático do PostgreSQL
3. **Configurar Alertas**: Configure alertas para monitoramento
4. **Otimizar Performance**: Ajuste recursos conforme necessário
5. **Configurar CDN**: Se usar DigitalOcean Spaces, configure CDN para melhor performance

---

## Documentação Adicional

- **[Variáveis de Ambiente](VARIAVEIS_AMBIENTE.md)** - Referência completa de variáveis
- **[Configurar Serviços](SERVICOS_EASYPANEL.md)** - Guia detalhado de PostgreSQL e Redis
- **[Deploy EasyPanel](DEPLOY_EASYPANEL.md)** - Documentação técnica completa

---

## Suporte

Se encontrar problemas:

1. Verifique os logs no EasyPanel
2. Consulte a documentação adicional acima
3. Verifique o endpoint `/health/dependencies` para diagnóstico
4. Revise as configurações de variáveis de ambiente

