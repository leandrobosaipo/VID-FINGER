# PRD - VID-FINGER V3
## Product Requirements Document
### Sistema Forense de Detecção de Vídeos Gerados por IA

**Versão:** 3.0  
**Data:** 2025-11-15  
**Status:** Implementado  
**Autor:** Equipe VID-FINGER

---

## 1. VISÃO GERAL DO PRODUTO

### 1.1 Propósito
VID-FINGER V3 é um sistema forense completo para análise, detecção e classificação de vídeos gerados por inteligência artificial, com capacidade de identificar conteúdo híbrido (real + IA), detectar spoofing de metadados e gerar versões "limpas" de vídeos sem fingerprints detectáveis.

### 1.2 Problema que Resolve
Com o avanço de modelos de geração de vídeo por IA (Sora, Runway Gen-3, Veo, etc.), há necessidade de:
- Detectar vídeos gerados por IA mesmo quando parcialmente processados
- Identificar manipulação de metadados (spoofing)
- Analisar conteúdo híbrido (trechos reais + trechos IA)
- Gerar evidências periciais para investigações
- Remover fingerprints de IA de vídeos processados

### 1.3 Público-Alvo
- Peritos forenses digitais
- Investigadores de segurança
- Analistas de conteúdo
- Pesquisadores em deepfake detection
- Profissionais de verificação de mídia

### 1.4 Objetivos de Negócio
- Fornecer ferramenta confiável de detecção de IA em vídeos
- Gerar relatórios periciais completos e auditáveis
- Suportar investigações legais e forenses
- Manter alta taxa de precisão na classificação

---

## 2. FUNCIONALIDADES PRINCIPAIS

### 2.1 Detecção de Vídeos Gerados por IA

#### 2.1.1 Classificações Suportadas
- **REAL_CAMERA**: Vídeos capturados por câmeras reais
- **AI_HEVC**: Vídeos gerados por IA com codec HEVC
- **AI_AV1**: Vídeos gerados por IA com codec AV1
- **SPOOFED_METADATA**: Vídeos com metadados falsos ou copiados
- **HYBRID_CONTENT**: Vídeos com partes reais e partes geradas por IA
- **UNKNOWN**: Casos não classificados com confiança suficiente

#### 2.1.2 Modelos de IA Detectados
- Sora (OpenAI)
- Runway Gen-3
- Gemini Veo (Google)
- Pika Labs
- Luma Dream Machine
- Outros modelos de IA

#### 2.1.3 Níveis de Confiança
- **Alta**: ≥ 80% de confiança
- **Média**: 60-79% de confiança
- **Baixa**: < 60% de confiança

### 2.2 Análise Forense Multi-Camada

#### 2.2.1 Análise PRNU (Photo Response Non-Uniformity)
- Extração de ruído do sensor de câmera
- Comparação com baseline de sensores reais
- Detecção de "ruído perfeito demais" (indicador de IA)
- Análise frame a frame do ruído PRNU

**Técnicas:**
- Filtro de alta frequência para isolamento de ruído
- Análise de variância e consistência entre frames
- Correlação com perfis de sensores conhecidos

#### 2.2.2 Análise FFT Temporal
- Análise espectral temporal do vídeo
- Detecção de padrões de difusão (típicos de IA)
- Análise de movimento e jitter temporal
- Identificação de movimento "muito suave" (indicador de IA)

**Features Extraídas:**
- Luminância temporal
- Movimento entre frames
- Textura espacial
- Entropia espectral
- Frequências dominantes

#### 2.2.3 Análise de Integridade de Metadados
- Verificação de metadados de câmera (Make, Model)
- Detecção de metadados QuickTime
- Identificação de contradições técnicas
- Detecção de metadados "limpos demais" (indicador de IA)
- Análise de spoofing (metadados copiados ou falsos)

#### 2.2.4 Análise de Fingerprint Técnico
- Análise de codec (H.264, HEVC, AV1)
- Identificação de encoder (libx264, libx265, Lavf, etc.)
- Análise de padrão GOP (Group of Pictures)
- Análise de padrão QP (Quantization Parameter)
- Detecção de re-encode
- Identificação de encoder minimalista

#### 2.2.5 Análise de Timeline Frame a Frame
- Combinação de evidências de todos os módulos
- Classificação de origem por frame (real_camera, ai, spoofed)
- Detecção de conteúdo híbrido
- Identificação de transições entre real e IA
- Cálculo de percentuais de conteúdo real vs IA

