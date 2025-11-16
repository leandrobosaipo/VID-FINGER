# Guia Passo a Passo - VID-FINGER API

## Como Usar a API - Passo a Passo Completo

### Pré-requisitos

- Servidor rodando em `http://localhost:8000`
- Arquivo de vídeo para análise (MP4, MOV, AVI, MKV, WebM)
- Navegador ou ferramenta para fazer requisições HTTP

---

## PASSO 1: Upload do Vídeo

### Opção A: Via Swagger UI (Recomendado)

1. **Acesse a documentação:**
   ```
   http://localhost:8000/docs
   ```

2. **Expanda o endpoint:**
   - Procure por `POST /api/v1/upload/init`
   - Clique para expandir

3. **Clique em "Try it out"**

4. **Selecione o arquivo:**
   - No campo `file`, clique em "Choose File"
   - Selecione seu arquivo de vídeo (ex: `video-teste.mp4`)
   - O sistema extrai automaticamente:
     - Nome do arquivo
     - Tamanho em bytes
     - Tipo MIME

5. **Webhook (opcional):**
   - Se quiser receber notificações, preencha `webhook_url`
   - Exemplo: `https://webhook.site/abc123-def456`

6. **Execute:**
   - Clique em "Execute"
   - Copie o `upload_id` retornado

### Opção B: Via cURL

```bash
curl -X POST "http://localhost:8000/api/v1/upload/init" \
  -F "file=@/caminho/para/seu/video.mp4" \
  -F "webhook_url=https://webhook.site/teste"
```

**Resposta esperada:**
```json
{
  "upload_id": "abc123-def456-ghi789",
  "chunk_size": 5242880,
  "total_chunks": 2,
  "upload_url": "/api/v1/upload/chunk/abc123-def456-ghi789"
}
```

**Importante:**
- Se `total_chunks = 1`: Arquivo foi salvo completamente, pule para PASSO 3
- Se `total_chunks > 1`: Continue para PASSO 2

---

## PASSO 2: Upload de Chunks Restantes (se necessário)

**Apenas necessário se `total_chunks > 1`**

### Via Swagger UI:

1. **Expanda:** `POST /api/v1/upload/chunk/{upload_id}`
2. **Cole o `upload_id`** no campo do path
3. **Preencha:**
   - `chunk_number`: 1, 2, 3... (sequencial)
   - `chunk`: Selecione o próximo chunk do arquivo
4. **Execute** para cada chunk restante

### Via cURL:

```bash
# Chunk 1
curl -X POST "http://localhost:8000/api/v1/upload/chunk/{upload_id}" \
  -F "chunk_number=1" \
  -F "chunk=@chunk1.bin"

# Chunk 2 (se houver)
curl -X POST "http://localhost:8000/api/v1/upload/chunk/{upload_id}" \
  -F "chunk_number=2" \
  -F "chunk=@chunk2.bin"
```

**Continue até `progress = 100%`**

---

## PASSO 3: Finalizar Upload e Iniciar Análise

### Via Swagger UI:

1. **Expanda:** `POST /api/v1/upload/complete/{upload_id}`
2. **Cole o `upload_id`**
3. **Webhook (opcional):** Preencha se não preencheu antes
4. **Execute**

### Via cURL:

```bash
curl -X POST "http://localhost:8000/api/v1/upload/complete/{upload_id}" \
  -F "webhook_url=https://webhook.site/teste"
```

**Resposta esperada:**
```json
{
  "analysis_id": "xyz789-abc123-def456",
  "status": "pending",
  "message": "Upload concluído. Análise iniciada."
}
```

**Copie o `analysis_id`** - você precisará dele nos próximos passos!

---

## PASSO 4: Consultar Status da Análise

### Via Swagger UI:

1. **Expanda:** `GET /api/v1/analysis/{analysis_id}`
2. **Cole o `analysis_id`**
3. **Execute**

### Via cURL:

```bash
curl "http://localhost:8000/api/v1/analysis/{analysis_id}"
```

**Resposta esperada:**
```json
{
  "id": "xyz789-abc123-def456",
  "status": "pending",
  "progress": 16,
  "current_step": null,
  "steps": [
    {
      "name": "upload",
      "status": "completed",
      "progress": 100
    },
    {
      "name": "metadata_extraction",
      "status": "pending",
      "progress": 0
    },
    ...
  ],
  "classification": null,
  "confidence": null
}
```

**Monitore o `progress`** - quando chegar a 100%, a análise está completa!

---

## PASSO 5: Download do Relatório JSON (Diagnóstico)

### Via Swagger UI:

1. **Expanda:** `GET /api/v1/reports/{analysis_id}/report`
2. **Cole o `analysis_id`**
3. **Execute**
4. **O JSON será exibido** na resposta

### Via cURL:

```bash
# Salvar relatório em arquivo
curl "http://localhost:8000/api/v1/reports/{analysis_id}/report" \
  -o relatorio.json

# Ver relatório no terminal
curl "http://localhost:8000/api/v1/reports/{analysis_id}/report" | python3 -m json.tool
```

