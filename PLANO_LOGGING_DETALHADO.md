# Plano de Implementação de Logging Detalhado

## Objetivo
Implementar logging abrangente em todas as camadas da aplicação para rastrear o fluxo completo de upload e análise, permitindo identificar onde ocorrem problemas (aplicação, servidor, storage service, DigitalOcean).

---

## Problema Atual
- Upload trava no nó (client) sem logs visíveis no servidor
- Impossível rastrear onde o processo está travando
- Falta de visibilidade em operações críticas (storage, CDN)

---

## Plano de Implementação

### 1. Middleware de Logging HTTP (Nova Camada)
**Arquivo:** `app/middleware/request_logging.py`

**Funcionalidades:**
- ✅ Interceptar TODAS as requisições HTTP antes de processar
- ✅ Gerar Correlation ID único por requisição
- ✅ Logar: método, path, headers (sanitizados), IP do cliente, timestamp
- ✅ Logar resposta: status code, tempo de processamento, tamanho da resposta
- ✅ Incluir Correlation ID em todos os logs subsequentes da mesma requisição

**Formato do Log:**
```
[2025-01-XX HH:MM:SS] [INFO] [REQUEST] [CORRELATION:abc123] → POST /api/v1/upload/analyze | IP: 192.168.1.1 | User-Agent: ...
[2025-01-XX HH:MM:SS] [INFO] [REQUEST] [CORRELATION:abc123] ← 202 Accepted | Duration: 1.234s | Size: 456 bytes
```

---

### 2. Logging no Endpoint `/api/v1/upload/analyze`
**Arquivo:** `app/api/v1/endpoints/upload.py`

**Pontos de Logging:**
1. **Início da requisição:**
   - Recebimento do arquivo
   - Nome, tamanho, MIME type detectado
   - Correlation ID

2. **Validações:**
   - Validação de tipo de arquivo (sucesso/falha)
   - Validação de tamanho (sucesso/falha)
   - Motivo de falha se houver

3. **Upload interno:**
   - Criação de upload_id
   - Divisão em chunks (quantidade)
   - Salvamento de cada chunk (progresso)
   - Finalização do upload

4. **Criação de análise:**
   - ID da análise criada
   - Status inicial
   - Webhook URL (se fornecido)

5. **Processamento em background:**
   - Task adicionada ao BackgroundTasks
   - Fallback para asyncio.create_task (se necessário)
   - Erros na criação da task

6. **Resposta:**
   - Status HTTP retornado
   - Tempo total da requisição
   - Dados retornados (analysis_id, status_url)

**Formato do Log:**
```
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Recebido arquivo: video.mp4 (1048576 bytes, video/mp4)
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Validações OK: tipo=video/mp4, tamanho=1048576
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Upload iniciado: upload_id=def456, chunks=1
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Chunk 0/1 salvo (100.0% completo)
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Upload finalizado: checksum=sha256:...
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Análise criada: analysis_id=xyz789
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Task de processamento adicionada ao BackgroundTasks
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Resposta enviada: 202 Accepted (1.234s)
```

---

### 3. Logging no UploadService
**Arquivo:** `app/services/upload_service.py`

**Pontos de Logging:**
1. **init_upload:**
   - Validações de tipo e tamanho
   - Cálculo de chunks
   - Criação do upload_id

2. **save_chunk:**
   - Recebimento de chunk (número, tamanho)
   - Salvamento no disco
   - Progresso atual (X/Y chunks)
   - Erros de I/O

3. **complete_upload:**
   - Montagem do arquivo final
   - Cálculo de checksum
   - Limpeza de chunks temporários
   - Caminho do arquivo final

**Formato do Log:**
```
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD_SERVICE] [UPLOAD_ID:def456] Inicializando upload: filename=video.mp4, size=1048576, chunks=1
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD_SERVICE] [UPLOAD_ID:def456] Chunk 0 recebido: size=1048576 bytes
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD_SERVICE] [UPLOAD_ID:def456] Chunk 0 salvo em: /app/storage/uploads/def456/chunk_00000
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD_SERVICE] [UPLOAD_ID:def456] Progresso: 1/1 chunks (100.0%)
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD_SERVICE] [UPLOAD_ID:def456] Finalizando upload: montando arquivo final
[2025-01-XX HH:MM:SS] [INFO] [UPLOAD_SERVICE] [UPLOAD_ID:def456] Arquivo montado: path=/app/storage/original/xyz789/video.mp4, checksum=sha256:...
```

---

### 4. Logging no ChunkedUploadManager
**Arquivo:** `app/utils/chunked_upload.py`

**Pontos de Logging:**
1. **init_upload:**
   - Metadados salvos
   - Diretório criado

2. **save_chunk:**
   - Chunk recebido (número, tamanho real)
   - Escrita no disco (sucesso/falha)
   - Estado atual (chunks recebidos)

