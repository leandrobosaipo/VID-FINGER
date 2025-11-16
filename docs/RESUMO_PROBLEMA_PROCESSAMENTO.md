# 🔍 Resumo do Problema - Processamento de Análise

## 📋 Problema Principal

As análises de vídeo ficam travadas em status "pending" ou falham durante o processamento, especificamente na etapa de "cleaning" (geração de vídeo limpo).

## 🔴 Sintomas Observados

1. **Status "pending"**: Análises criadas mas nunca processadas automaticamente
2. **Status "failed"**: Análises que começam mas falham em ~83% de progresso
3. **Etapa problemática**: Sempre para na etapa "cleaning" (geração de vídeo limpo)
4. **Arquivos não gerados**: `clean_video_url` e `report_url` ficam como `null`

## ✅ Correções Já Implementadas

### 1. Correção do Enum AnalysisStatus
**Problema**: Código usava `AnalysisStatus.running` que não existe no enum
**Solução**: Alterado para `AnalysisStatus.analyzing` (valor correto do enum)
**Arquivo**: `app/services/analysis_processor.py` linha 77

### 2. Melhorias no Fallback de Processamento
**Problema**: `asyncio.create_task()` não funcionava corretamente sem event loop ativo
**Solução**: 
- Melhorado tratamento de erros
- Criada nova sessão de banco para processamento
- Adicionado `await db.refresh()` após commits
**Arquivo**: `app/services/analysis_service.py` linhas 168-203

### 3. Correção de Conversão de Tipos
**Problema**: `analysis_id` sendo passado como UUID ao invés de string
**Solução**: Adicionado `str()` em chamadas para `FileService.generate_storage_path()`
**Arquivo**: `app/services/analysis_processor.py` linhas 200, 234

### 4. Tratamento de Erros na Geração de Vídeo Limpo
**Problema**: Erros na geração de vídeo limpo causavam falha completa
**Solução**: Adicionado try/except para continuar mesmo se vídeo limpo falhar
**Arquivo**: `app/services/analysis_processor.py` linhas 243-251

### 5. Melhorias no Tratamento de Erros Gerais
**Problema**: Erros não eram capturados corretamente
**Solução**: Melhorado tratamento de exceções com busca de análise novamente se necessário
**Arquivo**: `app/services/analysis_processor.py` linhas 296-316

## 🔧 Arquitetura Atual

### Fluxo de Processamento

1. **Upload** → `POST /api/v1/upload/analyze`
   - Recebe arquivo
   - Cria análise com status "pending"
   - Tenta iniciar Celery task ou fallback asyncio

2. **Processamento** → `AnalysisProcessor.process_analysis()`
   - Status muda para "analyzing"
   - Executa etapas sequencialmente:
     - metadata_extraction ✅
     - prnu ✅
     - fft ✅
     - classification ✅
     - report_generation ⚠️ (pode estar falhando silenciosamente)
     - cleaning ❌ (sempre falha aqui)

3. **Finalização** → Status "completed" ou "failed"

### Como o Processamento é Iniciado

**Opção 1: Celery (Preferencial)**
```python
from app.tasks.analysis_tasks import process_analysis
process_analysis.delay(str(analysis_id))
```
- Requer Celery worker rodando
- Tasks são enfileiradas no Redis
- Worker processa tasks da fila

**Opção 2: Fallback asyncio**
```python
asyncio.create_task(AnalysisProcessor.process_analysis(str(analysis_id), db))
```
- Executa no mesmo processo
- Requer event loop ativo
- Pode não funcionar em todos os contextos

## 🐛 Problemas Identificados mas Não Resolvidos

### 1. Processamento Não Inicia Automaticamente
**Sintoma**: Análises ficam em "pending" indefinidamente
**Possíveis Causas**:
- Celery worker não está rodando
- Fallback asyncio não está funcionando
- Erro silencioso ao iniciar processamento

**Evidências**:
- Logs não mostram "Task Celery iniciada" nem "Task de processamento criada"
- 10+ análises pendentes acumuladas

