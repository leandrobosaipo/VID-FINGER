"""Lógica de análise de fingerprint técnico do vídeo."""
from typing import Any, Optional


def extract_camera_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Extrai metadados específicos de câmera.
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com informações de câmera detectadas
    """
    camera_info = {
        "make": None,
        "model": None,
        "has_quicktime_metadata": False,
        "has_camera_metadata": False
    }
    
    tags = metadata.get("tags", {})
    format_tags = metadata.get("format_tags", {})
    
    # Procura por Make e Model em diferentes locais
    make = (
        tags.get("Make") or
        tags.get("make") or
        format_tags.get("Make") or
        format_tags.get("make") or
        tags.get("com.apple.quicktime.make") or
        format_tags.get("com.apple.quicktime.make")
    )
    
    model = (
        tags.get("Model") or
        tags.get("model") or
        format_tags.get("Model") or
        format_tags.get("model") or
        tags.get("com.apple.quicktime.model") or
        format_tags.get("com.apple.quicktime.model")
    )
    
    if make:
        camera_info["make"] = make
        camera_info["has_camera_metadata"] = True
    
    if model:
        camera_info["model"] = model
        camera_info["has_camera_metadata"] = True
    
    # Verifica metadados QuickTime
    quicktime_keys = [
        "com.apple.quicktime.make",
        "com.apple.quicktime.model",
        "com.apple.quicktime.creationdate"
    ]
    
    for key in quicktime_keys:
        if key in tags or key in format_tags:
            camera_info["has_quicktime_metadata"] = True
            break
    
    return camera_info


def analyze_qp_pattern(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Analisa padrão de quantização (QP).
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com análise do padrão QP
    """
    qp_avg = metadata.get("qp_avg")
    
    analysis = {
        "qp_available": qp_avg is not None,
        "qp_avg": qp_avg,
        "pattern": "unknown",
        "variation": None
    }
    
    # Se não temos QP direto, tentamos inferir pelo encoder e codec
    if qp_avg is None:
        encoder = metadata.get("encoder", "").lower()
        codec = metadata.get("codec_name", "").lower()
        
        # Encoders de IA geralmente têm QP mais regular
        if "lavf" in encoder or "libx265" in encoder:
            analysis["pattern"] = "encoder_based"
        elif codec == "hevc" and not encoder:
            analysis["pattern"] = "suspicious_minimal"
    
    return analysis


