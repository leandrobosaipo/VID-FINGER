# Webhooks por Etapa de Análise

## Visão Geral

O sistema VID-FINGER agora envia webhooks detalhados a cada etapa do processamento de análise, permitindo criar dashboards em tempo real e monitorar o progresso de forma granular.

## Eventos de Webhook

### Eventos Disponíveis

1. **`analysis.started`** - Análise iniciada
2. **`analysis.step.started`** - Etapa iniciada
3. **`analysis.step.completed`** - Etapa concluída
4. **`analysis.completed`** - Análise concluída
5. **`analysis.failed`** - Análise falhou

## Estrutura do Payload

### Webhook de Etapa (analysis.step.started / analysis.step.completed)

```json
{
  "event": "analysis.step.started",
  "analysis_id": "7b4b273a-37b3-4a9a-9b4c-1399f88c87d8",
  "timestamp": "2025-11-18T10:04:17.123456Z",
  "data": {
    "current_step": {
      "name": "metadata_extraction",
      "status": "running",
      "started_at": "2025-11-18T10:04:17.123456Z",
      "completed_at": null,
      "duration_seconds": 0.0,
      "result": null
    },
    "completed_steps": [],
    "pending_steps": [
      "prnu",
      "fft",
      "classification",
      "cleaning"
    ],
    "statistics": {
      "total_steps": 6,
      "completed_count": 0,
      "running_count": 1,
      "pending_count": 5,
      "progress_percentage": 8.33,
      "total_duration_seconds": 0.0,
      "estimated_remaining_seconds": null
    },
    "analysis": {
      "status": "analyzing",
      "classification": null,
      "confidence": null
    }
  }
}
```

### Webhook de Etapa Concluída

```json
{
  "event": "analysis.step.completed",
  "analysis_id": "7b4b273a-37b3-4a9a-9b4c-1399f88c87d8",
  "timestamp": "2025-11-18T10:04:21.456789Z",
  "data": {
    "current_step": null,
    "completed_steps": [
      {
        "name": "metadata_extraction",
        "status": "completed",
        "started_at": "2025-11-18T10:04:17.123456Z",
        "completed_at": "2025-11-18T10:04:21.456789Z",
        "duration_seconds": 4.33,
        "result": {
          "metadata_extracted": true,
          "codec": "h264",
          "duration": 30.5,
          "resolution": "1920x1080",
          "frame_rate": "30/1"
        }
      }
    ],
    "pending_steps": [
      "prnu",
      "fft",
      "classification",
      "cleaning"
    ],
    "statistics": {
      "total_steps": 6,
      "completed_count": 1,
      "running_count": 0,
      "pending_count": 4,
      "progress_percentage": 16.67,
      "total_duration_seconds": 4.33,
      "estimated_remaining_seconds": 17.32
    },
    "analysis": {
      "status": "analyzing",
      "classification": null,
      "confidence": null
    }
  }
}
```

## Etapas do Processamento

As seguintes etapas são rastreadas e geram webhooks:

1. **upload** - Upload do arquivo (já concluída na criação)
2. **metadata_extraction** - Extração de metadados do vídeo
3. **prnu** - Análise PRNU (ruído do sensor)
4. **fft** - Análise FFT temporal
5. **classification** - Classificação do vídeo
6. **report_generation** - Geração do relatório JSON
7. **cleaning** - Geração do vídeo limpo

## Resultados por Etapa

Cada etapa pode incluir resultados específicos no campo `result`:

### metadata_extraction
```json
{
  "metadata_extracted": true,
  "codec": "h264",
  "duration": 30.5,
  "resolution": "1920x1080",
  "frame_rate": "30/1"
}
```

### prnu
```json
{
  "prnu_detected": true,
  "confidence": 0.85
}
```

### fft
```json
{
  "fft_analysis_completed": true,
  "diffusion_detected": false
}
```

### classification
```json
{
  "classification": "REAL_CAMERA",
  "confidence": 0.92
}
```

### report_generation
```json
{
  "report_generated": true,
  "report_file_id": "5cc521a2-9b99-4a1e-8894-b2006e8c3e08",
  "cdn_url": "https://nyc3.digitaloceanspaces.com/cod5/vid-finger/analyses/..."
}
```

### cleaning
```json
{
  "clean_video_generated": true,
  "clean_video_id": "92eac802-18d0-4afe-a9f9-0d6de43a2f00",
  "cdn_url": "https://nyc3.digitaloceanspaces.com/cod5/vid-finger/analyses/..."
}
```

## Configuração

### Enviar Análise com Webhook

Ao criar uma análise, inclua o parâmetro `webhook_url`:

```bash
curl -X POST "http://localhost:8000/api/v1/upload/analyze" \
  -F "file=@video.mp4" \
  -F "webhook_url=https://seu-webhook.com/receive"
```