### 2. Falha na Etapa de Cleaning
**Sintoma**: Análise falha em ~83% (após classification, antes de cleaning)
**Possíveis Causas**:
- Erro na função `generate_clean_video()` do módulo `app/core/cleaner.py`
- FFmpeg não disponível ou com problemas
- Erro ao salvar arquivo de vídeo limpo
- Problema com paths ou permissões

**Evidências**:
- Status muda para "failed"
- `error_message` não está sendo salvo corretamente (fica como "N/A")
- Etapa "cleaning" nunca completa

### 3. Relatório Não Está Sendo Gerado
**Sintoma**: `report_url` sempre `null` mesmo quando análise completa parcialmente
**Possíveis Causas**:
- Erro silencioso na geração do relatório
- Erro ao salvar arquivo JSON
- Problema com commit do banco de dados

**Evidências**:
- Análises que chegam até classification não têm `report_file_id`

### 4. Problemas de Sessão de Banco de Dados
**Sintoma**: `IllegalStateChangeError` nos logs
**Possíveis Causas**:
- Conflito de transações
- Sessão sendo fechada enquanto ainda em uso
- Múltiplas sessões acessando mesmo objeto

**Evidências**:
- Erro aparece nos logs: "Method 'close()' can't be called here"

## 📊 Logs Relevantes

```
Erro ao processar análise 3d7b7722-bec0-4521-b3cb-0dc832994200: running
Traceback (most recent call last):
  File "app/services/analysis_processor.py", line 77, in process_analysis
    analysis.status = AnalysisStatus.running
                      ^^^^^^^^^^^^^^^^^^^^^^
AttributeError: running
```

Este erro foi corrigido, mas análises ainda falham.

## 🔍 Arquivos Chave

1. **`app/services/analysis_processor.py`** - Lógica principal de processamento
2. **`app/services/analysis_service.py`** - Inicia processamento após upload
3. **`app/core/cleaner.py`** - Geração de vídeo limpo (possível fonte de erro)
4. **`app/models/analysis.py`** - Enum AnalysisStatus
5. **`app/tasks/analysis_tasks.py`** - Tasks Celery

## 🧪 Como Reproduzir

1. Iniciar servidor: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Fazer upload: `POST /api/v1/upload/analyze` com arquivo de vídeo
3. Monitorar: `GET /api/v1/analysis/{analysis_id}`
4. Observar: Status fica em "pending" ou falha em ~83%

## 💡 Possíveis Soluções a Investigar

1. **Verificar se Celery worker está rodando**
   - Comando: `celery -A app.tasks.celery_app worker --loglevel=info`
   - Verificar se tasks estão sendo processadas

2. **Adicionar mais logs de debug**
   - Logar cada etapa do processamento
   - Logar erros específicos de cada função
   - Verificar se `generate_clean_video()` está sendo chamada

3. **Testar geração de vídeo limpo isoladamente**
   - Chamar `generate_clean_video()` diretamente
   - Verificar se FFmpeg está funcionando
   - Verificar paths e permissões

4. **Verificar se relatório está sendo gerado**
   - Adicionar logs antes/depois de salvar relatório
   - Verificar se arquivo JSON está sendo criado no filesystem
   - Verificar se commit do banco está funcionando

5. **Resolver problemas de sessão de banco**
   - Usar sessões separadas para cada operação
   - Garantir que commits acontecem antes de fechar sessão
   - Evitar compartilhar objetos entre sessões

6. **Implementar BackgroundTasks do FastAPI**
   - Mais confiável que asyncio.create_task()
   - Integrado com FastAPI
   - Melhor controle de execução

## 📝 Próximos Passos Sugeridos

1. Adicionar logging detalhado em cada etapa
2. Testar cada função isoladamente
3. Verificar se FFmpeg está instalado e funcionando
4. Verificar permissões de escrita nos diretórios
5. Implementar BackgroundTasks como alternativa ao Celery
6. Adicionar validação de erros mais específica

## 🔗 Arquivos de Referência

- `COMO_MONITORAR_PROCESSAMENTO.md` - Guia de monitoramento
- `scripts/monitor_analysis.py` - Script de monitoramento
- `scripts/start_celery_worker.sh` - Script para iniciar Celery
- `app/services/analysis_processor.py` - Código principal de processamento