def analyze_gop_pattern(metadata: dict[str, Any], gop_size: Optional[int] = None, gop_regularity: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Analisa padrão de GOP (Group of Pictures).
    
    Args:
        metadata: Metadados do vídeo
        gop_size: Tamanho do GOP (se disponível)
        gop_regularity: Análise de regularidade do GOP (se disponível)
        
    Returns:
        Dicionário com análise do padrão GOP
    """
    analysis = {
        "gop_size": gop_size or metadata.get("gop_size"),
        "pattern": "unknown",
        "is_regular": False,
        "regularity_confidence": 0.0
    }
    
    # Se temos análise de regularidade detalhada, usa ela
    if gop_regularity:
        analysis["gop_size"] = gop_regularity.get("gop_size") or analysis["gop_size"]
        analysis["is_regular"] = gop_regularity.get("is_regular", False)
        analysis["pattern"] = gop_regularity.get("pattern", "unknown")
        analysis["regularity_confidence"] = 1.0 - min(gop_regularity.get("coefficient_of_variation", 1.0), 1.0)
        analysis["variance"] = gop_regularity.get("variance")
        analysis["std_dev"] = gop_regularity.get("std_dev")
        analysis["coefficient_of_variation"] = gop_regularity.get("coefficient_of_variation")
    
    gop = analysis["gop_size"]
    
    # Se não temos análise de regularidade, usa heurística simples
    if gop and not gop_regularity:
        # GOP muito regular pode indicar IA
        # Câmeras reais geralmente têm GOP variável
        if 24 <= gop <= 60:
            analysis["is_regular"] = True
            analysis["pattern"] = "regular"
            analysis["regularity_confidence"] = 0.60  # Confiança média sem análise detalhada
        elif gop < 24:
            analysis["pattern"] = "short"
        else:
            analysis["pattern"] = "long"
    
    return analysis


def analyze_clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Analisa se os metadados estão "limpos demais" (ausência de campos esperados).
    Vídeos de IA geralmente têm metadados muito escassos comparados a câmeras reais.
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com análise de metadados limpos
    """
    tags = metadata.get("tags", {})
    format_tags = metadata.get("format_tags", {})
    all_tags = {**tags, **format_tags}
    
    # Campos esperados em vídeos de câmera real
    expected_camera_fields = [
        "Make", "make", "Model", "model",
        "com.apple.quicktime.make", "com.apple.quicktime.model",
        "com.apple.quicktime.creationdate", "creation_time",
        "date", "date_time", "date_time_original",
        "location", "location.ISO6709", "GPS"
    ]
    
    # Conta quantos campos esperados estão presentes
    present_fields = sum(1 for field in expected_camera_fields if field in all_tags)
    total_expected = len(expected_camera_fields)
    
    # Conta total de tags disponíveis
    total_tags = len(all_tags)
    
    # Metadados limpos demais: poucos campos esperados E poucas tags no total
    is_too_clean = (
        present_fields < 3 and  # Menos de 3 campos esperados
        total_tags < 10  # Menos de 10 tags no total
    )
    
    # Metadados extremamente limpos (forte indicador de IA)
    is_extremely_clean = (
        present_fields == 0 and  # Nenhum campo de câmera
        total_tags < 5  # Muito poucas tags
    )
    
    return {
        "is_too_clean": is_too_clean,
        "is_extremely_clean": is_extremely_clean,
        "present_camera_fields": present_fields,
        "total_expected_fields": total_expected,
        "total_tags": total_tags,
        "cleanliness_score": 1.0 - (present_fields / max(total_expected, 1))
    }


def analyze_encoder_signals(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Analisa sinais do encoder que podem indicar origem.
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com sinais do encoder
    """
    encoder = (metadata.get("encoder") or "").lower()
    codec = (metadata.get("codec_name") or "").lower()
    
    signals = {
        "encoder_name": metadata.get("encoder"),
        "codec": codec,
        "is_ai_encoder": False,
        "is_camera_encoder": False,
        "is_reencode": False,
        "is_minimalist_encoder": False,
        "reencode_confidence": 0.0,
        "ai_indicators": []
    }
    
    # Indicadores de encoder de IA
    ai_keywords = ["openai", "sora", "runway", "google", "aom", "svtav1"]
    for keyword in ai_keywords:
        if keyword in encoder:
            signals["is_ai_encoder"] = True
            signals["ai_indicators"].append(keyword)
    
    # Detecção melhorada de re-encode
    # libx265/libx264 são encoders de re-encode muito comuns
    if "libx265" in encoder:
        signals["is_reencode"] = True
        signals["reencode_confidence"] = 0.95
        # Se tem libx265 mas não tem metadados de câmera, aumenta suspeita de IA
        if not metadata.get("tags", {}).get("Make") and not metadata.get("format_tags", {}).get("Make"):
            signals["reencode_confidence"] = 0.98
    
    if "libx264" in encoder:
        signals["is_reencode"] = True
        signals["reencode_confidence"] = max(signals["reencode_confidence"], 0.90)
    
    # Encoder minimalista: Lavf sem detalhes adicionais
    # Vídeos de IA frequentemente passam por FFmpeg/Lavf sem preservar metadados
    encoder_name = metadata.get("encoder", "")
    if encoder_name:
        encoder_lower = encoder_name.lower()
        # Lavf sozinho ou com versão mínima indica encoder minimalista
        if "lavf" in encoder_lower:
            # Se tem apenas "Lavf" ou "Lavf" + versão sem mais info
            parts = encoder_lower.split()
            if len(parts) <= 2:  # "lavf60.16.100" ou "lavf 60.16.100"
                signals["is_minimalist_encoder"] = True
            # Se tem libx265 junto, também é minimalista
            if "libx265" in encoder_lower or "libx264" in encoder_lower:
                signals["is_minimalist_encoder"] = True
    
    # Encoders de câmera geralmente têm nomes específicos
    camera_keywords = ["iphone", "android", "camera", "canon", "nikon", "sony"]
    for keyword in camera_keywords:
        if keyword in encoder:
            signals["is_camera_encoder"] = True
            break
    
    # AV1 geralmente indica IA (especialmente Veo)
    if codec == "av1":
        signals["ai_indicators"].append("av1_codec")
    
    return signals


def calculate_fingerprint(metadata: dict[str, Any], gop_size: Optional[int] = None, gop_regularity: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Calcula fingerprint completo do vídeo.
    
    Args:
        metadata: Metadados do vídeo
        gop_size: Tamanho do GOP estimado
        gop_regularity: Análise de regularidade do GOP (se disponível)
        
    Returns:
        Dicionário com fingerprint completo
    """
    camera_info = extract_camera_metadata(metadata)
    qp_analysis = analyze_qp_pattern(metadata)
    gop_analysis = analyze_gop_pattern(metadata, gop_size, gop_regularity)
    encoder_signals = analyze_encoder_signals(metadata)
    clean_metadata_analysis = analyze_clean_metadata(metadata)
    
    return {
        "camera_metadata": camera_info,
        "qp_analysis": qp_analysis,
        "gop_analysis": gop_analysis,
        "encoder_signals": encoder_signals,
        "clean_metadata_analysis": clean_metadata_analysis
    }

