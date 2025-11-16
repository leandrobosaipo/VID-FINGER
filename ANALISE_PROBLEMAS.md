# Análise de Problemas - VID-FINGER

## Data da Análise
2025-01-XX

## Objetivo
Identificar problemas introduzidos após implementação de endpoints REST, Swagger e fila Celery, comparando com o funcionamento original do CLI.

---

## 1. Comparação: Fluxo Original vs Fluxo Atual

### 1.1 Fluxo Original (CLI - `src/cli.py`)

**Características:**
- ✅ **Processamento síncrono direto** - Todas as etapas executadas sequencialmente em um único processo
- ✅ **Sem dependências externas** - Não requer banco de dados, Redis ou Celery
- ✅ **Tratamento de erros explícito** - Erros são mostrados no terminal e salvos em `error_report.json`
- ✅ **Paths simples** - Usa `output/` com estrutura clara (original/, reports/, clean/)
- ✅ **Funções diretas** - Chama funções dos módulos `src.core.*` diretamente

**Fluxo de execução:**
```
1. Validação do arquivo de entrada
2. Extração de metadados (extract_metadata)
3. Estimativa de GOP (estimate_gop_size, estimate_gop_regularity)
4. Cálculo de fingerprint (calculate_fingerprint)
5. Análise PRNU (detect_prnu)
6. Análise FFT (detect_diffusion_signature, analyze_temporal_jitter)
7. Integridade de metadados (analyze_metadata_integrity)
8. Classificação preliminar (classify_video)
9. Análise de timeline (analyze_timeline)
10. Classificação final (classify_video)
11. Geração de relatório (create_forensic_report)
12. Salvamento de relatório (save_report)
13. Geração de vídeo limpo (generate_clean_video)
14. Exibição de resumo (print_summary)
```

**Pontos críticos:**
- Todas as funções são chamadas diretamente, sem intermediários
- Não há gerenciamento de sessão de banco de dados
- Não há necessidade de commit/refresh
- Erros são propagados imediatamente e tratados

### 1.2 Fluxo Atual (API - `app/services/analysis_service.py` + `app/services/analysis_processor.py`)

**Características:**
- ⚠️ **Processamento assíncrono** - Tenta usar Celery, com fallback para asyncio
- ⚠️ **Dependências externas** - Requer banco de dados, Redis (para Celery), e Celery worker
- ⚠️ **Tratamento de erros complexo** - Erros podem ser silenciosos se não capturados corretamente
- ⚠️ **Paths complexos** - Usa `storage/` com estrutura baseada em `analysis_id`
- ⚠️ **Múltiplas camadas** - Upload → Análise → Processamento → Tasks

**Fluxo de execução:**
```
1. Upload via API (POST /api/v1/upload/analyze)
2. Criação de análise no banco (status: pending)
3. Tentativa de iniciar Celery task (process_analysis.delay)
4. Se Celery falhar → Fallback asyncio (asyncio.create_task)
5. Processamento assíncrono (AnalysisProcessor.process_analysis)
   - Busca análise no banco
   - Atualiza status para analyzing
   - Executa etapas sequencialmente
   - Salva resultados no banco após cada etapa
   - Atualiza status para completed ou failed
```

**Pontos críticos:**
- Depende de Celery worker rodando OU fallback asyncio funcionando
- Requer gerenciamento correto de sessões de banco de dados
- Múltiplos commits podem causar problemas de transação
- Erros podem ser silenciosos se não logados corretamente

### 1.3 Diferenças Críticas Identificadas

| Aspecto | Original (CLI) | Atual (API) | Impacto |
|---------|---------------|-------------|---------|
| **Processamento** | Síncrono direto | Assíncrono (Celery/asyncio) | ⚠️ Pode não iniciar |
| **Banco de dados** | Não usa | SQLAlchemy async | ⚠️ Problemas de sessão |
| **Paths** | `output/` fixo | `storage/{analysis_id}/` | ✅ OK |
| **Tratamento de erros** | Terminal + JSON | Logs + banco | ⚠️ Pode ser silencioso |
| **Dependências** | Apenas Python | Python + Redis + Celery | ⚠️ Mais pontos de falha |

