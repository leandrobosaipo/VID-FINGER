# VID-FINGER V3

**Video Intelligent Detection Fingerprint V3** - Sistema Forense Anti-Spoof + Raw IA Extractor

## 📋 Descrição

VID-FINGER V3 é um sistema forense completo capaz de:

1. **Detectar IA mesmo parcialmente** - Identifica trechos de vídeo gerados por IA
2. **Detectar spoofing de metadados** - Identifica metadados falsos, copiados ou manipulados
3. **Identificar ferramentas de edição** - Detecta Premiere, CapCut, VN, Davinci, FFmpeg, etc.
4. **Separar sinais reais vs IA** - Análise frame a frame
5. **Gerar vídeo limpo** - Remove fingerprints de IA, gerando vídeo "indetectável"

## 🎯 Entregáveis Obrigatórios

O sistema **sempre gera 3 arquivos**:

1. **`original_input.(mp4/mov)`** → Arquivo original copiado em `output/original/`
2. **`analysis_report.json`** → Relatório pericial completo em `output/reports/`
3. **`clean_IA_version.mp4`** → Vídeo limpo sem fingerprints em `output/clean/`

## 🚀 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- FFmpeg instalado no sistema

### Instalar FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Baixe de [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

### Instalar Dependências Python

```bash
pip install -r requirements.txt
```

**Dependências principais:**
- numpy (análise numérica)
- scipy (FFT e processamento de sinal)
- opencv-python (processamento de frames)
- prnu (análise PRNU)

## 📖 Uso

### Comando Básico

```bash
python3 src/cli.py --input "/caminho/do/video.mp4"
```

### Especificar Diretório de Saída

```bash
python3 src/cli.py --input video.mp4 --output-dir ./output
```

### Pular Geração do Vídeo Limpo (Mais Rápido)

```bash
python3 src/cli.py --input video.mp4 --skip-clean
```

### Exemplo Completo

```bash
python3 src/cli.py --input "/Users/leandrobosaipo/Downloads/13h - Lavanderia sem erro.mp4"
```

**Saída no terminal:**
```
======================================================================
VID-FINGER V3 - Relatório Forense de Análise
======================================================================

Arquivo: 13h - Lavanderia sem erro.mp4
Codec: hevc
Encoder: Lavc60.31.102 libx265
Resolução: 480x872
Frame Rate: 30.0 fps
Duração: 9.8s

----------------------------------------------------------------------
Classificação: AI_HEVC
Confiança: 90.00% (alta)
Razão: Codec HEVC com padrões suspeitos de IA

Ferramentas Detectadas:
  • FFmpeg (confiança: 40.0%)

Distribuição de Origem:
  - real_camera: 100.0%
----------------------------------------------------------------------

Entregáveis Gerados:
  1. Original: output/original/13h - Lavanderia sem erro.mp4
  2. Relatório: output/reports/report_13h - Lavanderia sem erro_2025-11-14_171632.json
  3. Vídeo Limpo: output/clean/clean_IA_version_13h - Lavanderia sem erro.mp4
======================================================================
```

## 📊 Formato do Relatório JSON

O relatório pericial completo inclui:

```json
{
  "file": "video.mp4",
  "classification": "AI_HEVC",
  "confidence": 0.9,
  "confidence_level": "alta",
  "most_likely_model": "Outro modelo de IA",
  "model_probabilities": {
    "Sora (OpenAI)": 0.2,
    "Runway Gen-3": 0.4,
    "Outro modelo de IA": 0.6
  },
  "prnu_analysis": {
    "general_analysis": { ... },
    "frame_analysis": [ ... ]
  },
  "fft_analysis": {
    "diffusion_detected": true,
    "confidence": 0.75,
    "model_signatures": { ... },
    "jitter_analysis": { ... }
  },
  "metadata_integrity": {
    "integrity_status": "edited",
    "tool_signatures": [ ... ],
    "spoofing_analysis": { ... }
  },
  "timeline": [
    {"frame": 0, "origin": "ai", "confidence": 0.94},
    {"frame": 1, "origin": "real_camera", "confidence": 0.85}
  ],
  "hybrid_analysis": {
    "is_hybrid": false,
    "real_percentage": 0.0,
    "ai_percentage": 100.0
  },
  "tool_signatures": [
    {"tool": "FFmpeg", "confidence": 0.4}
  ]
}
```

## 🔍 Classificações V3

### REAL_CAMERA
Vídeos capturados por câmeras reais.

**Indicadores:**
- Metadados de câmera presentes
- Ruído PRNU físico consistente
- Jitter temporal natural
- Padrões de movimento irregulares

**Confiança:** 60-95%

### AI_HEVC / AI_AV1
Vídeos gerados por IA com codec HEVC ou AV1.

**Indicadores:**
- Codec HEVC/AV1 sem metadados de câmera
- Ruído PRNU "perfeito demais"
- Movimento muito suave (baixo jitter)
- Padrões FFT de difusão

**Confiança:** 40-95%

### SPOOFED_METADATA
Vídeos com metadados falsos ou copiados.

