# Setup Completo - VID-FINGER API

## ✅ Status da Implementação

### Fase 1: Preparação do Ambiente - COMPLETA
- ✅ Python 3.11.4 verificado
- ✅ FFmpeg 8.0 instalado
- ✅ Ambiente virtual criado
- ✅ Dependências instaladas
- ✅ Arquivo .env configurado com credenciais do Spaces

### Fase 2: Configuração do Banco de Dados - COMPLETA
- ✅ SQLite configurado para desenvolvimento
- ✅ Migrações Alembic criadas e aplicadas
- ✅ Tabelas criadas: analyses, files, analysis_steps
- ✅ Problema de campo `metadata` resolvido (renomeado para `video_metadata` e `step_metadata`)

### Fase 3: Configuração do DigitalOcean Spaces - COMPLETA
- ✅ Credenciais configuradas no .env
- ✅ OUTPUT_PREFIX=vid-finger configurado
- ✅ StorageService implementado
- ✅ LifecycleService criado (script para configurar expiração de 7 dias)
- ⚠️ Lifecycle policy precisa ser configurada manualmente no painel do Spaces (erro SSL em dev)

### Fase 4: Correção de Dependências - COMPLETA
- ✅ Imports corrigidos (app.core ao invés de src.core)
- ✅ greenlet instalado (necessário para SQLAlchemy async)
- ✅ pymediainfo versão corrigida (7.0.0 ao invés de 9.0.0)
- ✅ prnu removido do requirements (módulo local)

### Fase 5: Teste de Inicialização - COMPLETA
- ✅ FastAPI inicia corretamente
- ✅ /docs acessível
- ✅ /health retorna OK
- ✅ Endpoints básicos funcionando

### Fase 6: Teste de Endpoints - COMPLETA
- ✅ POST /api/v1/upload/init - Funcionando
- ✅ POST /api/v1/upload/chunk/{id} - Funcionando
- ✅ POST /api/v1/upload/complete/{id} - Funcionando
- ✅ GET /api/v1/analysis/{id} - Funcionando
- ✅ Arquivos sendo salvos corretamente em storage/

## 🎯 Como Testar Localmente

### Opção 1: Script Automatizado (Recomendado)

```bash
# 1. Ativar ambiente virtual
source venv/bin/activate

# 2. Iniciar servidor (em um terminal)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Em outro terminal, executar testes
source venv/bin/activate
python scripts/test_api_local.py
```

### Opção 2: Teste Manual via Swagger

1. Iniciar servidor:
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

2. Acessar http://localhost:8000/docs

3. Testar endpoints interativamente

### Opção 3: Teste com Arquivo Real

```bash
source venv/bin/activate

# Iniciar servidor
uvicorn app.main:app --reload &

# Executar teste completo
python scripts/test_api_local.py

# Verificar resultados
ls -lh storage/original/*/
sqlite3 vidfinger.db "SELECT id, status, classification FROM analyses LIMIT 5;"
```

## 📋 Checklist de Funcionalidades

### ✅ Funcionando
- [x] Upload chunked de vídeos
- [x] Criação de análise no banco
- [x] Endpoints de status
- [x] Armazenamento local de arquivos
- [x] Validação de tipos de arquivo
- [x] Geração de checksums
- [x] Estrutura de diretórios organizada

### ⚠️ Parcialmente Implementado
- [ ] Processamento de análise (tasks Celery criadas mas não implementadas)
- [ ] Upload para CDN (código pronto, precisa testar com credenciais)
- [ ] Webhooks (código pronto, precisa testar)
- [ ] Download de relatórios (endpoint criado mas não implementado)
- [ ] Download de arquivos (endpoint criado mas não implementado)

### ❌ Não Implementado
- [ ] Cancelamento de análise
- [ ] Processamento assíncrono completo
- [ ] Geração de relatórios JSON
- [ ] Geração de vídeo limpo
- [ ] Integração completa com módulos core/

## 🔧 Configuração do DigitalOcean Spaces Lifecycle

Para configurar a expiração automática de 7 dias:

### Opção 1: Via Painel Web
1. Acesse o painel do DigitalOcean Spaces
2. Selecione o bucket `cod5`
3. Vá em "Settings" > "Lifecycle Rules"
4. Crie uma regra:
   - Prefix: `vid-finger/`
   - Action: Delete
   - Days: 7

