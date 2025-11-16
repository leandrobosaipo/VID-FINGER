"""Classificador de vídeo baseado em regras heurísticas."""
from typing import Any, Optional


CLASSIFICATION_LABELS = {
    "REAL_CAMERA": "REAL_CAMERA",
    "AI_HEVC": "AI_HEVC",
    "AI_AV1": "AI_AV1",
    "SPOOFED_METADATA": "SPOOFED_METADATA",
    "HYBRID_CONTENT": "HYBRID_CONTENT",
    "UNKNOWN": "UNKNOWN"
}

AI_MODELS = {
    "SORA": "Sora (OpenAI)",
    "RUNWAY": "Runway Gen-3",
    "VEO": "Gemini Veo (Google)",
    "PIKA": "Pika Labs",
    "LUMA": "Luma Dream Machine",
    "OTHER": "Outro modelo de IA"
}


def classify_real_camera(fingerprint: dict[str, Any]) -> tuple[bool, float]:
    """
    Verifica se o vídeo é de câmera real.
    
    Args:
        fingerprint: Fingerprint do vídeo
        
    Returns:
        Tupla (é_câmera_real, confidence)
    """
    camera_metadata = fingerprint.get("camera_metadata", {})
    
    # Se tem metadados de câmera, provavelmente é real
    if camera_metadata.get("has_camera_metadata"):
        confidence = 0.85
        if camera_metadata.get("has_quicktime_metadata"):
            confidence = 0.95
        return True, confidence
    
    # Codec H.264 com encoder não suspeito pode ser câmera
    encoder_signals = fingerprint.get("encoder_signals", {})
    codec = encoder_signals.get("codec", "")
    
    if codec == "h264" and not encoder_signals.get("is_ai_encoder"):
        if encoder_signals.get("is_camera_encoder"):
            return True, 0.75
        if not encoder_signals.get("is_reencode"):
            return True, 0.60
    
    return False, 0.0


def classify_ai_av1(fingerprint: dict[str, Any]) -> tuple[bool, float]:
    """
    Verifica se o vídeo é IA gerado com codec AV1.
    
    Args:
        fingerprint: Fingerprint do vídeo
        
    Returns:
        Tupla (é_AI_AV1, confidence)
    """
    encoder_signals = fingerprint.get("encoder_signals", {})
    codec = encoder_signals.get("codec", "")
    
    if codec != "av1":
        return False, 0.0
    
    confidence = 0.70
    
    # Se tem indicadores de Google/AOM, aumenta confiança
    ai_indicators = encoder_signals.get("ai_indicators", [])
    if "google" in ai_indicators or "aom" in ai_indicators:
        confidence = 0.90
    
    if "av1_codec" in ai_indicators:
        confidence = 0.85
    
    # Se não tem metadados de câmera, aumenta suspeita
    camera_metadata = fingerprint.get("camera_metadata", {})
    if not camera_metadata.get("has_camera_metadata"):
        confidence = min(confidence + 0.10, 0.95)
    
    return True, confidence


def classify_ai_hevc(fingerprint: dict[str, Any]) -> tuple[bool, float]:
    """
    Verifica se o vídeo é IA gerado com codec HEVC.
    
    Args:
        fingerprint: Fingerprint do vídeo
        
    Returns:
        Tupla (é_AI_HEVC, confidence)
    """
    encoder_signals = fingerprint.get("encoder_signals", {})
    codec = encoder_signals.get("codec", "")
    
    if codec != "hevc":
        return False, 0.0
    
    confidence = 0.50
    
    # Se tem indicadores de IA no encoder
    ai_indicators = encoder_signals.get("ai_indicators", [])
    if ai_indicators:
        confidence = 0.80
    
    # Se não tem metadados de câmera
    camera_metadata = fingerprint.get("camera_metadata", {})
    if not camera_metadata.get("has_camera_metadata"):
        confidence += 0.15
    
    # Análise de metadados limpos (novo)
    clean_metadata = fingerprint.get("clean_metadata_analysis", {})
    if clean_metadata.get("is_extremely_clean"):
        confidence += 0.20  # Metadados extremamente limpos = forte indicador
    elif clean_metadata.get("is_too_clean"):
        confidence += 0.10  # Metadados limpos demais
    
    # Detecção melhorada de re-encode
    if encoder_signals.get("is_reencode"):
        reencode_conf = encoder_signals.get("reencode_confidence", 0.0)
        # Re-encode com libx265 sem metadados de câmera é muito suspeito
        if reencode_conf > 0.95 and not camera_metadata.get("has_camera_metadata"):
            confidence += 0.15
        elif reencode_conf > 0.90:
            confidence += 0.08
    
    # Encoder minimalista (Lavf sem mais info) pode indicar Sora
    if encoder_signals.get("is_minimalist_encoder"):
        confidence += 0.12
    
    # Encoder minimalista alternativo (verificação antiga mantida para compatibilidade)
    encoder_name = encoder_signals.get("encoder_name", "").lower()
    if "lavf" in encoder_name and len(encoder_name) < 20 and not encoder_signals.get("is_minimalist_encoder"):
        confidence += 0.10
    
    # GOP regular pode indicar IA (melhorado)
    gop_analysis = fingerprint.get("gop_analysis", {})
    if gop_analysis.get("is_regular"):
        regularity_conf = gop_analysis.get("regularity_confidence", 0.0)
        # Se GOP é muito regular (alta confiança), aumenta mais a suspeita
        if regularity_conf > 0.80:
            confidence += 0.12
        elif regularity_conf > 0.60:
            confidence += 0.08
        else:
            confidence += 0.05
    
    # QP com padrão suspeito
    qp_analysis = fingerprint.get("qp_analysis", {})
    if qp_analysis.get("pattern") == "suspicious_minimal":
        confidence += 0.10
    
    confidence = min(confidence, 0.95)
    
    # Se tem metadados de câmera, reduz confiança
    if camera_metadata.get("has_camera_metadata"):
        confidence = max(confidence - 0.30, 0.20)
    
    return confidence > 0.40, confidence


