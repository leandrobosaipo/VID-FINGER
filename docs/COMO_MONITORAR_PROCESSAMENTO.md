# 🔍 Como Monitorar e Testar Processamento em Background

## Problema Identificado

O processamento não está iniciando automaticamente porque:

1. **Celery precisa de worker rodando**: Tasks são enfileiradas mas não processadas sem worker
2. **asyncio.create_task() precisa de event loop ativo**: Fallback não funciona em todos os contextos

## Soluções

### Opção 1: Usar Celery (Recomendado para Produção)

**1. Iniciar Redis:**
```bash
# macOS
brew install redis
brew services start redis

# Ou manualmente
redis-server
```

**2. Iniciar Celery Worker:**
```bash
./scripts/start_celery_worker.sh
```

Ou manualmente:
```bash
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info
```

**3. Verificar se está funcionando:**
```bash
# Em outro terminal, verificar tasks
celery -A app.tasks.celery_app inspect active
```

### Opção 2: Monitorar Análises

**Monitorar análise específica:**
```bash
python scripts/monitor_analysis.py <analysis_id>
```

**Listar análises pendentes:**
```bash
python scripts/monitor_analysis.py --list
```

**Monitorar todas pendentes:**
```bash
python scripts/monitor_analysis.py --all
```

### Opção 3: Verificar Status via API

```bash
# Obter status
curl "http://localhost:8000/api/v1/analysis/{analysis_id}" | python3 -m json.tool

# Listar todas
curl "http://localhost:8000/api/v1/analysis?page=1&page_size=10" | python3 -m json.tool
```

## Como Funciona o Processamento

### Fluxo Atual:

1. **Upload completo** → `create_analysis_from_upload()`
2. **Tenta iniciar Celery task** → `process_analysis.delay()`
3. **Se Celery falhar** → Fallback com `asyncio.create_task()`
4. **Processamento executa** → `AnalysisProcessor.process_analysis()`

### Etapas de Processamento:

1. ⏳ **metadata_extraction** - Extrai metadados do vídeo
2. ⏳ **prnu** - Análise PRNU (ruído do sensor)
3. ⏳ **fft** - Análise FFT temporal
4. ⏳ **classification** - Classifica origem do vídeo
5. ⏳ **report_generation** - Gera relatório JSON
6. ⏳ **cleaning** - Gera vídeo limpo

## Debugging

### Verificar Logs do Servidor

Os logs mostram:
- `✅ Task Celery iniciada` - Celery funcionando
- `⚠️ Celery não disponível` - Usando fallback
- `❌ Erro no processamento` - Erro durante processamento

### Verificar se Processamento Está Rodando

```bash
# Ver processos Python
ps aux | grep python

# Ver processos Celery
ps aux | grep celery

# Ver conexões Redis
redis-cli CLIENT LIST
```

### Testar Processamento Manualmente

```bash
# Via endpoint de reprocessamento
curl -X POST "http://localhost:8000/api/v1/analysis/{analysis_id}/reprocess"
```

## Solução Temporária (Sem Celery)

Se não quiser usar Celery, o código atual tenta usar `asyncio.create_task()`, mas isso só funciona se houver um event loop ativo. Para garantir funcionamento sem Celery, você pode:

1. **Usar BackgroundTasks do FastAPI** (mais confiável)
2. **Processar sincronamente** (não recomendado para produção)
3. **Usar threading** (alternativa simples)

## Próximos Passos

1. ✅ Script de monitoramento criado
2. ✅ Script para iniciar Celery worker criado
3. ⏳ Melhorar fallback para funcionar sem Celery
4. ⏳ Adicionar mais logs de debug