### 2.3 Detecção de Ferramentas de Edição

#### 2.3.1 Ferramentas Detectadas
- Adobe Premiere Pro
- CapCut
- VN Video Editor
- DaVinci Resolve
- FFmpeg
- Sora (OpenAI)
- Runway

#### 2.3.2 Métodos de Detecção
- Análise de assinaturas no encoder
- Identificação de tags de formato específicas
- Análise de metadados de software
- Confiança por ferramenta (0.0 a 1.0)

### 2.4 Geração de Vídeo Limpo

#### 2.4.1 Pipeline de Limpeza
1. **Remoção de Metadados**: Remove todos os metadados do vídeo
2. **Re-encode Neutro**: Re-encoda com preset neutro (libx264, CRF 17±2, preset slow)
3. **Adição de Jitter Temporal**: Adiciona ruído temporal mínimo para quebrar padrões de IA

#### 2.4.2 Objetivo
Gerar vídeo sem fingerprints detectáveis de IA, simulando características de câmera real.

### 2.5 Calibração de Sensor Baseline

#### 2.5.1 Funcionalidade
Permite calibrar perfil de sensor real (ex: iPhone 11) para comparação posterior.

#### 2.5.2 Uso
```bash
python3 src/cli.py --calibrate video_real.mp4 --baseline-profile sensor_profile.json
```

#### 2.5.3 Dados Armazenados
- Variância PRNU média
- Correlação média
- Características temporais
- Número de frames analisados

---

## 3. ENTREGÁVEIS OBRIGATÓRIOS

O sistema **sempre gera 3 arquivos** para cada análise:

### 3.1 Arquivo Original
- **Localização**: `output/original/`
- **Nome**: `[seo-base]-original.[ext]`
- **Conteúdo**: Cópia exata do arquivo de entrada
- **Propósito**: Preservar evidência original

### 3.2 Relatório Pericial JSON
- **Localização**: `output/reports/`
- **Nome**: `[seo-base]-forensic-report-[timestamp].json`
- **Conteúdo**: Relatório completo com todas as análises
- **Estrutura**: Ver seção 4.1

### 3.3 Vídeo Limpo
- **Localização**: `output/clean/`
- **Nome**: `[descricao-humana]-[DD-MM-YYYY-HH-MM-SS].mp4`
- **Conteúdo**: Vídeo sem fingerprints de IA
- **Propósito**: Versão "indetectável" do vídeo

---

## 4. ESTRUTURA DE DADOS

### 4.1 Estrutura do Relatório JSON

```json
{
  "file": "nome_arquivo.mp4",
  "file_path": "/caminho/completo/arquivo.mp4",
  "codec": "hevc",
  "encoder": "Lavc60.31.102 libx265",
  "major_brand": "isom",
  "compatible_brands": ["isom", "iso2", "avc1", "mp41"],
  "duration": 9.8,
  "bit_rate": 1234567,
  "frame_rate": 30.0,
  "width": 480,
  "height": 872,
  "gop_estimate": 30,
  "qp_pattern": "suspicious_minimal",
  
  "classification": "AI_HEVC",
  "confidence": 0.90,
  "confidence_level": "alta",
  "reason": "Codec HEVC com padrões suspeitos de IA",
  "most_likely_model": "Sora (OpenAI)",
  "model_probabilities": {
    "Sora (OpenAI)": 0.6,
    "Runway Gen-3": 0.4,
    "Outro modelo de IA": 0.2
  },
  
  "prnu_analysis": {
    "general_analysis": {
      "prnu_detected": true,
      "noise_consistency": 0.85,
      "noise_variance": 2.5,
      "is_perfect_noise": true,
      "is_physical_sensor": false,
      "confidence": 0.75
    },
    "frame_analysis": [
      {
        "frame": 0,
        "origin": "ai",
        "confidence": 0.85,
        "noise_variance": 2.3
      }
    ]
  },
  
  "fft_analysis": {
    "diffusion_detected": true,
    "confidence": 0.75,
    "model_signatures": {
      "has_sora_pattern": false,
      "has_runway_pattern": true
    },
    "motion_analysis": {
      "has_ai_pattern": true,
      "smoothness_score": 0.90,
      "jitter_analysis": {
        "has_natural_jitter": false,
        "jitter_variance": 0.05
      }
    }
  },
  
  "metadata_integrity": {
    "integrity_status": "edited",
    "tool_signatures": [
      {
        "tool": "FFmpeg",
        "confidence": 0.40
      }
    ],
    "spoofing_analysis": {
      "is_spoofed": false,
      "confidence": 0.0
    }
  },
  
  "timeline": [
    {
      "frame": 0,
      "origin": "ai",
      "confidence": 0.94,
      "evidence_scores": {
        "real_camera": 0.1,
        "ai": 0.94,
        "spoofed": 0.0
      }
    }
  ],
  
  "hybrid_analysis": {
    "is_hybrid": false,
    "real_percentage": 0.0,
    "ai_percentage": 100.0,
    "transitions": []
  },
  
  "timeline_summary": {
    "origin_distribution": {
      "ai": 100.0,
      "real_camera": 0.0
    },
    "total_frames": 294
  },
  
  "tool_signatures": [
    {
      "tool": "FFmpeg",
      "confidence": 0.40
    }
  ],
  
  "fingerprint": {
    "camera_metadata": {
      "make": null,
      "model": null,
      "has_quicktime_metadata": false,
      "has_camera_metadata": false
    },
    "qp_analysis": {
      "qp_available": false,
      "pattern": "suspicious_minimal"
    },
    "gop_analysis": {
      "gop_size": 30,
      "is_regular": true,
      "regularity_confidence": 0.85
    },
    "encoder_signals": {
      "encoder_name": "Lavc60.31.102 libx265",
      "codec": "hevc",
      "is_ai_encoder": false,
      "is_reencode": true,
      "reencode_confidence": 0.95
    },
    "clean_metadata_analysis": {
      "is_extremely_clean": true,
      "total_tags": 3
    }
  }
}
```

