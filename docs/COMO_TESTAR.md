# 🚀 Como Testar - VID-FINGER API

## ✅ Upload Simplificado - Agora Só Seleciona o Arquivo!

### Passo 1: Upload do Vídeo

**Via Swagger UI (Mais Fácil):**

1. Acesse: http://localhost:8000/docs
2. Expanda `POST /api/v1/upload/init`
3. Clique em **"Try it out"**
4. No campo **"file"**, clique em **"Choose File"**
5. Selecione seu arquivo de vídeo (ex: `andando-neutro-time-square.mp4`)
6. (Opcional) Preencha `webhook_url` se quiser receber notificações
7. Clique em **"Execute"**
8. **Copie o `upload_id`** retornado

**Via cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/init" \
  -F "file=@/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"
```

**Resposta:**
```json
{
  "upload_id": "abc123-def456-ghi789",
  "chunk_size": 5242880,
  "total_chunks": 2,
  "upload_url": "/api/v1/upload/chunk/abc123-def456-ghi789"
}
```

---

### Passo 2: Finalizar Upload e Iniciar Análise

**Via Swagger UI:**
1. Expanda `POST /api/v1/upload/complete/{upload_id}`
2. Cole o `upload_id` do Passo 1
3. Clique em **"Execute"**
4. **Copie o `analysis_id`** retornado

**Via cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/complete/{upload_id}"
```

**Resposta:**
```json
{
  "analysis_id": "xyz789-abc123-def456",
  "status": "pending",
  "message": "Upload concluído. Análise iniciada."
}
```

---

### Passo 3: Consultar Status da Análise

**Via Swagger UI:**
1. Expanda `GET /api/v1/analysis/{analysis_id}`
2. Cole o `analysis_id` do Passo 2
3. Clique em **"Execute"**

**Via cURL:**
```bash
curl "http://localhost:8000/api/v1/analysis/{analysis_id}" | python3 -m json.tool
```

**Resposta:**
```json
{
  "id": "xyz789-abc123-def456",
  "status": "pending",
  "progress": 16,
  "steps": [
    {"name": "upload", "status": "completed", "progress": 100},
    {"name": "metadata_extraction", "status": "pending", "progress": 0},
    ...
  ],
  "classification": null,
  "confidence": null
}
```

**Monitore o `progress`** - quando chegar a 100%, a análise está completa!

---

### Passo 4: Download do Relatório JSON (Diagnóstico)

**Via Swagger UI:**
1. Expanda `GET /api/v1/reports/{analysis_id}/report`
2. Cole o `analysis_id`
3. Clique em **"Execute"**
4. O JSON será exibido na resposta

**Via cURL:**
```bash
# Salvar em arquivo
curl "http://localhost:8000/api/v1/reports/{analysis_id}/report" \
  -o relatorio.json

# Ver no terminal
curl "http://localhost:8000/api/v1/reports/{analysis_id}/report" | \
  python3 -m json.tool | head -50
```

**O relatório contém:**
- ✅ Classificação (REAL_CAMERA, AI_HEVC, UNKNOWN, etc.)
- ✅ Confiança (0.0 a 1.0)
- ✅ Análise PRNU completa
- ✅ Análise FFT temporal
- ✅ Análise de metadados
- ✅ Timeline frame a frame
- ✅ Ferramentas detectadas

---

### Passo 5: Download do Vídeo Limpo

**Via Swagger UI:**
1. Expanda `GET /api/v1/files/{analysis_id}/clean_video`
2. Cole o `analysis_id`
3. Clique em **"Execute"**
4. O arquivo será baixado automaticamente

**Via cURL:**
```bash
curl "http://localhost:8000/api/v1/files/{analysis_id}/clean_video" \
  -o video-limpo.mp4
```

**Importante:** O vídeo limpo só estará disponível após a análise completa!

---

### Passo 6: Download do Vídeo Original

**Via Swagger UI:**
1. Expanda `GET /api/v1/files/{analysis_id}/original`
2. Cole o `analysis_id`
3. Clique em **"Execute"**

**Via cURL:**
```bash
curl "http://localhost:8000/api/v1/files/{analysis_id}/original" \
  -o video-original.mp4
```

---

## 🎯 Teste Rápido Completo

Execute este script:

```bash
#!/bin/bash

API_URL="http://localhost:8000"
VIDEO_FILE="/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"

echo "1️⃣ Upload..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload/init" \
  -F "file=@$VIDEO_FILE")
UPLOAD_ID=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['upload_id'])")
echo "   Upload ID: $UPLOAD_ID"

echo "2️⃣ Complete..."
COMPLETE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload/complete/$UPLOAD_ID")
ANALYSIS_ID=$(echo $COMPLETE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])")
echo "   Analysis ID: $ANALYSIS_ID"

echo "3️⃣ Status..."
curl -s "$API_URL/api/v1/analysis/$ANALYSIS_ID" | python3 -m json.tool | grep -E '"status"|"progress"|"classification"'

echo "4️⃣ Download original..."
curl -s -o /tmp/original.mp4 "$API_URL/api/v1/files/$ANALYSIS_ID/original"
ls -lh /tmp/original.mp4

echo ""
echo "✅ Teste completo!"
echo "   Analysis ID: $ANALYSIS_ID"
echo "   Swagger: $API_URL/docs"
```

---

## 📋 Resumo dos Endpoints

| Endpoint | Método | O que faz |
|----------|--------|-----------|
| `/api/v1/upload/init` | POST | **Upload do arquivo** (só selecionar!) |
| `/api/v1/upload/complete/{id}` | POST | Finalizar upload e iniciar análise |
| `/api/v1/analysis/{id}` | GET | Consultar status da análise |
| `/api/v1/reports/{id}/report` | GET | **Download do relatório JSON** |
| `/api/v1/files/{id}/original` | GET | Download do vídeo original |
| `/api/v1/files/{id}/clean_video` | GET | **Download do vídeo limpo** |

---

## 🌐 Acesse Agora

- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## ⚠️ Notas Importantes

1. **Arquivos grandes**: São divididos automaticamente em chunks internamente
2. **Relatório e vídeo limpo**: Só estarão disponíveis após análise completa
3. **Status da análise**: Monitore via `/api/v1/analysis/{id}` até `progress = 100%`
4. **Webhooks**: Configure `webhook_url` para receber notificações em tempo real

