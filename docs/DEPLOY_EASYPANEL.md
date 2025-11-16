# Deploy no EasyPanel - VID-FINGER API

Este guia detalha como fazer deploy da aplicação VID-FINGER API no EasyPanel.

## Pré-requisitos

- Conta no EasyPanel configurada
- DigitalOcean Spaces configurado com bucket criado
- Credenciais do DigitalOcean Spaces (Access Key e Secret Key)
- Domínio configurado (opcional, mas recomendado)

## Passo 1: Criar Novo Projeto no EasyPanel

1. Acesse o painel do EasyPanel
2. Clique em "New Project" ou "Novo Projeto"
3. Selecione "Git Repository" como fonte
4. Configure:
   - **Repository URL**: `https://github.com/leandrobosaipo/VID-FINGER.git`
   - **Branch**: `main`
   - **Build Method**: **Dockerfile** (o EasyPanel detectará automaticamente o Dockerfile na raiz)

**Importante**: O projeto inclui um `Dockerfile` na raiz que será detectado automaticamente pelo EasyPanel. Não é necessário configurar Build Pack ou comandos de build manualmente - o Dockerfile já está configurado para:
- Instalar todas as dependências do sistema (FFmpeg, libpq-dev, gcc)
- Instalar dependências Python do `requirements-api.txt`
- Executar migrações do Alembic no start
- Usar a variável `PORT` fornecida pelo EasyPanel

## Passo 2: Configurar Banco de Dados PostgreSQL

1. No EasyPanel, vá para "Databases" ou "Bancos de Dados"
2. Crie um novo banco PostgreSQL
3. Anote as credenciais:
   - Host
   - Porta (geralmente 5432)
   - Database name
   - Username
   - Password

## Passo 3: Configurar Redis

1. No EasyPanel, vá para "Databases" ou "Bancos de Dados"
2. Crie uma instância Redis
3. Anote a URL de conexão (formato: `redis://host:port/0`)

## Passo 4: Configurar Variáveis de Ambiente

No projeto EasyPanel, vá para "Environment Variables" ou "Variáveis de Ambiente" e adicione:

### Configurações Básicas

```bash
APP_NAME=VID-FINGER API
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=gerar-uma-chave-secreta-aleatoria-aqui
```

### Banco de Dados

```bash
# Substitua com as credenciais do PostgreSQL criado no EasyPanel
DATABASE_URL=postgresql+asyncpg://usuario:senha@host:5432/vidfinger
DATABASE_URL_SYNC=postgresql://usuario:senha@host:5432/vidfinger
```

### Redis

```bash
# Substitua com a URL do Redis criado no EasyPanel
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/0
CELERY_RESULT_BACKEND=redis://host:6379/0
```

### Storage Local

```bash
STORAGE_PATH=/app/storage
MAX_FILE_SIZE=10737418240
CHUNK_SIZE=5242880
```

### DigitalOcean Spaces (CDN)

```bash
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=cod5
DO_SPACES_KEY=LZQAHCBDGFOLQR5UUHFR
DO_SPACES_SECRET=QVrgE+F/Rr0IDkZF5y0AdPtnnh2VMuPo8cCVrdxKzX4
OUTPUT_PREFIX=vid-finger
UPLOAD_TO_CDN=True
```

**IMPORTANTE**: Substitua as credenciais acima pelas suas credenciais reais do DigitalOcean Spaces.

### API Base URL (CRÍTICO para funcionar com endereço público)

```bash
# Configure com o domínio público da sua aplicação no EasyPanel
# Exemplo: https://vid-finger.seudominio.com
API_BASE_URL=https://seu-dominio-publico.com
```

**IMPORTANTE**: Esta variável é essencial para que a API funcione corretamente com endereço público. Configure com o domínio que o EasyPanel atribuir à sua aplicação.

### Webhooks (Opcional)

```bash
WEBHOOK_TIMEOUT=10
WEBHOOK_RETRY_ATTEMPTS=3
```

### FFmpeg

```bash
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe
```

## Passo 5: Configurar Build e Start Commands (Usando Dockerfile)

**Com Dockerfile, você NÃO precisa configurar Build e Start Commands manualmente!**

O Dockerfile já está configurado para:
- **Build**: Instala todas as dependências automaticamente
- **Start**: Executa migrações e inicia o servidor automaticamente

O EasyPanel detectará o Dockerfile e usará os comandos definidos nele:
- Migrações são executadas automaticamente no start: `alembic upgrade head`
- Servidor inicia automaticamente: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

**Nota**: A variável `PORT` é fornecida automaticamente pelo EasyPanel. O Dockerfile usa `${PORT:-8000}` como fallback caso a variável não esteja disponível.