---

## 5. ARQUITETURA TÉCNICA

### 5.1 Fluxo de Processamento

```
1. Validação de Arquivo
   ↓
2. Extração de Metadados (ffprobe)
   ↓
3. Estimativa de GOP e Regularidade
   ↓
4. Cálculo de Fingerprint Técnico
   ↓
5. Carregamento de Baseline Profile (se disponível)
   ↓
6. Análise PRNU (com baseline se disponível)
   ↓
7. Análise FFT Temporal
   ↓
8. Verificação de Integridade de Metadados
   ↓
9. Classificação Preliminar
   ↓
10. Análise de Timeline Frame a Frame
    ↓
11. Classificação Final
    ↓
12. Geração de Nomes SEO-friendly
    ↓
13. Cópia do Arquivo Original
    ↓
14. Geração de Relatório Pericial
    ↓
15. Análise de Conteúdo Visual/Audio (opcional)
    ↓
16. Geração de Vídeo Limpo (se não --skip-clean)
    ↓
17. Exibição de Resumo no Terminal
```

### 5.2 Módulos Principais

#### 5.2.1 `ffprobe_reader.py`
- Extração de metadados usando ffprobe
- Estimativa de tamanho GOP
- Análise de regularidade GOP

#### 5.2.2 `fingerprint_logic.py`
- Extração de metadados de câmera
- Análise de padrão QP
- Análise de padrão GOP
- Análise de metadados limpos
- Análise de sinais do encoder

#### 5.2.3 `video_classifier.py`
- Classificação heurística baseada em regras
- Cálculo de probabilidades por modelo de IA
- Detecção de câmera real
- Detecção de spoofing
- Detecção de conteúdo híbrido

#### 5.2.4 `prnu_detector.py`
- Extração de frames do vídeo
- Extração de ruído PRNU por frame
- Análise de padrão PRNU
- Comparação com baseline
- Análise frame a frame

#### 5.2.5 `fft_temporal.py`
- Extração de features temporais
- Análise de espectro FFT
- Detecção de assinatura de difusão
- Análise de movimento e jitter

#### 5.2.6 `metadata_integrity.py`
- Detecção de assinaturas de ferramentas
- Detecção de spoofing de metadados
- Análise de contradições técnicas

#### 5.2.7 `timeline_analyzer.py`
- Combinação de evidências multi-módulo
- Análise frame a frame
- Detecção de conteúdo híbrido
- Cálculo de distribuição de origens

#### 5.2.8 `cleaner.py`
- Remoção de metadados
- Re-encode neutro
- Adição de jitter temporal
- Pipeline completo de limpeza

#### 5.2.9 `sensor_calibration.py`
- Extração de fingerprint de sensor
- Salvamento de perfil baseline
- Carregamento de perfil baseline