---

## 2. Problemas Identificados

### 2.1 Problema: Processamento Não Inicia Automaticamente

**Sintoma:**
- Análises ficam em status "pending" indefinidamente
- Logs não mostram tentativas de iniciar processamento

**Causa Raiz Identificada:**

#### Problema 1: Celery não está rodando
- **Evidência:** Código tenta `process_analysis.delay()` mas não há worker processando
- **Localização:** `app/services/analysis_service.py:172`
- **Solução:** Verificar se Celery worker está rodando ou usar BackgroundTasks do FastAPI

#### Problema 2: Fallback asyncio não funciona corretamente
- **Evidência:** `asyncio.create_task()` pode não executar se não houver event loop ativo
- **Localização:** `app/services/analysis_service.py:196`
- **Problema:** Em contexto FastAPI, o event loop pode não estar disponível no momento da criação da task
- **Solução:** Usar `BackgroundTasks` do FastAPI ao invés de `asyncio.create_task()`

**Código problemático:**
```python
# app/services/analysis_service.py:192-203
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(start_processing())  # ⚠️ Pode não executar
        logger.info(f"✅ Task de processamento criada para análise {analysis_id}")
    else:
        loop.run_until_complete(start_processing())  # ⚠️ Pode bloquear
except RuntimeError:
    asyncio.run(start_processing())  # ⚠️ Cria novo loop, pode não funcionar
```

**Solução recomendada:**
```python
from fastapi import BackgroundTasks

# No endpoint ou serviço
background_tasks.add_task(AnalysisProcessor.process_analysis, str(analysis_id), db)
```

### 2.2 Problema: Falha na Etapa Cleaning (83%)

**Sintoma:**
- Análise falha em ~83% de progresso (após classification, antes de cleaning)
- Status muda para "failed"
- `error_message` não está sendo salvo corretamente

**Causa Raiz Identificada:**

#### Problema 1: `generate_clean_video()` pode retornar None silenciosamente
- **Evidência:** Função retorna `None` se `results["success"]` for `False`, mas não lança exceção
- **Localização:** `app/core/cleaner.py:214-219`
- **Problema:** Código em `analysis_processor.py:257` verifica `if clean_result and Path(clean_result).exists()`, mas se `clean_result` for `None`, não há erro explícito

#### Problema 2: FFmpeg pode não estar disponível ou com problemas
- **Evidência:** Funções `remove_metadata()`, `reencode_neutral()`, `add_temporal_jitter()` retornam `False` em caso de erro, mas não propagam exceção
- **Localização:** `app/core/cleaner.py:8-116`
- **Problema:** Erros do FFmpeg são capturados mas não logados

#### Problema 3: Erro não está sendo salvo no banco
- **Evidência:** Código em `analysis_processor.py:300-321` tenta salvar erro, mas pode falhar silenciosamente
- **Localização:** `app/services/analysis_processor.py:300-321`
- **Problema:** Se `analysis` não estiver disponível no contexto de exceção, erro não é salvo

**Código problemático:**
```python
# app/services/analysis_processor.py:247-255
try:
    clean_result = generate_clean_video(...)
except Exception as clean_error:
    logger.warning(f"[{analysis_id}] Erro ao gerar vídeo limpo: {clean_error}")
    clean_result = None  # ⚠️ Continua sem erro explícito

if clean_result and Path(clean_result).exists():
    # Salva vídeo limpo
else:
    # ⚠️ Não há else explícito - continua sem erro
```

**Solução recomendada:**
1. Adicionar logs detalhados antes/depois de cada chamada FFmpeg
2. Verificar se FFmpeg está disponível no início do processamento
3. Salvar erro explicitamente se cleaning falhar
4. Considerar tornar cleaning opcional (não bloquear análise completa)