### Opção 2: Via Script (quando SSL estiver resolvido)
```bash
source venv/bin/activate
python scripts/setup_spaces_lifecycle.py
```

## 📁 Estrutura de Arquivos

```
VID-FINGER/
├── app/                    # Código da API
│   ├── api/v1/endpoints/  # Endpoints REST
│   ├── core/              # Módulos de análise (reutilizados)
│   ├── models/            # Modelos SQLAlchemy
│   ├── services/          # Lógica de negócio
│   └── tasks/             # Tasks Celery
├── storage/               # Arquivos armazenados localmente
├── migrations/            # Migrações Alembic
├── scripts/               # Scripts auxiliares
├── tests/                 # Testes
├── .env                   # Variáveis de ambiente (criado)
├── vidfinger.db           # Banco SQLite (criado após migração)
└── requirements-api.txt   # Dependências da API
```

## 🐛 Problemas Conhecidos e Soluções

### 1. Erro SSL no Spaces
**Problema**: Erro ao configurar lifecycle policy via script
**Solução**: Configurar manualmente no painel ou ignorar em dev local

### 2. Tasks Celery não implementadas
**Problema**: Análise não é processada automaticamente
**Solução**: Implementar tasks em `app/tasks/analysis_tasks.py` chamando módulos `core/`

### 3. Redis não necessário para testes básicos
**Problema**: Redis não está rodando
**Solução**: Para testes básicos de upload, Redis não é necessário. Celery só é usado para processamento assíncrono.

## 🚀 Próximos Passos

1. **Implementar Tasks de Análise**
   - Completar `extract_metadata_task`
   - Completar `analyze_prnu_task`
   - Completar `analyze_fft_task`
   - Completar `classify_video_task`
   - Completar `generate_report_task`
   - Completar `generate_clean_video_task`

2. **Testar com Arquivo Real**
   - Usar `/Users/leandrobosaipo/Downloads/andando-pela-cua.mp4`
   - Verificar se análise completa funciona

3. **Implementar Endpoints de Download**
   - Completar `GET /api/v1/reports/{id}/report`
   - Completar `GET /api/v1/files/{id}/{type}`

4. **Configurar Redis e Celery** (opcional para dev)
   - Instalar Redis: `brew install redis`
   - Iniciar Redis: `redis-server`
   - Iniciar Celery worker: `celery -A app.tasks.celery_app worker`

## 📝 Comandos Úteis

```bash
# Ativar ambiente
source venv/bin/activate

# Iniciar servidor
uvicorn app.main:app --reload

# Ver logs do banco
sqlite3 vidfinger.db "SELECT * FROM analyses ORDER BY created_at DESC LIMIT 5;"

# Ver arquivos salvos
find storage -type f -name "*.mp4" | head -5

# Limpar dados de teste
rm -rf storage/uploads/* storage/original/* storage/reports/* storage/clean/*
rm vidfinger.db
alembic upgrade head
```

## ✅ Validação Final

Execute este comando para validar que tudo está funcionando:

```bash
source venv/bin/activate && \
python -c "
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)

# Test 1: Health
r = client.get('/health')
assert r.status_code == 200, 'Health check failed'
print('✓ Health check OK')

# Test 2: Upload init
r = client.post('/api/v1/upload/init', json={
    'filename': 'test.mp4',
    'file_size': 1000,
    'mime_type': 'video/mp4'
})
assert r.status_code == 201, 'Upload init failed'
upload_id = r.json()['upload_id']
print('✓ Upload init OK')

# Test 3: Chunk upload
r = client.post(
    f'/api/v1/upload/chunk/{upload_id}',
    data={'chunk_number': 0},
    files={'chunk': ('test.bin', io.BytesIO(b'x' * 1000), 'application/octet-stream')}
)
assert r.status_code == 200, 'Chunk upload failed'
print('✓ Chunk upload OK')

# Test 4: Complete upload
r = client.post(f'/api/v1/upload/complete/{upload_id}')
assert r.status_code == 200, 'Complete upload failed'
analysis_id = r.json()['analysis_id']
print('✓ Complete upload OK')

# Test 5: Get analysis
r = client.get(f'/api/v1/analysis/{analysis_id}')
assert r.status_code == 200, 'Get analysis failed'
print('✓ Get analysis OK')

print('\n🎉 Todos os testes passaram! API está funcionando corretamente.')
"
```

Se todos os testes passarem, a API está pronta para uso!