**Indicadores:**
- Contradições entre metadados e encoder
- Metadados copiados de outro vídeo
- Incompatibilidades técnicas

**Confiança:** 60-95%

### HYBRID_CONTENT
Vídeos com partes reais e partes geradas por IA.

**Indicadores:**
- Timeline mostra transições entre real e IA
- Distribuição mista de origens

**Confiança:** 50-95%

### UNKNOWN
Casos não classificados com confiança suficiente.

**Confiança:** 50%

## 🧠 Módulos Técnicos

### 1. PRNU Detector
- Extrai ruído PRNU dos frames
- Compara com padrões de sensores reais
- Detecta "ruído perfeito demais" (IA) vs "ruído físico" (câmera)

### 2. FFT Temporal
- Análise espectral temporal
- Detecta padrões de difusão
- Identifica movimento muito suave (típico de IA)
- Detecta ausência de jitter

### 3. Metadata Integrity
- Detecta metadados spoofed
- Identifica ferramentas de edição
- Detecta contradições técnicas

### 4. Timeline Analyzer
- Análise frame a frame
- Combina resultados de todos os módulos
- Gera timeline de origem
- Detecta conteúdo híbrido

### 5. Cleaner
- Remove metadados
- Re-encoda com preset neutro
- Randomiza QP
- Adiciona jitter microtemporal
- Gera vídeo sem fingerprints detectáveis

## 🏗️ Estrutura do Projeto

```
VID-FINGER/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ffprobe_reader.py      # Leitura de metadados
│   │   ├── fingerprint_logic.py    # Análise de padrões técnicos
│   │   ├── video_classifier.py     # Classificação heurística
│   │   ├── prnu_detector.py        # Detecção PRNU
│   │   ├── fft_temporal.py         # Análise FFT temporal
│   │   ├── metadata_integrity.py   # Integridade de metadados
│   │   ├── timeline_analyzer.py    # Timeline frame a frame
│   │   └── cleaner.py              # Limpeza de vídeo
│   ├── __init__.py
│   ├── cli.py                      # Interface de linha de comando
│   └── utils.py                    # Utilitários
├── output/
│   ├── original/                   # Arquivos originais copiados
│   ├── reports/                    # Relatórios JSON
│   └── clean/                      # Vídeos limpos gerados
├── requirements.txt                # Dependências Python
└── README.md                       # Esta documentação
```

## 🧪 Testes

### Teste Básico

```bash
python3 src/cli.py --input "/caminho/do/seu/video.mp4"
```

### Teste com Vídeo de IA

```bash
python3 src/cli.py --input "/Users/leandrobosaipo/Downloads/13h - Lavanderia sem erro.mp4"
```

**Resultado esperado:**
- Classificação: AI_HEVC (alta confiança)
- 3 arquivos gerados: original, relatório, vídeo limpo

### Validar Vídeo Limpo

```bash
python3 src/cli.py --input "output/clean/clean_IA_version_<nome>.mp4" --skip-clean
```

**Resultado esperado:**
- Classificação: UNKNOWN (confiança baixa)
- Indica que fingerprints foram removidos

## ✨ Funcionalidades V3

### Detecção Avançada

- **Anti-Spoof**: Detecta IA mesmo com metadados falsos
- **Frame a Frame**: Identifica trechos reais vs IA
- **Ferramentas**: Detecta Premiere, CapCut, Davinci, FFmpeg
- **Híbrido**: Identifica conteúdo misto (real + IA)

### Análise Forense

- **PRNU**: Ruído do sensor para identificar origem
- **FFT Temporal**: Padrões espectrais de difusão
- **Timeline**: Origem de cada frame
- **Integridade**: Verificação de metadados

### Limpeza de Vídeo

- Remove metadados
- Re-encoda neutro
- Randomiza QP
- Adiciona jitter artificial
- Gera vídeo "indetectável"

## ⚠️ Limitações

- Análise PRNU pode ser lenta em vídeos muito longos
- Geração de vídeo limpo requer FFmpeg e pode demorar
- Alguns padrões de IA podem não ser detectados se muito processados

## 🔧 Troubleshooting

### Erro: "ffprobe não encontrado"

Instale FFmpeg seguindo as instruções na seção de Instalação.

### Erro: "ModuleNotFoundError: No module named 'cv2'"

Instale OpenCV:
```bash
pip install opencv-python
```

### Erro: "ModuleNotFoundError: No module named 'prnu'"

A biblioteca `prnu` pode não estar disponível. O sistema funciona sem ela, mas a análise PRNU será limitada.

### Vídeo limpo não gerado

Verifique se FFmpeg está instalado e funcionando:
```bash
ffmpeg -version
```

## 📝 Licença

Este é um projeto para fins de demonstração e validação.

## 🚧 Roadmap Futuro (v4, v5)

- Modelo de ML treinado para fingerprint SORA
- Detector de difusão baseado em PatchGAN
- Ferramenta CLI + GUI web
- API REST para automações
- Exportar relatório pericial assinado (PDF digital)