## Passo 6: Configurar Porta e Domínio Público

1. No EasyPanel, vá para as configurações do projeto
2. Configure a porta: `8000` (ou a porta que o EasyPanel atribuir)
3. Configure o domínio público:
   - Se tiver domínio próprio: adicione o domínio nas configurações
   - Se usar domínio do EasyPanel: anote o domínio fornecido
4. **IMPORTANTE**: Atualize a variável `API_BASE_URL` com o domínio público configurado

## Passo 7: Verificar Dependências do Sistema

**Com Dockerfile, todas as dependências do sistema já estão incluídas!**

O Dockerfile instala automaticamente:
- ✅ Python 3.11
- ✅ FFmpeg e FFprobe
- ✅ libpq-dev (para PostgreSQL)
- ✅ gcc (compilador C)

Não é necessário verificar ou instalar manualmente - tudo está no Dockerfile.

## Passo 8: Deploy

1. Clique em "Deploy" ou "Deploy Now"
2. Aguarde o build completar
3. Verifique os logs para garantir que não há erros

## Passo 9: Verificar Saúde da Aplicação

Após o deploy, teste os endpoints:

1. **Health Check**:
   ```bash
   curl https://seu-dominio-publico.com/health
   ```

2. **Health Dependencies**:
   ```bash
   curl https://seu-dominio-publico.com/health/dependencies
   ```

3. **Documentação Swagger**:
   Acesse: `https://seu-dominio-publico.com/docs`

## Passo 10: Configurar DigitalOcean Spaces como Público

Para que os arquivos sejam acessíveis via URL pública:

1. Acesse o painel do DigitalOcean Spaces
2. Vá para o bucket `cod5`
3. Configure as permissões:
   - **File Listing**: Desabilitado (recomendado para segurança)
   - **CDN**: Habilitado (opcional, mas recomendado para performance)
4. Se usar CDN, anote a URL do CDN e atualize `DO_SPACES_ENDPOINT` se necessário

## Troubleshooting

### Problema: Aplicação não inicia

**Solução**:
- Verifique os logs no EasyPanel
- Confirme que todas as variáveis de ambiente estão configuradas
- Verifique se o banco de dados está acessível
- Confirme que a porta está configurada corretamente

### Problema: Erro de conexão com banco de dados

**Solução**:
- Verifique se o PostgreSQL está rodando
- Confirme que as credenciais em `DATABASE_URL` estão corretas
- Verifique se o banco de dados permite conexões do IP do EasyPanel

### Problema: Upload para CDN falha

**Solução**:
- Verifique se as credenciais do Spaces estão corretas
- Confirme que o bucket existe e está acessível
- Verifique os logs da aplicação para erros específicos

### Problema: URLs geradas com IP local ao invés de domínio público

**Solução**:
- Confirme que `API_BASE_URL` está configurado com o domínio público
- Reinicie a aplicação após configurar `API_BASE_URL`
- Verifique se o domínio está configurado corretamente no EasyPanel

### Problema: FFmpeg não encontrado

**Solução**:
- A funcionalidade de cleaning será pulada automaticamente
- Para habilitar, você pode precisar usar uma imagem Docker customizada
- Ou configurar FFmpeg no script de build (pode não funcionar dependendo do ambiente)

## Estrutura de Arquivos no Spaces

Os arquivos serão organizados no Spaces da seguinte forma:

```
vid-finger/
  analyses/
    {analysis_id}/
      original/
        {filename}
      report/
        {report_filename}.json
      clean_video/
        {clean_filename}
```

## Monitoramento

Após o deploy, monitore:

1. **Logs da aplicação** no EasyPanel
2. **Uso de recursos** (CPU, memória, disco)
3. **Uso do Spaces** (armazenamento e transferência)
4. **Saúde da aplicação** via endpoint `/health`

## Próximos Passos

- Configure webhooks para receber notificações de progresso
- Configure lifecycle policy no Spaces para limpeza automática de arquivos antigos
- Configure monitoramento e alertas
- Configure backup do banco de dados

## Documentação Adicional

Para informações mais detalhadas, consulte:

- **[Variáveis de Ambiente](VARIAVEIS_AMBIENTE.md)** - Lista completa de todas as variáveis necessárias
- **[Configurar Serviços EasyPanel](SERVICOS_EASYPANEL.md)** - Guia detalhado para configurar PostgreSQL e Redis
- **[Guia Passo a Passo Completo](GUIA_DEPLOY_EASYPANEL.md)** - Guia visual completo do deploy

## Referências

- [Documentação EasyPanel](https://easypanel.io/docs)
- [DigitalOcean Spaces Documentation](https://docs.digitalocean.com/products/spaces/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

