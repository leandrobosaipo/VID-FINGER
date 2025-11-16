# Instruções Pós-Deploy - Correção de Variáveis no EasyPanel

Este guia explica exatamente o que fazer no EasyPanel após o código ser atualizado no GitHub.

## ✅ O Que Foi Corrigido no Código

1. ✅ Adicionado `psycopg2-binary>=2.9.9` ao `requirements-api.txt`
2. ✅ Criado documento com variáveis prontas para copiar/colar

## 🔧 O Que Você Precisa Fazer no EasyPanel

### Passo 1: Aguardar Deploy Automático (ou Fazer Manual)

O EasyPanel pode fazer deploy automático quando detectar mudanças no GitHub. Se não fizer automaticamente:

1. Vá para o projeto no EasyPanel
2. Clique em **"Deploy"** ou **"Redeploy"**
3. Aguarde o build completar

### Passo 2: Corrigir Variável DATABASE_URL

**IMPORTANTE**: Esta é a correção **mais crítica**!

1. No EasyPanel, vá para **"Environment Variables"** ou **"Variáveis de Ambiente"**
2. Encontre a variável `DATABASE_URL`
3. Clique para **editar**
4. **Substitua** o início da URL:

   **DE:**
   ```
   postgresql://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital?sslmode=disable
   ```

   **PARA:**
   ```
   postgresql+asyncpg://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital?sslmode=disable
   ```

   **Ou simplesmente**: Adicione `+asyncpg` após `postgresql`:
   ```
   postgresql+asyncpg://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital?sslmode=disable
   ```

5. **Salve** a alteração

### Passo 3: Verificar Outras Variáveis

Certifique-se de que estas variáveis estão configuradas (consulte `docs/VARIAVEIS_AMBIENTE_EASYPANEL.md`):

- ✅ `DATABASE_URL` - **DEVE** usar `postgresql+asyncpg://`
- ✅ `DATABASE_URL_SYNC` - **DEVE** usar `postgresql://` (já está correto)
- ✅ `REDIS_URL`
- ✅ `CELERY_BROKER_URL`
- ✅ `CELERY_RESULT_BACKEND`
- ✅ `API_BASE_URL` - com seu domínio público
- ✅ `STORAGE_PATH` ou `storage_path` (dependendo do que EasyPanel aceita)

### Passo 4: Fazer Novo Deploy

Após corrigir `DATABASE_URL`:

1. Clique em **"Deploy"** ou **"Redeploy"**
2. Aguarde o build completar
3. As migrações devem executar corretamente agora

### Passo 5: Verificar Logs

Após o deploy:

1. Vá para a aba **"Logs"** no EasyPanel
2. Procure por mensagens de sucesso:
   ```
   INFO: Alembic migrations completed
   INFO: Application startup complete
   ```
3. Se houver erros, verifique:
   - Se `DATABASE_URL` está correto
   - Se as credenciais estão corretas
   - Se os serviços PostgreSQL e Redis estão rodando

### Passo 6: Testar Aplicação

Após o deploy bem-sucedido:

1. Acesse: `https://criadordigital-vidfinger.ujhifl.easypanel.host/health`
   - Deve retornar: `{"status":"healthy","version":"1.0.0"}`

2. Acesse: `https://criadordigital-vidfinger.ujhifl.easypanel.host/health/dependencies`
   - Deve retornar: `{"all_dependencies_ok":true,...}`

3. Acesse: `https://criadordigital-vidfinger.ujhifl.easypanel.host/docs`
   - Deve mostrar a documentação Swagger

## 📋 Checklist Rápido

- [ ] Código atualizado no GitHub (com psycopg2-binary)
- [ ] Deploy feito no EasyPanel
- [ ] `DATABASE_URL` corrigido para usar `postgresql+asyncpg://`
- [ ] Novo deploy após corrigir `DATABASE_URL`
- [ ] Logs mostram migrações executadas com sucesso
- [ ] Health check retorna `healthy`
- [ ] Dependencies check retorna `all_dependencies_ok: true`

## 🆘 Se Ainda Houver Erros

### Erro: "ModuleNotFoundError: No module named 'psycopg2'"

**Solução**: 
- Verifique se o deploy foi feito **após** o commit com `psycopg2-binary`
- Verifique os logs do build para confirmar que `psycopg2-binary` foi instalado
- Se necessário, force um novo build completo

### Erro: "Database connection failed"

**Solução**:
- Verifique se `DATABASE_URL` usa `postgresql+asyncpg://` (não `postgresql://`)
- Verifique se o serviço PostgreSQL está rodando
- Verifique se as credenciais estão corretas
- Teste a conexão manualmente se possível

### Erro: "Migration failed"

**Solução**:
- Verifique se `DATABASE_URL_SYNC` está correto
- Verifique se `psycopg2-binary` foi instalado
- Verifique os logs do Alembic para erros específicos

## 📞 Próximos Passos

Após tudo funcionar:

1. Teste fazer upload de um vídeo
2. Verifique se o processamento inicia
3. Monitore os logs durante o processamento
4. Verifique se os arquivos são enviados para o CDN (se configurado)

---

## 📚 Documentação de Referência

- **[Variáveis Prontas para Copiar](VARIAVEIS_AMBIENTE_EASYPANEL.md)** - Blocos completos para copiar/colar
- **[Variáveis Completas](VARIAVEIS_AMBIENTE.md)** - Documentação técnica completa
- **[Guia Deploy Completo](GUIA_DEPLOY_EASYPANEL.md)** - Passo a passo completo