### 2.3 Problema: Relatório Não é Gerado

**Sintoma:**
- `report_url` sempre `null` mesmo quando análise completa parcialmente
- Análises que chegam até classification não têm `report_file_id`

**Causa Raiz Identificada:**

#### Problema 1: Relatório pode estar sendo gerado mas não salvo no banco
- **Evidência:** Código gera relatório e salva arquivo, mas commit pode falhar
- **Localização:** `app/services/analysis_processor.py:189-230`
- **Problema:** Se commit falhar, `report_file_id` não é setado, mas arquivo existe no filesystem

#### Problema 2: Erro silencioso ao salvar relatório
- **Evidência:** Não há try/except específico para salvamento de relatório
- **Localização:** `app/services/analysis_processor.py:212-230`
- **Problema:** Se `report_path.stat().st_size` ou `FileService.calculate_checksum()` falharem, erro não é capturado

**Código problemático:**
```python
# app/services/analysis_processor.py:212-230
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# ⚠️ Sem try/except - pode falhar silenciosamente
report_file = File(...)
db.add(report_file)
analysis.report_file_id = report_file.id
await db.commit()  # ⚠️ Se falhar, não há tratamento
```

**Solução recomendada:**
1. Adicionar try/except específico para salvamento de relatório
2. Verificar se arquivo foi criado antes de criar registro no banco
3. Adicionar logs antes/depois de cada operação crítica

### 2.4 Problema: Sessões de Banco de Dados

**Sintoma:**
- `IllegalStateChangeError` nos logs
- Erro: "Method 'close()' can't be called here"

**Causa Raiz Identificada:**

#### Problema 1: Múltiplas sessões acessando mesmo objeto
- **Evidência:** `analysis` é buscado em uma sessão, mas pode ser usado em outra
- **Localização:** `app/services/analysis_service.py:184` cria nova sessão para processamento
- **Problema:** Objeto `analysis` da sessão original pode estar sendo usado na nova sessão

#### Problema 2: Sessões sendo fechadas prematuramente
- **Evidência:** `get_db()` fecha sessão automaticamente após yield
- **Localização:** `app/database.py:34-40`
- **Problema:** Se objeto for usado após fechamento da sessão, erro ocorre

#### Problema 3: Conflitos de transação
- **Evidência:** Múltiplos commits na mesma análise podem causar conflitos
- **Localização:** `app/services/analysis_processor.py` tem múltiplos `await db.commit()`
- **Problema:** Se duas operações tentarem atualizar mesmo objeto simultaneamente, erro ocorre

**Código problemático:**
```python
# app/services/analysis_service.py:181-188
async def start_processing():
    async with AsyncSessionLocal() as processing_db:
        # ⚠️ Nova sessão - objeto analysis pode não estar sincronizado
        await AnalysisProcessor.process_analysis(str(analysis_id), processing_db)
```

**Solução recomendada:**
1. Buscar análise novamente na nova sessão ao invés de reutilizar objeto
2. Usar `db.refresh()` após commits quando necessário
3. Garantir que commits acontecem antes de fechar sessão
4. Evitar compartilhar objetos entre sessões

---

## 3. Plano de Correção

### 3.1 Correção Imediata: Processamento Não Inicia

**Prioridade:** ALTA

**Ações:**
1. Substituir fallback asyncio por `BackgroundTasks` do FastAPI
2. Adicionar verificação se Celery está disponível antes de tentar usar
3. Adicionar logs detalhados para rastrear tentativas de início

**Arquivos a modificar:**
- `app/services/analysis_service.py` (linhas 168-203)
- `app/api/v1/endpoints/upload.py` (adicionar BackgroundTasks)

### 3.2 Correção: Falha na Etapa Cleaning

**Prioridade:** ALTA

**Ações:**
1. Adicionar logs detalhados antes/depois de cada chamada FFmpeg
2. Verificar disponibilidade do FFmpeg no início do processamento
3. Salvar erro explicitamente se cleaning falhar (não apenas warning)
4. Tornar cleaning opcional - não bloquear análise completa se falhar

