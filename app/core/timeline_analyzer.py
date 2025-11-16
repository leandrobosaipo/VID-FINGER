"""Analisador de timeline frame a frame combinando todos os módulos."""
from typing import Any, Optional


def combine_frame_analysis(
    prnu_results: list[dict[str, Any]],
    fft_results: dict[str, Any],
    metadata_integrity: dict[str, Any],
    fingerprint: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Combina resultados de todos os módulos para análise frame a frame.
    
    Args:
        prnu_results: Resultados do PRNU detector por frame
        fft_results: Resultados da análise FFT temporal
        metadata_integrity: Análise de integridade de metadados
        fingerprint: Fingerprint técnico do vídeo
        
    Returns:
        Timeline completa com origem de cada frame
    """
    timeline = []
    
    # Se não temos análise PRNU frame a frame, cria timeline básica
    if not prnu_results:
        return timeline
    
    # Análise geral de FFT
    motion_analysis = fft_results.get("motion_analysis", {})
    has_ai_pattern = motion_analysis.get("has_ai_pattern", False)
    diffusion_confidence = fft_results.get("confidence", 0.0)
    
    # Análise de spoofing
    is_spoofed = metadata_integrity.get("spoofing_analysis", {}).get("is_spoofed", False)
    
    # Fingerprint técnico
    encoder_signals = fingerprint.get("encoder_signals", {})
    clean_metadata = fingerprint.get("clean_metadata_analysis", {})
    
    # Processa cada frame da análise PRNU
    for prnu_frame in prnu_results:
        frame_num = prnu_frame.get("frame", 0)
        prnu_origin = prnu_frame.get("origin", "unknown")
        prnu_confidence = prnu_frame.get("confidence", 0.5)
        
        # Combina evidências
        evidence_scores = {
            "real_camera": 0.0,
            "ai": 0.0,
            "spoofed": 0.0
        }
        
        # Evidência PRNU
        if prnu_origin == "real_camera":
            evidence_scores["real_camera"] += prnu_confidence * 0.4
        elif prnu_origin == "ai":
            evidence_scores["ai"] += prnu_confidence * 0.4
        
        # Evidência FFT (aplica a todos os frames se detectado)
        if has_ai_pattern:
            evidence_scores["ai"] += diffusion_confidence * 0.3
        
        # Evidência de spoofing
        if is_spoofed:
            evidence_scores["spoofed"] += 0.3
        
        # Evidência de metadados limpos (indica IA)
        if clean_metadata.get("is_extremely_clean"):
            evidence_scores["ai"] += 0.2
        
        # Evidência de encoder
        if encoder_signals.get("is_reencode") and not encoder_signals.get("is_camera_encoder"):
            evidence_scores["ai"] += 0.1
        
        # Determina origem final
        max_score = max(evidence_scores.values())
        final_origin = max(evidence_scores.items(), key=lambda x: x[1])[0]
        
        # Normaliza para nomes padrão
        if final_origin == "real_camera":
            origin_label = "real_camera"
        elif final_origin == "ai":
            origin_label = "ai"
        elif final_origin == "spoofed":
            origin_label = "spoofed_metadata"
        else:
            origin_label = "unknown"
        
        timeline.append({
            "frame": frame_num,
            "origin": origin_label,
            "confidence": min(max_score, 0.95),
            "evidence_scores": {
                "real_camera": evidence_scores["real_camera"],
                "ai": evidence_scores["ai"],
                "spoofed": evidence_scores["spoofed"]
            }
        })
    
    return timeline


def detect_hybrid_content(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Detecta se o conteúdo é híbrido (partes reais + partes IA).
    
    Args:
        timeline: Timeline frame a frame
        
    Returns:
        Análise de conteúdo híbrido
    """
    if not timeline:
        return {
            "is_hybrid": False,
            "real_percentage": 0.0,
            "ai_percentage": 0.0,
            "transitions": []
        }
    
    total_frames = len(timeline)
    real_frames = sum(1 for f in timeline if f["origin"] == "real_camera")
    ai_frames = sum(1 for f in timeline if f["origin"] == "ai")
    
    real_percentage = (real_frames / total_frames) * 100
    ai_percentage = (ai_frames / total_frames) * 100
    
    # Detecta transições entre real e IA
    transitions = []
    prev_origin = None
    for frame_data in timeline:
        current_origin = frame_data["origin"]
        if prev_origin and prev_origin != current_origin:
            transitions.append({
                "frame": frame_data["frame"],
                "from": prev_origin,
                "to": current_origin
            })
        prev_origin = current_origin
    
    # É híbrido se tem tanto frames reais quanto IA
    is_hybrid = (
        real_percentage > 10 and
        ai_percentage > 10 and
        len(transitions) > 0
    )
    
    return {
        "is_hybrid": is_hybrid,
        "real_percentage": real_percentage,
        "ai_percentage": ai_percentage,
        "spoofed_percentage": (sum(1 for f in timeline if f["origin"] == "spoofed_metadata") / total_frames) * 100,
        "transitions": transitions,
        "total_frames": total_frames
    }


def generate_timeline_summary(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Gera resumo estatístico da timeline.
    
    Args:
        timeline: Timeline frame a frame
        
    Returns:
        Resumo estatístico
    """
    if not timeline:
        return {}
    
    origins = {}
    for frame_data in timeline:
        origin = frame_data["origin"]
        origins[origin] = origins.get(origin, 0) + 1
    
    total = len(timeline)
    
    return {
        "total_frames": total,
        "origin_distribution": {
            origin: (count / total) * 100
            for origin, count in origins.items()
        },
        "dominant_origin": max(origins.items(), key=lambda x: x[1])[0] if origins else "unknown",
        "average_confidence": sum(f["confidence"] for f in timeline) / total if timeline else 0.0
    }


def apply_classification_override(
    timeline: list[dict[str, Any]],
    macro_classification: str
) -> tuple[list[dict[str, Any]], bool]:
    """
    Aplica override baseado na classificação macro para evitar contradições.
    
    Args:
        timeline: Timeline frame a frame
        macro_classification: Classificação macro do vídeo
        
    Returns:
        Tupla (timeline corrigida, foi_ajustada)
    """
    if not timeline:
        return timeline, False
    
    adjusted = False
    
    # Se classificação macro é AI_HEVC ou AI_AV1, força timeline para "ai"
    if macro_classification in ["AI_HEVC", "AI_AV1"]:
        for frame_data in timeline:
            if frame_data["origin"] == "real_camera":
                frame_data["origin"] = "ai"
                frame_data["confidence"] = max(frame_data.get("confidence", 0.5), 0.70)
                frame_data["evidence_scores"]["ai"] = frame_data["evidence_scores"].get("ai", 0.0) + 0.5
                frame_data["evidence_scores"]["real_camera"] = 0.0
                adjusted = True
    
    # Se classificação macro é SPOOFED_METADATA, ajusta timeline
    elif macro_classification == "SPOOFED_METADATA":
        for frame_data in timeline:
            if frame_data["origin"] == "real_camera" and frame_data.get("confidence", 0) < 0.80:
                frame_data["origin"] = "spoofed_metadata"
                adjusted = True
    
    # Se classificação macro é REAL_CAMERA com alta confiança, valida timeline
    elif macro_classification == "REAL_CAMERA":
        # Se timeline mostra muito "ai", pode ser falso positivo - mantém como está
        # mas reduz confiança de frames marcados como "ai"
        ai_count = sum(1 for f in timeline if f["origin"] == "ai")
        total = len(timeline)
        if ai_count / total > 0.5:  # Mais de 50% marcado como IA
            # Pode ser híbrido ou erro - não força override
            pass
    
    return timeline, adjusted


def analyze_timeline(
    prnu_results: list[dict[str, Any]],
    fft_results: dict[str, Any],
    metadata_integrity: dict[str, Any],
    fingerprint: dict[str, Any],
    macro_classification: Optional[str] = None
) -> dict[str, Any]:
    """
    Análise completa de timeline combinando todos os módulos.
    
    Args:
        prnu_results: Resultados do PRNU por frame
        fft_results: Resultados da análise FFT
        metadata_integrity: Análise de integridade
        fingerprint: Fingerprint técnico
        macro_classification: Classificação macro do vídeo (opcional, para override)
        
    Returns:
        Análise completa de timeline
    """
    # Gera timeline frame a frame
    timeline = combine_frame_analysis(
        prnu_results,
        fft_results,
        metadata_integrity,
        fingerprint
    )
    
    # Aplica override baseado em classificação macro se fornecido
    timeline_adjusted = False
    if macro_classification:
        timeline, timeline_adjusted = apply_classification_override(timeline, macro_classification)
    
    # Detecta conteúdo híbrido
    hybrid_analysis = detect_hybrid_content(timeline)
    
    # Gera resumo
    summary = generate_timeline_summary(timeline)
    
    return {
        "timeline": timeline,
        "hybrid_analysis": hybrid_analysis,
        "summary": summary,
        "timeline_adjusted": timeline_adjusted,
        "macro_classification_override": macro_classification if timeline_adjusted else None
    }