def calculate_model_probabilities(fingerprint: dict[str, Any]) -> dict[str, float]:
    """
    Calcula probabilidades por modelo de IA baseado nos sinais detectados.
    
    Args:
        fingerprint: Fingerprint completo do vídeo
        
    Returns:
        Dicionário com probabilidades por modelo (0.0 a 1.0)
    """
    encoder_signals = fingerprint.get("encoder_signals", {})
    codec = encoder_signals.get("codec", "")
    encoder_name = (encoder_signals.get("encoder_name") or "").lower()
    ai_indicators = encoder_signals.get("ai_indicators", [])
    clean_metadata = fingerprint.get("clean_metadata_analysis", {})
    gop_analysis = fingerprint.get("gop_analysis", {})
    
    probabilities = {
        AI_MODELS["SORA"]: 0.0,
        AI_MODELS["RUNWAY"]: 0.0,
        AI_MODELS["VEO"]: 0.0,
        AI_MODELS["PIKA"]: 0.0,
        AI_MODELS["LUMA"]: 0.0,
        AI_MODELS["OTHER"]: 0.0
    }
    
    # VEO - Geralmente usa AV1
    if codec == "av1":
        probabilities[AI_MODELS["VEO"]] = 0.70
        if "google" in ai_indicators or "aom" in ai_indicators:
            probabilities[AI_MODELS["VEO"]] = 0.90
        if clean_metadata.get("is_extremely_clean"):
            probabilities[AI_MODELS["VEO"]] = min(probabilities[AI_MODELS["VEO"]] + 0.10, 0.95)
    
    # SORA - HEVC com padrões específicos
    if codec == "hevc":
        sora_score = 0.0
        
        # Encoder minimalista é típico de Sora
        if encoder_signals.get("is_minimalist_encoder"):
            sora_score += 0.30
        
        # Metadados extremamente limpos
        if clean_metadata.get("is_extremely_clean"):
            sora_score += 0.25
        
        # Re-encode com libx265 sem metadados
        if encoder_signals.get("is_reencode") and encoder_signals.get("reencode_confidence", 0) > 0.95:
            sora_score += 0.20
        
        # GOP regular
        if gop_analysis.get("is_regular"):
            regularity_conf = gop_analysis.get("regularity_confidence", 0.0)
            if regularity_conf > 0.80:
                sora_score += 0.15
        
        # Indicadores explícitos
        if "sora" in ai_indicators or "openai" in ai_indicators:
            sora_score = 0.90
        
        probabilities[AI_MODELS["SORA"]] = min(sora_score, 0.95)
        
        # RUNWAY - Também usa HEVC mas com padrões diferentes
        runway_score = 0.0
        
        if "runway" in ai_indicators:
            runway_score = 0.90
        elif codec == "hevc" and not encoder_signals.get("is_minimalist_encoder"):
            # Runway geralmente preserva mais metadados que Sora
            if not clean_metadata.get("is_extremely_clean"):
                runway_score = 0.40
        
        probabilities[AI_MODELS["RUNWAY"]] = min(runway_score, 0.85)
    
    # PIKA e LUMA - Menos comum, geralmente HEVC também
    if codec == "hevc":
        if "pika" in ai_indicators:
            probabilities[AI_MODELS["PIKA"]] = 0.85
        if "luma" in ai_indicators:
            probabilities[AI_MODELS["LUMA"]] = 0.85
    
    # Normaliza probabilidades se alguma for alta
    max_prob = max(probabilities.values())
    if max_prob > 0.5:
        # Se temos uma probabilidade alta, reduz outras proporcionalmente
        total = sum(probabilities.values())
        if total > 1.0:
            for model in probabilities:
                probabilities[model] = probabilities[model] / total
    
    # OTHER - Probabilidade residual se não identificamos modelo específico
    if max(probabilities.values()) < 0.50:
        probabilities[AI_MODELS["OTHER"]] = 0.60
    
    return probabilities