### Usando webhook.site para Testes

1. Acesse https://webhook.site
2. Copie sua URL única
3. Use no parâmetro `webhook_url`:

```bash
curl -X POST "http://localhost:8000/api/v1/upload/analyze" \
  -F "file=@video.mp4" \
  -F "webhook_url=https://webhook.site/unique-id"
```

## Integração com n8n

### Configuração Básica

1. Crie um novo workflow no n8n
2. Adicione um nó **Webhook** (trigger)
3. Configure o método como **POST**
4. Copie a URL do webhook gerada
5. Use essa URL no parâmetro `webhook_url` ao enviar análises

### Exemplo de Workflow n8n

```
Webhook (Trigger)
  ↓
IF Node (verificar event)
  ├─ analysis.step.started → Atualizar Dashboard
  ├─ analysis.step.completed → Atualizar Dashboard
  └─ analysis.completed → Notificar Conclusão
  ↓
Set Node (extrair dados)
  ↓
HTTP Request (salvar em banco/dashboard)
```

### Exemplo de Filtro por Evento

No n8n, use um nó **IF** para filtrar eventos:

```javascript
// Condição: event === "analysis.step.completed"
{{ $json.body.event }} === "analysis.step.completed"
```

### Exemplo de Extração de Dados

```javascript
// Progresso
{{ $json.body.data.statistics.progress_percentage }}%

// Etapa atual
{{ $json.body.data.current_step.name }}

// Tempo decorrido
{{ $json.body.data.statistics.total_duration_seconds }}s

// Tempo estimado restante
{{ $json.body.data.statistics.estimated_remaining_seconds }}s
```

## Estatísticas Disponíveis

O campo `statistics` fornece:

- **total_steps**: Total de etapas (6)
- **completed_count**: Etapas concluídas
- **running_count**: Etapas em execução (0 ou 1)
- **pending_count**: Etapas pendentes
- **progress_percentage**: Progresso percentual (0-100)
- **total_duration_seconds**: Tempo total decorrido
- **estimated_remaining_seconds**: Tempo estimado restante (baseado na média)

## Tratamento de Erros

- Webhooks não bloqueiam o processamento
- Erros de webhook são logados mas não interrompem a análise
- Sistema de retry automático (3 tentativas com backoff exponencial)
- Timeout configurável (padrão: 10 segundos)

## Variáveis de Ambiente

```bash
# Timeout para webhooks em segundos
WEBHOOK_TIMEOUT=10

# Número de tentativas para webhooks
WEBHOOK_RETRY_ATTEMPTS=3
```

## Exemplo Completo de Fluxo

1. **Upload iniciado** → `analysis.started`
2. **metadata_extraction iniciada** → `analysis.step.started` (metadata_extraction)
3. **metadata_extraction concluída** → `analysis.step.completed` (metadata_extraction)
4. **prnu iniciada** → `analysis.step.started` (prnu)
5. **prnu concluída** → `analysis.step.completed` (prnu)
6. **fft iniciada** → `analysis.step.started` (fft)
7. **fft concluída** → `analysis.step.completed` (fft)
8. **classification iniciada** → `analysis.step.started` (classification)
9. **classification concluída** → `analysis.step.completed` (classification)
10. **report_generation iniciada** → `analysis.step.started` (report_generation)
11. **report_generation concluída** → `analysis.step.completed` (report_generation)
12. **cleaning iniciada** → `analysis.step.started` (cleaning)
13. **cleaning concluída** → `analysis.step.completed` (cleaning)
14. **Análise concluída** → `analysis.completed`

## Dashboard Sugerido

Com os webhooks, você pode criar um dashboard que mostra:

- **Progresso geral**: Barra de progresso baseada em `progress_percentage`
- **Etapa atual**: Nome e status da etapa em execução
- **Etapas concluídas**: Lista com tempo de duração de cada uma
- **Etapas pendentes**: Lista das próximas etapas
- **Estatísticas**: Tempo total, tempo estimado restante
- **Resultados**: Classificação e confiança quando disponível
- **Gráficos**: Tempo por etapa, distribuição de tempo

## Troubleshooting

### Webhooks não estão sendo recebidos

1. Verifique se `webhook_url` foi fornecido corretamente
2. Verifique logs do servidor para erros de webhook
3. Teste a URL do webhook manualmente (webhook.site)
4. Verifique firewall/proxy que possa estar bloqueando

### Webhooks estão atrasados

- Webhooks são enviados de forma assíncrona
- Erros não bloqueiam o processamento
- Verifique `WEBHOOK_TIMEOUT` e `WEBHOOK_RETRY_ATTEMPTS`

### Payload incompleto

- Certifique-se de que o banco de dados está atualizado
- Verifique se todas as etapas foram executadas corretamente
- Alguns campos podem ser `null` se ainda não disponíveis

