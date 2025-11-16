# 🚀 Guia - Endpoint Simplificado

## Endpoint Único: POST /api/v1/upload/analyze

### Como Usar

**Via Swagger UI:**
1. Acesse: http://localhost:8000/docs
2. Expanda: `POST /api/v1/upload/analyze`
3. Clique "Try it out"
4. Selecione arquivo no campo "file"
5. (Opcional) Preencha webhook_url
6. Execute

**Via cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/analyze" \
  -F "file=@seu-video.mp4"
```

### Resposta

```json
{
  "analysis_id": "abc123-def456-ghi789",
  "status": "processing",
  "status_url": "http://localhost:8000/api/v1/analysis/abc123-def456-ghi789",
  "message": "Arquivo recebido e análise iniciada. Use status_url para acompanhar o progresso."
}
```

### Consultar Status e Obter Links

```bash
curl "http://localhost:8000/api/v1/analysis/{analysis_id}" | python3 -m json.tool
```

**Resposta (quando completo):**
```json
{
  "id": "abc123-def456-ghi789",
  "status": "completed",
  "progress": 100,
  "clean_video_url": "http://localhost:8000/api/v1/files/abc123.../clean_video",
  "report_url": "http://localhost:8000/api/v1/reports/abc123.../report",
  "original_video_url": "http://localhost:8000/api/v1/files/abc123.../original",
  "classification": "AI_HEVC",
  "confidence": 0.9,
  ...
}
```

### Fluxo Completo

1. **Upload**: POST /api/v1/upload/analyze
   - Selecione arquivo
   - Recebe `analysis_id` imediatamente

2. **Status**: GET /api/v1/analysis/{analysis_id}
   - Consulta progresso
   - Quando completo, recebe links para:
     - Vídeo limpo (`clean_video_url`)
     - Relatório JSON (`report_url`)
     - Vídeo original (`original_video_url`)

### Download dos Arquivos

Use as URLs retornadas no status:

```bash
# Vídeo limpo
curl "{clean_video_url}" -o video-limpo.mp4

# Relatório
curl "{report_url}" -o relatorio.json

# Vídeo original
curl "{original_video_url}" -o video-original.mp4
```

