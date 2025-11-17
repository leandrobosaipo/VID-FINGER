# Variáveis de Ambiente - EasyPanel (Prontas para Copiar/Colar)

Este documento contém blocos de variáveis de ambiente **prontos para copiar e colar** diretamente no EasyPanel.

## ⚠️ IMPORTANTE: Correção Necessária

O `DATABASE_URL` **DEVE** usar `postgresql+asyncpg://` (não `postgresql://`) para conexões assíncronas.

---

## 📋 Bloco Completo - Copiar e Colar no EasyPanel

Copie **TODO** o bloco abaixo e cole nas variáveis de ambiente do EasyPanel:

```bash
# ============================================
# OBRIGATÓRIAS
# ============================================
# IMPORTANTE: não usar ?sslmode=disable com asyncpg
DATABASE_URL=postgresql+asyncpg://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital
# Se precisar desabilitar SSL, use o parâmetro apenas em DATABASE_URL_SYNC (psycopg2)
DATABASE_URL_SYNC=postgresql://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital?sslmode=disable
REDIS_URL=redis://default:ABF93E2D72196575E616CB41A49EE@criadordigital_redis:6379/0
CELERY_BROKER_URL=redis://default:ABF93E2D72196575E616CB41A49EE@criadordigital_redis:6379/0
CELERY_RESULT_BACKEND=redis://default:ABF93E2D72196575E616CB41A49EE@criadordigital_redis:6379/0

# ============================================
# RECOMENDADAS
# ============================================
API_BASE_URL=https://criadordigital-vidfinger.ujhifl.easypanel.host
SECRET_KEY=p9AqH7mZC0w3Jr4T8fV1sK2xN9bQ5eR6uP3tY0aL
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

---

## 🔍 O Que Foi Corrigido

### ❌ ANTES (Incorreto - driver síncrono e sslmode com asyncpg):
```
DATABASE_URL=postgresql://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital?sslmode=disable
```

### ✅ AGORA (Correto para asyncpg):
```
DATABASE_URL=postgresql+asyncpg://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital
```

**Diferenças**:
- Adicionado `+asyncpg` após `postgresql` para suportar conexões assíncronas.
- Removido `?sslmode=disable`, que causa erro com o driver asyncpg.

---

## 📝 Como Usar no EasyPanel

### Método 1: Copiar Bloco Completo

1. Copie **TODO** o bloco acima (do `# ============================================` até o final)
2. No EasyPanel, vá para **"Environment Variables"** do projeto
3. Se houver opção de **"Import"** ou **"Paste"**, cole o bloco completo
4. Se não houver, adicione cada variável manualmente

### Método 2: Adicionar Variáveis Individualmente

Se precisar adicionar uma por uma:

1. Vá para **"Environment Variables"** no EasyPanel
2. Para cada linha do bloco acima (sem os comentários `#`):
   - Clique em **"Add Variable"**
   - **Name**: parte antes do `=`
   - **Value**: parte depois do `=`
   - Salve

### Método 3: Editar Variável Existente

Se `DATABASE_URL` já existe:

1. Encontre `DATABASE_URL` na lista
2. Clique para editar
3. **Substitua** `postgresql://` por `postgresql+asyncpg://` no início
4. Salve

---

## ✅ Checklist de Verificação

Antes de fazer deploy, verifique:

- [ ] `DATABASE_URL` começa com `postgresql+asyncpg://` (não `postgresql://`)
- [ ] `DATABASE_URL_SYNC` começa com `postgresql://` (está correto)
- [ ] `REDIS_URL` está configurado
- [ ] `CELERY_BROKER_URL` está configurado
- [ ] `CELERY_RESULT_BACKEND` está configurado
- [ ] `API_BASE_URL` está com o domínio público correto
- [ ] `STORAGE_PATH` está configurado (ou `storage_path` se EasyPanel exigir minúscula)

---

## 🔧 Se EasyPanel Exigir Minúsculas

Se o EasyPanel não aceitar `STORAGE_PATH` e exigir `storage_path`:

1. Adicione ambas as variáveis:
   ```
   STORAGE_PATH=/app/storage
   storage_path=/app/storage
   ```

2. Ou use apenas a minúscula:
   ```
   storage_path=/app/storage
   ```

O código tentará usar ambas automaticamente.

---

## 🚀 Após Configurar

1. **Salve** todas as variáveis
2. **Faça novo deploy** no EasyPanel
3. **Aguarde** o build completar
4. **Verifique** os logs para garantir que não há erros
5. **Teste** o endpoint `/health/dependencies`

---

## 📞 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'psycopg2'"

**Solução**: O `psycopg2-binary` foi adicionado ao `requirements-api.txt`. Faça novo deploy.

### Erro: "Database connection failed"

**Solução**: 
- Verifique se `DATABASE_URL` usa `postgresql+asyncpg://`
- Verifique se as credenciais estão corretas
- Verifique se o serviço PostgreSQL está rodando

### Erro: "Migration failed"

**Solução**:
- Verifique se `DATABASE_URL_SYNC` está correto
- Verifique se `psycopg2-binary` foi instalado (deve estar no requirements-api.txt)

---

## 📚 Referências

- [Variáveis de Ambiente Completas](VARIAVEIS_AMBIENTE.md) - Documentação técnica completa
- [Configurar Serviços](SERVICOS_EASYPANEL.md) - Como criar PostgreSQL e Redis
- [Guia Deploy Completo](GUIA_DEPLOY_EASYPANEL.md) - Passo a passo completo
