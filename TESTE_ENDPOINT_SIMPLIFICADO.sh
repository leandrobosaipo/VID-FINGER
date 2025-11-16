#!/bin/bash

API_URL="http://localhost:8000"
VIDEO_FILE="/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     TESTE - ENDPOINT SIMPLIFICADO /api/v1/analyze          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Upload e análise em uma única chamada
echo "1️⃣  Enviando arquivo e iniciando análise..."
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/analyze" \
  -F "file=@$VIDEO_FILE")

echo "$RESPONSE" | python3 -m json.tool

ANALYSIS_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])" 2>/dev/null)

if [ -z "$ANALYSIS_ID" ]; then
    echo "❌ Erro ao iniciar análise"
    exit 1
fi

echo ""
echo "   ✅ Analysis ID: $ANALYSIS_ID"
echo ""

# 2. Consultar status (com links)
echo "2️⃣  Consultando status da análise..."
STATUS_RESPONSE=$(curl -s "$API_URL/api/v1/analysis/$ANALYSIS_ID")
echo "$STATUS_RESPONSE" | python3 -m json.tool | head -30

echo ""
echo "📋 URLs disponíveis no status:"
echo "$STATUS_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"   original_video_url: {data.get('original_video_url', 'null')}\")
print(f\"   clean_video_url: {data.get('clean_video_url', 'null')}\")
print(f\"   report_url: {data.get('report_url', 'null')}\")
" 2>/dev/null

echo ""
echo "✅ Teste completo!"
echo ""
echo "🌐 Swagger UI: $API_URL/docs"
echo "   Procure por: POST /api/v1/analyze"