def classify_spoofed_metadata(
    fingerprint: dict[str, Any],
    metadata_integrity: Optional[dict[str, Any]] = None
) -> tuple[bool, float]:
    """
    Verifica se o vídeo tem metadados spoofed.
    
    Args:
        fingerprint: Fingerprint do vídeo
        metadata_integrity: Análise de integridade de metadados
        
    Returns:
        Tupla (é_spoofed, confidence)
    """
    if metadata_integrity:
        spoofing = metadata_integrity.get("spoofing_analysis", {})
        if spoofing.get("is_spoofed"):
            return True, spoofing.get("confidence", 0.7)
    
    # Verifica contradições no fingerprint
    encoder_signals = fingerprint.get("encoder_signals", {})
    clean_metadata = fingerprint.get("clean_metadata_analysis", {})
    camera_metadata = fingerprint.get("camera_metadata", {})
    
    # Contradição: tem metadados de câmera mas encoder é de re-encode
    if (camera_metadata.get("has_camera_metadata") and 
        encoder_signals.get("is_reencode") and
        encoder_signals.get("reencode_confidence", 0) > 0.90):
        return True, 0.75
    
    return False, 0.0


def classify_hybrid_content(
    timeline_analysis: Optional[dict[str, Any]] = None
) -> tuple[bool, float]:
    """
    Verifica se o conteúdo é híbrido (partes reais + partes IA).
    
    Args:
        timeline_analysis: Análise de timeline
        
    Returns:
        Tupla (é_híbrido, confidence)
    """
    if timeline_analysis:
        hybrid = timeline_analysis.get("hybrid_analysis", {})
        if hybrid.get("is_hybrid"):
            real_pct = hybrid.get("real_percentage", 0)
            ai_pct = hybrid.get("ai_percentage", 0)
            # Confiança baseada na distribuição
            confidence = min((real_pct + ai_pct) / 100.0, 0.95)
            return True, confidence
    
    return False, 0.0


def classify_video(
    fingerprint: dict[str, Any],
    metadata_integrity: Optional[dict[str, Any]] = None,
    timeline_analysis: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    Classifica o vídeo usando regras heurísticas.
    
    Args:
        fingerprint: Fingerprint completo do vídeo
        metadata_integrity: Análise de integridade de metadados (opcional)
        timeline_analysis: Análise de timeline (opcional)
        
    Returns:
        Dicionário com classificação, confidence e probabilidades por modelo
    """
    # Ordem de verificação: HYBRID primeiro, depois SPOOFED, depois REAL_CAMERA, depois AI
    
    # 1. Verifica se é conteúdo híbrido
    is_hybrid, hybrid_confidence = classify_hybrid_content(timeline_analysis)
    if is_hybrid and hybrid_confidence > 0.50:
        return {
            "classification": CLASSIFICATION_LABELS["HYBRID_CONTENT"],
            "confidence": hybrid_confidence,
            "reason": "Conteúdo híbrido detectado (partes reais + partes IA)",
            "model_probabilities": {},
            "timeline_analysis": timeline_analysis
        }
    
    # 2. Verifica se tem metadados spoofed
    is_spoofed, spoofed_confidence = classify_spoofed_metadata(fingerprint, metadata_integrity)
    if is_spoofed and spoofed_confidence > 0.60:
        return {
            "classification": CLASSIFICATION_LABELS["SPOOFED_METADATA"],
            "confidence": spoofed_confidence,
            "reason": "Metadados spoofed detectados",
            "model_probabilities": {}
        }
    
    # 3. Verifica se é câmera real
    is_real, real_confidence = classify_real_camera(fingerprint)
    if is_real and real_confidence > 0.60:
        return {
            "classification": CLASSIFICATION_LABELS["REAL_CAMERA"],
            "confidence": real_confidence,
            "reason": "Metadados de câmera detectados",
            "model_probabilities": {}
        }
    
    # 4. Verifica se é AI AV1
    is_av1, av1_confidence = classify_ai_av1(fingerprint)
    if is_av1 and av1_confidence > 0.60:
        model_probs = calculate_model_probabilities(fingerprint)
        return {
            "classification": CLASSIFICATION_LABELS["AI_AV1"],
            "confidence": av1_confidence,
            "reason": "Codec AV1 detectado com sinais de IA",
            "model_probabilities": model_probs
        }
    
    # 5. Verifica se é AI HEVC
    is_hevc, hevc_confidence = classify_ai_hevc(fingerprint)
    if is_hevc and hevc_confidence > 0.60:
        model_probs = calculate_model_probabilities(fingerprint)
        return {
            "classification": CLASSIFICATION_LABELS["AI_HEVC"],
            "confidence": hevc_confidence,
            "reason": "Codec HEVC com padrões suspeitos de IA",
            "model_probabilities": model_probs
        }
    
    # 6. Caso não classificado
    return {
        "classification": CLASSIFICATION_LABELS["UNKNOWN"],
        "confidence": 0.50,
        "reason": "Não foi possível determinar origem com confiança suficiente",
        "model_probabilities": {}
    }