#### 5.2.10 `content_analyzer.py`
- Análise de conteúdo visual
- Geração de descrições

#### 5.2.11 `audio_transcriber.py`
- Transcrição de áudio usando Whisper
- Geração de descrições baseadas em áudio

#### 5.2.12 `human_name_generator.py`
- Geração de nomes descritivos em português
- Combinação de análise visual e audio

#### 5.2.13 `video_content_analyzer.py`
- Geração de nomes SEO-friendly
- Sanitização de nomes de arquivo

### 5.3 Dependências Externas

#### 5.3.1 FFmpeg
- **Uso**: Processamento de vídeo, extração de metadados, re-encode
- **Instalação**: Via package manager do sistema

#### 5.3.2 Bibliotecas Python
- `pymediainfo>=9.0.0`: Leitura de metadados
- `ffmpeg-python>=0.2.0`: Interface Python para FFmpeg
- `numpy>=1.24.0`: Análise numérica
- `scipy>=1.10.0`: FFT e processamento de sinal
- `opencv-python>=4.8.0`: Processamento de frames
- `prnu>=0.1.0`: Análise PRNU
- `openai-whisper>=20231117`: Transcrição de áudio
- `pydub>=0.25.1`: Processamento de áudio

---

## 6. INTERFACE DE LINHA DE COMANDO (CLI)

### 6.1 Comandos Disponíveis

#### 6.1.1 Análise de Vídeo
```bash
python3 src/cli.py --input "/caminho/do/video.mp4"
```

**Parâmetros:**
- `--input` / `-i`: Caminho para arquivo de vídeo (obrigatório)
- `--output-dir` / `-o`: Diretório de saída (padrão: `output`)
- `--skip-clean`: Pula geração de vídeo limpo (mais rápido)
- `--baseline-profile`: Caminho para perfil baseline (padrão: `sensor_profile.json`)

#### 6.1.2 Calibração de Sensor
```bash
python3 src/cli.py --calibrate "/caminho/video_real.mp4" --baseline-profile "perfil.json"
```

**Parâmetros:**
- `--calibrate`: Caminho para vídeo real de calibração
- `--baseline-profile`: Caminho para salvar perfil (padrão: `sensor_profile.json`)

### 6.2 Saída no Terminal

O sistema exibe um resumo formatado:

```
======================================================================
VID-FINGER V3 - Relatório Forense de Análise
======================================================================

Arquivo: video.mp4
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
  - ai: 100.0%
----------------------------------------------------------------------

Entregáveis Gerados:
  1. Original: output/original/video-original.mp4
  2. Relatório: output/reports/video-forensic-report-20251115-120000.json
  3. Vídeo Limpo: output/clean/descricao-15-11-2025-12-00-00.mp4
======================================================================
```

---

## 7. CASOS DE USO

### 7.1 Caso de Uso 1: Detecção de Vídeo Gerado por IA
**Cenário**: Investigador recebe vídeo suspeito e precisa verificar se foi gerado por IA.

**Fluxo:**
1. Executa análise: `python3 src/cli.py --input video_suspeito.mp4`
2. Sistema analisa vídeo usando todos os módulos
3. Gera relatório com classificação e confiança
4. Identifica modelo de IA mais provável (ex: Sora)
5. Gera vídeo limpo para análise adicional

**Resultado Esperado:**
- Classificação: `AI_HEVC` com confiança alta
- Modelo mais provável: `Sora (OpenAI)`
- Relatório JSON completo com evidências

### 7.2 Caso de Uso 2: Detecção de Conteúdo Híbrido
**Cenário**: Vídeo contém partes reais e partes geradas por IA.

**Fluxo:**
1. Executa análise com baseline: `python3 src/cli.py --input video.mp4 --baseline-profile sensor_profile.json`
2. Sistema analisa frame a frame
3. Identifica transições entre real e IA
4. Calcula percentuais de cada tipo

**Resultado Esperado:**
- Classificação: `HYBRID_CONTENT`
- Timeline mostra frames reais e frames IA
- Percentuais: ex: 60% real, 40% IA

### 7.3 Caso de Uso 3: Detecção de Spoofing de Metadados
**Cenário**: Vídeo tem metadados de câmera mas foi gerado por IA.

**Fluxo:**
1. Executa análise completa
2. Sistema detecta contradição: metadados de câmera + encoder de re-encode
3. Identifica spoofing