3. **assemble_file:**
   - Início da montagem
   - Chunks encontrados
   - Ordem de montagem
   - Finalização e checksum

**Formato do Log:**
```
[2025-01-XX HH:MM:SS] [DEBUG] [CHUNKED_UPLOAD] [UPLOAD_ID:def456] Inicializando: dir=/app/storage/uploads/def456
[2025-01-XX HH:MM:SS] [DEBUG] [CHUNKED_UPLOAD] [UPLOAD_ID:def456] Metadados salvos: metadata.json
[2025-01-XX HH:MM:SS] [DEBUG] [CHUNKED_UPLOAD] [UPLOAD_ID:def456] Salvando chunk 0: size=1048576, file=chunk_00000
[2025-01-XX HH:MM:SS] [DEBUG] [CHUNKED_UPLOAD] [UPLOAD_ID:def456] Chunk 0 salvo com sucesso
[2025-01-XX HH:MM:SS] [DEBUG] [CHUNKED_UPLOAD] [UPLOAD_ID:def456] Montando arquivo: 1 chunks encontrados
[2025-01-XX HH:MM:SS] [DEBUG] [CHUNKED_UPLOAD] [UPLOAD_ID:def456] Arquivo montado: checksum=sha256:...
```

---

### 5. Logging no StorageService (DigitalOcean Spaces)
**Arquivo:** `app/services/storage_service.py`

**Pontos de Logging:**
1. **Inicialização:**
   - Cliente S3 criado (sucesso/falha)
   - Credenciais validadas
   - Bucket configurado

2. **upload_file:**
   - Início do upload (arquivo, key, tamanho)
   - Tipo de upload (simples vs multipart)
   - Progresso do upload (se possível)
   - URL gerada (sucesso)
   - Erro detalhado (falha) com código de erro do S3

3. **Conexão:**
   - Timeout de conexão
   - Erros de rede
   - Erros de autenticação

**Formato do Log:**
```
[2025-01-XX HH:MM:SS] [INFO] [STORAGE] [ANALYSIS:xyz789] Iniciando upload para CDN: file=/app/storage/..., key=vid-finger/analyses/xyz789/original/video.mp4, size=1048576
[2025-01-XX HH:MM:SS] [INFO] [STORAGE] [ANALYSIS:xyz789] Upload em progresso: 0% (0/1048576 bytes)
[2025-01-XX HH:MM:SS] [INFO] [STORAGE] [ANALYSIS:xyz789] Upload em progresso: 50% (524288/1048576 bytes)
[2025-01-XX HH:MM:SS] [INFO] [STORAGE] [ANALYSIS:xyz789] Upload concluído: URL=https://nyc3.digitaloceanspaces.com/cod5/vid-finger/analyses/xyz789/original/video.mp4
[2025-01-XX HH:MM:SS] [ERROR] [STORAGE] [ANALYSIS:xyz789] Erro no upload: ClientError(NoCredentialsError) - Credenciais não encontradas
```

---

### 6. Logging no AnalysisService
**Arquivo:** `app/services/analysis_service.py`

**Pontos de Logging (Adicionais):**
1. **create_analysis_from_file:**
   - Arquivo recebido
   - Upload interno iniciado
   - Análise criada
   - Persistência no banco (commit)

2. **start_processing_background:**
   - Task iniciada
   - Método usado (Celery vs direto)
   - Erros na inicialização

**Formato do Log:**
```
[2025-01-XX HH:MM:SS] [INFO] [ANALYSIS] [ANALYSIS:xyz789] Criando análise a partir de arquivo: filename=video.mp4
[2025-01-XX HH:MM:SS] [INFO] [ANALYSIS] [ANALYSIS:xyz789] Upload interno iniciado: upload_id=def456
[2025-01-XX HH:MM:SS] [INFO] [ANALYSIS] [ANALYSIS:xyz789] Arquivo persistido no banco: file_id=file-uuid, path=/app/storage/...
[2025-01-XX HH:MM:SS] [INFO] [ANALYSIS] [ANALYSIS:xyz789] Análise persistida no banco: analysis_id=xyz789, status=pending
[2025-01-XX HH:MM:SS] [INFO] [ANALYSIS] [ANALYSIS:xyz789] Processamento em background iniciado: método=BackgroundTasks
```

---

### 7. Configuração de Logging Centralizada
**Arquivo:** `app/config.py` ou `app/utils/logger.py`

**Configurações:**
- Nível de log configurável via variável de ambiente (`LOG_LEVEL=INFO|DEBUG`)
- Formato padronizado com timestamps, níveis, contexto
- Suporte a output em console (stdout) e arquivo (opcional)
- Sanitização de dados sensíveis (senhas, tokens)

**Variáveis de Ambiente:**
```bash
LOG_LEVEL=INFO  # ou DEBUG para logs mais detalhados
LOG_FILE=/app/logs/app.log  # opcional, se não especificado só console
LOG_FORMAT=structured  # ou simple
```

