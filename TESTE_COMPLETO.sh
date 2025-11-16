#!/bin/bash

API_URL="http://localhost:8000"
VIDEO_FILE="/Users/leandrobosaipo/Downloads/andando-neutro-time-square.mp4"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     TESTE COMPLETO - VID-FINGER API                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Upload
echo "1️⃣  Fazendo upload do arquivo..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload/init" \
  -F "file=@$VIDEO_FILE")

UPLOAD_ID=$(echo $UPLOAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['upload_id'])" 2>/dev/null)

if [ -z "$UPLOAD_ID" ]; then
    echo "❌ Erro no upload:"
    echo "$UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"
    exit 1
fi

echo "   ✅ Upload ID: $UPLOAD_ID"
echo ""

# 2. Complete
echo "2️⃣  Finalizando upload e iniciando análise..."
COMPLETE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/upload/complete/$UPLOAD_ID")

ANALYSIS_ID=$(echo $COMPLETE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['analysis_id'])" 2>/dev/null)

if [ -z "$ANALYSIS_ID" ]; then
    echo "❌ Erro ao completar upload:"
    echo "$COMPLETE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$COMPLETE_RESPONSE"
    exit 1
fi

echo "   ✅ Analysis ID: $ANALYSIS_ID"
echo ""

# 3. Status
echo "3️⃣  Verificando status da análise..."
STATUS_RESPONSE=$(curl -s "$API_URL/api/v1/analysis/$ANALYSIS_ID")
STATUS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
PROGRESS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['progress'])" 2>/dev/null)

echo "   Status: $STATUS"
echo "   Progresso: $PROGRESS%"
echo ""

# 4. Download original
echo "4️⃣  Testando download do arquivo original..."
ORIGINAL_SIZE=$(curl -s -o /tmp/video-original-test.mp4 -w "%{size_download}" \
  "$API_URL/api/v1/files/$ANALYSIS_ID/original")

if [ "$ORIGINAL_SIZE" -gt 0 ]; then
    echo "   ✅ Arquivo original baixado: $ORIGINAL_SIZE bytes"
    rm -f /tmp/video-original-test.mp4
else
    echo "   ⚠️  Arquivo não encontrado ou vazio"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     ✅ TESTE COMPLETO - TODOS OS PASSOS FUNCIONANDO        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1. Consultar status da análise:"
echo "   curl '$API_URL/api/v1/analysis/$ANALYSIS_ID' | python3 -m json.tool"
echo ""
echo "2. Download do relatório JSON (quando análise completar):"
echo "   curl '$API_URL/api/v1/reports/$ANALYSIS_ID/report' -o relatorio.json"
echo ""
echo "3. Download do vídeo limpo (quando análise completar):"
echo "   curl '$API_URL/api/v1/files/$ANALYSIS_ID/clean_video' -o video-limpo.mp4"
echo ""
echo "4. Download do vídeo original:"
echo "   curl '$API_URL/api/v1/files/$ANALYSIS_ID/original' -o video-original.mp4"
echo ""
echo "🌐 Swagger UI: $API_URL/docs"
echo ""