**Resultado Esperado:**
- Classificação: `SPOOFED_METADATA`
- Confiança alta na detecção de spoofing
- Relatório detalha contradições encontradas

### 7.4 Caso de Uso 4: Geração de Vídeo Limpo
**Cenário**: Usuário precisa de versão do vídeo sem fingerprints de IA.

**Fluxo:**
1. Executa análise sem `--skip-clean`
2. Sistema gera vídeo limpo após análise
3. Vídeo limpo tem metadados removidos, re-encode neutro e jitter adicionado

**Resultado Esperado:**
- Vídeo limpo gerado em `output/clean/`
- Nome descritivo em português
- Vídeo sem fingerprints detectáveis

---

## 8. REQUISITOS NÃO-FUNCIONAIS

### 8.1 Performance
- Análise de vídeo de 10s: ~30-60 segundos (dependendo de hardware)
- Geração de vídeo limpo: ~1-2x duração do vídeo
- Análise PRNU: mais lenta, pode ser otimizada com menos frames

### 8.2 Confiabilidade
- Tratamento de erros em todos os módulos
- Fallback quando módulos falham
- Relatório de erro salvo em JSON se análise falhar

### 8.3 Compatibilidade
- **Python**: 3.10 ou superior
- **Sistemas Operacionais**: macOS, Linux, Windows
- **Formatos de Vídeo**: MP4, MOV, e outros suportados por FFmpeg
- **Codecs**: H.264, HEVC, AV1

### 8.4 Usabilidade
- Interface CLI simples e intuitiva
- Mensagens de progresso claras
- Resumo formatado no terminal
- Relatórios JSON bem estruturados

### 8.5 Manutenibilidade
- Código modular e bem organizado
- Documentação inline
- Separação de responsabilidades
- Fácil extensão de novos módulos

---

## 9. LIMITAÇÕES CONHECIDAS

### 9.1 Limitações Técnicas
- Análise PRNU pode ser lenta em vídeos muito longos
- Geração de vídeo limpo requer FFmpeg e pode demorar
- Alguns padrões de IA podem não ser detectados se muito processados
- Transcrição de áudio requer Whisper (pode não estar disponível)

### 9.2 Limitações de Precisão
- Confiança pode ser baixa em casos ambíguos
- Modelos de IA em evolução podem gerar novos padrões não detectados
- Vídeos muito processados podem perder fingerprints originais

### 9.3 Limitações de Escalabilidade
- Processamento é sequencial (não paralelo)
- Análise frame a frame pode ser custosa em vídeos longos
- Requer recursos computacionais adequados

---

## 10. ROADMAP FUTURO

### 10.1 Versão 4 (Planejada)
- Modelo de ML treinado para fingerprint SORA
- Detector de difusão baseado em PatchGAN
- Melhorias na detecção de modelos específicos

### 10.2 Versão 5 (Planejada)
- Interface web (GUI)
- API REST para automações
- Exportação de relatório pericial assinado (PDF digital)
- Suporte a processamento em lote
- Dashboard de análise

### 10.3 Melhorias Contínuas
- Otimização de performance
- Expansão de assinaturas de ferramentas
- Melhorias na detecção de spoofing
- Suporte a mais modelos de IA

---

## 11. MÉTRICAS DE SUCESSO

### 11.1 Precisão
- Taxa de acerto na classificação: > 85%
- Taxa de falsos positivos: < 10%
- Taxa de falsos negativos: < 15%

### 11.2 Performance
- Tempo de análise: < 2x duração do vídeo
- Uso de memória: < 2GB para vídeos de 10s

### 11.3 Usabilidade
- Tempo para primeira análise: < 5 minutos (incluindo setup)
- Documentação completa e clara

---

## 12. GLOSSÁRIO

- **PRNU**: Photo Response Non-Uniformity - Ruído único do sensor de câmera
- **GOP**: Group of Pictures - Grupo de frames em vídeo comprimido
- **QP**: Quantization Parameter - Parâmetro de quantização
- **FFT**: Fast Fourier Transform - Transformada Rápida de Fourier
- **Spoofing**: Falsificação ou manipulação de metadados
- **Fingerprint**: Assinatura única que identifica origem ou processamento
- **Baseline**: Perfil de referência de sensor real para comparação
- **Jitter**: Variação temporal no movimento (natural em câmeras reais)

---

## 13. REFERÊNCIAS TÉCNICAS

### 13.1 Técnicas Utilizadas
- Análise PRNU para identificação de sensor
- Análise espectral temporal (FFT)
- Análise heurística de metadados
- Processamento de sinal digital
- Análise forense de vídeo