---

### 8. Context Manager para Correlation ID
**Arquivo:** `app/utils/context.py`

**Funcionalidade:**
- Context variable para armazenar Correlation ID
- Função helper para obter Correlation ID em qualquer lugar
- Integração com middleware HTTP

---

## Estrutura de Arquivos Novos/Criados

```
app/
├── middleware/
│   ├── __init__.py
│   └── request_logging.py  # NOVO: Middleware de logging HTTP
├── utils/
│   ├── context.py  # NOVO: Context manager para Correlation ID
│   └── logger.py  # NOVO: Configuração centralizada de logging
└── [arquivos existentes modificados]
    ├── main.py  # Adicionar middleware
    ├── api/v1/endpoints/upload.py  # Adicionar logs detalhados
    ├── services/upload_service.py  # Adicionar logs
    ├── services/storage_service.py  # Adicionar logs detalhados
    ├── services/analysis_service.py  # Adicionar logs
    └── utils/chunked_upload.py  # Adicionar logs
```

---

## Ordem de Implementação

1. ✅ Criar configuração centralizada de logging (`utils/logger.py`)
2. ✅ Criar context manager para Correlation ID (`utils/context.py`)
3. ✅ Criar middleware de logging HTTP (`middleware/request_logging.py`)
4. ✅ Integrar middleware no `main.py`
5. ✅ Adicionar logs no endpoint `/api/v1/upload/analyze`
6. ✅ Adicionar logs no `UploadService`
7. ✅ Adicionar logs no `ChunkedUploadManager`
8. ✅ Adicionar logs detalhados no `StorageService`
9. ✅ Adicionar logs no `AnalysisService`
10. ✅ Testar fluxo completo de upload
11. ✅ Commit e deploy

---

## Formato Padrão de Log

**Estrutura:**
```
[TIMESTAMP] [LEVEL] [CONTEXT] [CORRELATION_ID] [ANALYSIS_ID/UPLOAD_ID] Mensagem | Detalhes adicionais
```

**Exemplo:**
```
[2025-01-15 10:30:45.123] [INFO] [REQUEST] [CORRELATION:abc123] → POST /api/v1/upload/analyze | IP: 192.168.1.1
[2025-01-15 10:30:45.124] [INFO] [UPLOAD] [CORRELATION:abc123] Recebido arquivo: video.mp4 (1048576 bytes, video/mp4)
[2025-01-15 10:30:45.125] [INFO] [UPLOAD] [CORRELATION:abc123] [ANALYSIS:xyz789] Análise criada
[2025-01-15 10:30:45.126] [INFO] [STORAGE] [CORRELATION:abc123] [ANALYSIS:xyz789] Iniciando upload para CDN
[2025-01-15 10:30:46.500] [INFO] [STORAGE] [CORRELATION:abc123] [ANALYSIS:xyz789] Upload concluído: URL=https://...
[2025-01-15 10:30:46.501] [INFO] [REQUEST] [CORRELATION:abc123] ← 202 Accepted | Duration: 1.378s
```

---

## Validações e Testes

1. **Teste de Upload Simples:**
   - Upload de arquivo pequeno (< 5MB)
   - Verificar logs em todas as camadas
   - Verificar Correlation ID presente em todos os logs

2. **Teste de Upload Grande:**
   - Upload de arquivo grande (> 5MB, múltiplos chunks)
   - Verificar logs de progresso de chunks
   - Verificar logs de montagem do arquivo

3. **Teste de Upload com CDN:**
   - Upload com `UPLOAD_TO_CDN=True`
   - Verificar logs do StorageService
   - Verificar URL gerada nos logs

4. **Teste de Erro:**
   - Upload de arquivo inválido
   - Verificar logs de erro detalhados
   - Verificar stack trace quando aplicável

---

## Perguntas para Validação

Antes de implementar, preciso confirmar:

1. **Nível de Log:**
   - [ ] INFO apenas (operações principais)
   - [ ] DEBUG também (detalhes internos, chamadas de função)

2. **Output:**
   - [ ] Console apenas (stdout/stderr)
   - [ ] Arquivo também (`/app/logs/app.log`)
   - [ ] Ambos

3. **Correlation ID:**
   - [ ] Incluir em TODOS os logs da requisição
   - [ ] Apenas em logs principais

4. **Dados Sensíveis:**
   - [ ] Sanitizar automaticamente (senhas, tokens)
   - [ ] Logar tudo (para debug)

5. **Performance:**
   - [ ] Logs assíncronos (não bloquear requisições)
   - [ ] Logs síncronos (mais simples)

---

## Próximos Passos

Após aprovação do plano:

1. Implementar código conforme plano
2. Testar localmente
3. Criar commit com mensagem descritiva
4. Fazer push para GitHub
5. Deploy no EasyPanel
6. Validar logs em produção