**O relatório contém:**
- Classificação do vídeo (REAL_CAMERA, AI_HEVC, UNKNOWN, etc.)
- Confiança da classificação (0.0 a 1.0)
- Análise PRNU completa
- Análise FFT temporal
- Análise de metadados
- Timeline frame a frame
- Ferramentas detectadas
- Distribuição de origem

---

## PASSO 6: Download do Vídeo Limpo

### Via Swagger UI:

1. **Expanda:** `GET /api/v1/files/{analysis_id}/clean_video`
2. **Cole o `analysis_id`**
3. **Execute**
4. **O arquivo será baixado automaticamente**

### Via cURL:

```bash
# Download do vídeo limpo
curl "http://localhost:8000/api/v1/files/{analysis_id}/clean_video" \
  -o video-limpo.mp4
```

**Importante:**
- O vídeo limpo só estará disponível após a análise completa
- Se receber erro 404, aguarde a análise terminar

---

## PASSO 7: Download do Vídeo Original

### Via Swagger UI:

1. **Expanda:** `GET /api/v1/files/{analysis_id}/original`
2. **Cole o `analysis_id`**
3. **Execute**

### Via cURL:

```bash
curl "http://localhost:8000/api/v1/files/{analysis_id}/original" \
  -o video-original.mp4
```

---

## Resumo dos Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/upload/init` | POST | Upload do arquivo (extrai info automaticamente) |
| `/api/v1/upload/chunk/{id}` | POST | Upload de chunk (se arquivo > 5MB) |
| `/api/v1/upload/complete/{id}` | POST | Finalizar upload e iniciar análise |
| `/api/v1/analysis/{id}` | GET | Consultar status da análise |
| `/api/v1/reports/{id}/report` | GET | Download do relatório JSON (diagnóstico) |
| `/api/v1/files/{id}/original` | GET | Download do vídeo original |
| `/api/v1/files/{id}/clean_video` | GET | Download do vídeo limpo |

---

## Exemplo Completo - Fluxo Rápido

```bash
# 1. Upload
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/upload/init" \
  -F "file=@video.mp4")
UPLOAD_ID=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['upload_id'])")

# 2. Complete
COMPLETE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/upload/complete/$UPLOAD_ID")
ANALYSIS_ID=$(echo $COMPLETE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])")

# 3. Aguardar análise (verificar status periodicamente)
curl "http://localhost:8000/api/v1/analysis/$ANALYSIS_ID"

# 4. Download relatório
curl "http://localhost:8000/api/v1/reports/$ANALYSIS_ID/report" -o relatorio.json

# 5. Download vídeo limpo
curl "http://localhost:8000/api/v1/files/$ANALYSIS_ID/clean_video" -o video-limpo.mp4
```

---

## Troubleshooting

### Erro: "Arquivo muito grande"
- Arquivos > 5MB precisam ser enviados em chunks
- Use o endpoint `/upload/chunk/{upload_id}` para enviar chunks restantes

### Erro: "Análise não encontrada"
- Verifique se o `analysis_id` está correto
- Certifique-se de ter executado `/upload/complete` antes

### Erro: "Relatório ainda não foi gerado"
- A análise pode estar em andamento
- Verifique o status em `/analysis/{analysis_id}`
- Aguarde até `progress = 100%`

### Erro: "Vídeo limpo ainda não foi gerado"
- O vídeo limpo só é gerado após análise completa
- Verifique se `status = "completed"` em `/analysis/{analysis_id}`

---

## Teste Rápido

Execute este script para testar tudo:

```bash
#!/bin/bash

API_URL="http://localhost:8000"
VIDEO_FILE="/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"

echo "1. Fazendo upload..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload/init" \
  -F "file=@$VIDEO_FILE")
echo "$UPLOAD_RESPONSE" | python3 -m json.tool

UPLOAD_ID=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['upload_id'])")
echo "Upload ID: $UPLOAD_ID"

echo -e "\n2. Finalizando upload..."
COMPLETE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload/complete/$UPLOAD_ID")
echo "$COMPLETE_RESPONSE" | python3 -m json.tool

ANALYSIS_ID=$(echo $COMPLETE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])")
echo "Analysis ID: $ANALYSIS_ID"

echo -e "\n3. Verificando status..."
curl -s "$API_URL/api/v1/analysis/$ANALYSIS_ID" | python3 -m json.tool

echo -e "\n4. Para baixar relatório:"
echo "curl '$API_URL/api/v1/reports/$ANALYSIS_ID/report' -o relatorio.json"

echo -e "\n5. Para baixar vídeo limpo (após análise completa):"
echo "curl '$API_URL/api/v1/files/$ANALYSIS_ID/clean_video' -o video-limpo.mp4"
```

---

## Próximos Passos

Após implementar as tasks Celery, a análise será processada automaticamente e você poderá:
- Receber webhooks em tempo real
- Consultar progresso em tempo real
- Baixar relatório e vídeo limpo automaticamente