### 13.2 Bibliotecas e Ferramentas
- FFmpeg: Processamento de vídeo
- OpenCV: Processamento de imagens
- NumPy/SciPy: Análise numérica
- Whisper: Transcrição de áudio

---

## 14. ANÁLISE DO PROJETO

### 14.1 O que o Projeto Faz

VID-FINGER V3 é um sistema forense completo que:

1. **Detecta vídeos gerados por IA** usando múltiplas técnicas:
   - Análise PRNU (ruído do sensor)
   - Análise FFT temporal (padrões de difusão)
   - Análise de metadados e fingerprints técnicos
   - Análise frame a frame para conteúdo híbrido

2. **Identifica modelos específicos de IA**:
   - Sora (OpenAI)
   - Runway Gen-3
   - Gemini Veo (Google)
   - Pika Labs
   - Luma Dream Machine

3. **Detecta manipulações**:
   - Spoofing de metadados
   - Ferramentas de edição utilizadas
   - Re-encode e processamento

4. **Gera evidências periciais**:
   - Relatório JSON completo
   - Timeline frame a frame
   - Vídeo limpo sem fingerprints

### 14.2 Como Funciona

O sistema utiliza uma arquitetura modular com múltiplas camadas de análise:

1. **Extração de Metadados**: Usa ffprobe para extrair informações técnicas do vídeo
2. **Análise PRNU**: Extrai ruído único do sensor e compara com baseline
3. **Análise FFT**: Analisa padrões espectrais temporais para detectar difusão
4. **Análise de Metadados**: Verifica integridade e detecta spoofing
5. **Fingerprint Técnico**: Analisa codec, encoder, GOP, QP
6. **Timeline**: Combina todas as evidências frame a frame
7. **Classificação**: Usa regras heurísticas para classificar o vídeo
8. **Limpeza**: Remove fingerprints de IA do vídeo

### 14.3 Bibliotecas e Módulos Utilizados

#### Bibliotecas Python Principais:
- **pymediainfo**: Leitura de metadados de mídia
- **ffmpeg-python**: Interface Python para FFmpeg
- **numpy**: Análise numérica e processamento de arrays
- **scipy**: FFT e processamento de sinal
- **opencv-python**: Processamento de frames e imagens
- **prnu**: Análise PRNU (Photo Response Non-Uniformity)
- **openai-whisper**: Transcrição de áudio
- **pydub**: Processamento de áudio

#### Módulos do Projeto:
1. **ffprobe_reader.py**: Extração de metadados via ffprobe
2. **fingerprint_logic.py**: Cálculo de fingerprint técnico
3. **video_classifier.py**: Classificação heurística
4. **prnu_detector.py**: Detecção de ruído PRNU
5. **fft_temporal.py**: Análise FFT temporal
6. **metadata_integrity.py**: Verificação de integridade
7. **timeline_analyzer.py**: Análise frame a frame
8. **cleaner.py**: Geração de vídeo limpo
9. **sensor_calibration.py**: Calibração de baseline
10. **content_analyzer.py**: Análise de conteúdo visual
11. **audio_transcriber.py**: Transcrição de áudio
12. **human_name_generator.py**: Geração de nomes descritivos
13. **video_content_analyzer.py**: Geração de nomes SEO-friendly

### 14.4 Como Usar

#### Instalação:
```bash
# Instalar FFmpeg (macOS)
brew install ffmpeg

# Instalar dependências Python
pip install -r requirements.txt
```

#### Uso Básico:
```bash
# Análise simples
python3 src/cli.py --input "/caminho/do/video.mp4"

# Com diretório de saída customizado
python3 src/cli.py --input video.mp4 --output-dir ./output

# Pular geração de vídeo limpo (mais rápido)
python3 src/cli.py --input video.mp4 --skip-clean

# Calibrar sensor baseline
python3 src/cli.py --calibrate video_real.mp4 --baseline-profile sensor_profile.json

# Usar baseline profile
python3 src/cli.py --input video.mp4 --baseline-profile sensor_profile.json
```

#### Saída:
O sistema sempre gera 3 arquivos:
1. **Original**: Cópia do arquivo de entrada em `output/original/`
2. **Relatório**: JSON completo em `output/reports/`
3. **Vídeo Limpo**: Vídeo sem fingerprints em `output/clean/`

---

**Fim do PRD**

