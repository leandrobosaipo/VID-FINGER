# Configurar Serviços no EasyPanel - PostgreSQL e Redis

Este guia explica como criar e configurar os serviços PostgreSQL e Redis no EasyPanel para uso com a aplicação VID-FINGER API.

## Pré-requisitos

- Conta no EasyPanel configurada
- Acesso ao painel do EasyPanel

## Configurar PostgreSQL

### Passo 1: Criar Serviço PostgreSQL

1. No painel do EasyPanel, clique em **"New Service"** ou **"Novo Serviço"**
2. Selecione **"PostgreSQL"** na lista de serviços disponíveis
3. Configure:
   - **Service Name**: `vidfinger-postgres` (ou outro nome de sua escolha)
   - **Version**: Selecione uma versão estável (recomendado: 15 ou superior)
   - **Database Name**: `vidfinger` (ou outro nome de sua escolha)
   - **Username**: `postgres` (ou outro usuário de sua escolha)
   - **Password**: Gere uma senha forte e anote-a

### Passo 2: Obter Informações de Conexão

Após criar o serviço PostgreSQL:

1. Vá para a página do serviço PostgreSQL criado
2. Procure pela seção **"Connection"**, **"Conexão"** ou **"Connection String"**
3. Anote as seguintes informações:
   - **Host**: Exemplo: `postgres-service.easypanel.internal` ou IP
   - **Port**: Geralmente `5432`
   - **Database**: O nome do banco configurado (ex: `vidfinger`)
   - **Username**: O usuário configurado (ex: `postgres`)
   - **Password**: A senha que você configurou

### Passo 3: Montar URLs de Conexão

Com as informações acima, monte as URLs:

**DATABASE_URL** (assíncrona):
```
postgresql+asyncpg://[username]:[password]@[host]:[port]/[database]
```

**DATABASE_URL_SYNC** (síncrona):
```
postgresql://[username]:[password]@[host]:[port]/[database]
```

**Exemplo:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:minhasenha123@postgres-service.easypanel.internal:5432/vidfinger
DATABASE_URL_SYNC=postgresql://postgres:minhasenha123@postgres-service.easypanel.internal:5432/vidfinger
```

### Passo 4: Configurar como Variável de Ambiente

1. Vá para o projeto da aplicação VID-FINGER no EasyPanel
2. Vá para **"Environment Variables"** ou **"Variáveis de Ambiente"**
3. Adicione as duas variáveis:
   - `DATABASE_URL` com a URL assíncrona
   - `DATABASE_URL_SYNC` com a URL síncrona

## Configurar Redis

### Passo 1: Criar Serviço Redis

1. No painel do EasyPanel, clique em **"New Service"** ou **"Novo Serviço"**
2. Selecione **"Redis"** na lista de serviços disponíveis
3. Configure:
   - **Service Name**: `vidfinger-redis` (ou outro nome de sua escolha)
   - **Version**: Selecione uma versão estável (recomendado: 7 ou superior)

### Passo 2: Obter Informações de Conexão

Após criar o serviço Redis:

1. Vá para a página do serviço Redis criado
2. Procure pela seção **"Connection"**, **"Conexão"** ou **"Connection String"**
3. Anote as seguintes informações:
   - **Host**: Exemplo: `redis-service.easypanel.internal` ou IP
   - **Port**: Geralmente `6379`

### Passo 3: Montar URLs de Conexão

Com as informações acima, monte as URLs:

**REDIS_URL**:
```
redis://[host]:[port]/0
```

**CELERY_BROKER_URL** (geralmente igual ao REDIS_URL):
```
redis://[host]:[port]/0
```

**CELERY_RESULT_BACKEND** (geralmente igual ao REDIS_URL):
```
redis://[host]:[port]/0
```

**Exemplo:**
```bash
REDIS_URL=redis://redis-service.easypanel.internal:6379/0
CELERY_BROKER_URL=redis://redis-service.easypanel.internal:6379/0
CELERY_RESULT_BACKEND=redis://redis-service.easypanel.internal:6379/0
```

### Passo 4: Configurar como Variável de Ambiente

1. Vá para o projeto da aplicação VID-FINGER no EasyPanel
2. Vá para **"Environment Variables"** ou **"Variáveis de Ambiente"**
3. Adicione as três variáveis:
   - `REDIS_URL`
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`

## Configurar Serviços como Dependências (Opcional)

No EasyPanel, você pode configurar os serviços PostgreSQL e Redis como dependências da aplicação:

1. Vá para as configurações do projeto VID-FINGER
2. Procure por **"Dependencies"** ou **"Dependências"**
3. Adicione:
   - O serviço PostgreSQL criado
   - O serviço Redis criado

Isso garante que os serviços sejam iniciados antes da aplicação.

## Verificar Conexões

Após configurar tudo, você pode verificar se as conexões estão funcionando:

1. Faça deploy da aplicação
2. Acesse o endpoint: `https://seu-dominio.com/health/dependencies`
3. Verifique se retorna:
   ```json
   {
     "database": {
       "accessible": true
     },
     "redis": {
       "available": true
     }
   }
   ```

## Troubleshooting

### Erro: "Service not found" ou "Connection refused"

- Verifique se os serviços PostgreSQL e Redis estão rodando
- Verifique se os nomes dos serviços nas URLs estão corretos
- No EasyPanel, os serviços podem usar nomes internos como `postgres-service.easypanel.internal`
- Verifique se a porta está correta

### Erro: "Authentication failed"

- Verifique se o username e password estão corretos
- Verifique se o usuário tem permissões no banco de dados
- Tente recriar o serviço com novas credenciais

### Erro: "Database does not exist"

- Verifique se o nome do banco de dados na URL está correto
- Alguns serviços criam o banco automaticamente, outros não
- Verifique se o banco foi criado corretamente

### URLs de Conexão Internas vs Externas

- No EasyPanel, serviços geralmente usam nomes internos para comunicação
- Use os nomes internos fornecidos pelo EasyPanel (ex: `postgres-service.easypanel.internal`)
- Não use `localhost` ou `127.0.0.1` a menos que o serviço esteja no mesmo container

## Exemplo Completo

### Serviços Criados:
- PostgreSQL: `vidfinger-postgres`
- Redis: `vidfinger-redis`

### Variáveis de Ambiente Configuradas:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:senha123@vidfinger-postgres.easypanel.internal:5432/vidfinger
DATABASE_URL_SYNC=postgresql://postgres:senha123@vidfinger-postgres.easypanel.internal:5432/vidfinger
REDIS_URL=redis://vidfinger-redis.easypanel.internal:6379/0
CELERY_BROKER_URL=redis://vidfinger-redis.easypanel.internal:6379/0
CELERY_RESULT_BACKEND=redis://vidfinger-redis.easypanel.internal:6379/0
```

## Próximos Passos

Após configurar os serviços:
1. Configure as outras variáveis de ambiente (veja `VARIAVEIS_AMBIENTE.md`)
2. Faça deploy da aplicação
3. Verifique os logs para garantir que as conexões estão funcionando
4. Teste os endpoints da API