**Arquivos a modificar:**
- `app/services/analysis_processor.py` (linhas 232-275)
- `app/core/cleaner.py` (adicionar logs e melhorar tratamento de erros)

### 3.3 Correção: Relatório Não é Gerado

**Prioridade:** MÉDIA

**Ações:**
1. Adicionar try/except específico para salvamento de relatório
2. Verificar se arquivo foi criado antes de criar registro no banco
3. Adicionar logs antes/depois de cada operação crítica

**Arquivos a modificar:**
- `app/services/analysis_processor.py` (linhas 189-230)

### 3.4 Correção: Sessões de Banco de Dados

**Prioridade:** MÉDIA

**Ações:**
1. Buscar análise novamente na nova sessão ao invés de reutilizar objeto
2. Usar `db.refresh()` após commits quando necessário
3. Garantir que commits acontecem antes de fechar sessão

**Arquivos a modificar:**
- `app/services/analysis_processor.py` (adicionar refresh após commits)
- `app/services/analysis_service.py` (buscar análise novamente na nova sessão)

---

## 4. Checklist de Verificação

Antes de implementar correções, verificar:

- [ ] Celery worker está rodando? (`celery -A app.tasks.celery_app worker --loglevel=info`)
- [ ] Redis está disponível? (`redis-cli ping`)
- [ ] FFmpeg está instalado e no PATH? (`ffmpeg -version`)
- [ ] Permissões de escrita nos diretórios? (`storage/`, `output/`)
- [ ] Banco de dados está acessível? (conexão SQLite/PostgreSQL)
- [ ] Logs estão sendo gerados? (verificar nível de log)

---

## 5. Recomendações Adicionais

### 5.1 Melhorias de Arquitetura

1. **Usar BackgroundTasks do FastAPI** ao invés de asyncio.create_task()
   - Mais confiável e integrado com FastAPI
   - Melhor controle de execução
   - Não requer gerenciamento manual de event loop

2. **Adicionar health check para dependências**
   - Verificar Celery worker antes de tentar usar
   - Verificar FFmpeg no início do processamento
   - Verificar banco de dados antes de operações críticas

3. **Melhorar tratamento de erros**
   - Sempre salvar erro no banco quando análise falha
   - Adicionar logs detalhados em cada etapa
   - Não falhar silenciosamente

4. **Tornar cleaning opcional**
   - Não bloquear análise completa se cleaning falhar
   - Salvar erro mas continuar processamento
   - Permitir retry de cleaning posteriormente

### 5.2 Testes Recomendados

1. **Teste de processamento sem Celery**
   - Verificar se fallback funciona corretamente
   - Verificar se análise completa sem worker

2. **Teste de falha em cleaning**
   - Simular falha do FFmpeg
   - Verificar se análise completa mesmo com cleaning falhando
   - Verificar se erro é salvo corretamente

3. **Teste de geração de relatório**
   - Verificar se relatório é gerado e salvo
   - Verificar se `report_file_id` é setado corretamente
   - Verificar se commit funciona

4. **Teste de sessões de banco**
   - Verificar se não há `IllegalStateChangeError`
   - Verificar se objetos são sincronizados corretamente
   - Verificar se commits funcionam corretamente

---

## 6. Conclusão

Os problemas identificados são principalmente relacionados à transição de um sistema síncrono simples (CLI) para um sistema assíncrono complexo (API). As principais causas são:

1. **Processamento não inicia**: Fallback asyncio não funciona corretamente no contexto FastAPI
2. **Falha em cleaning**: Erros não são propagados corretamente, análise falha silenciosamente
3. **Relatório não gerado**: Commits podem falhar sem tratamento adequado
4. **Problemas de sessão DB**: Objetos compartilhados entre sessões causam conflitos

As correções recomendadas são diretas e devem resolver a maioria dos problemas. A prioridade é corrigir o problema de inicialização do processamento, pois é o mais crítico.

