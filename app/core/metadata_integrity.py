"""Análise de integridade de metadados e detecção de spoofing."""
from typing import Any, Optional


# Assinaturas conhecidas de ferramentas de edição
TOOL_SIGNATURES = {
    "Premiere Pro": {
        "encoder_keywords": ["adobe", "premiere"],
        "format_tags": ["com.adobe.premiere"],
        "software_keywords": ["adobe", "premiere"]
    },
    "CapCut": {
        "encoder_keywords": ["capcut"],
        "format_tags": ["capcut"],
        "software_keywords": ["capcut", "byteplus"]
    },
    "VN Video Editor": {
        "encoder_keywords": ["vn"],
        "format_tags": ["vn"],
        "software_keywords": ["vn"]
    },
    "DaVinci Resolve": {
        "encoder_keywords": ["davinci", "blackmagic"],
        "format_tags": ["davinci"],
        "software_keywords": ["davinci", "blackmagic"]
    },
    "FFmpeg": {
        "encoder_keywords": ["lavf", "lavc"],
        "format_tags": ["lavf"],
        "software_keywords": ["ffmpeg"]
    },
    "Sora": {
        "encoder_keywords": ["openai", "sora"],
        "format_tags": [],
        "software_keywords": ["openai", "sora"]
    },
    "Runway": {
        "encoder_keywords": ["runway"],
        "format_tags": [],
        "software_keywords": ["runway"]
    }
}


def detect_tool_signatures(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Detecta assinaturas de ferramentas de edição/renderização.
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Lista de ferramentas detectadas com confiança
    """
    detected_tools = []
    encoder = (metadata.get("encoder") or "").lower()
    tags = metadata.get("tags", {})
    format_tags = metadata.get("format_tags", {})
    all_tags = {**tags, **format_tags}
    
    # Verifica cada ferramenta conhecida
    for tool_name, signatures in TOOL_SIGNATURES.items():
        confidence = 0.0
        
        # Verifica keywords no encoder
        for keyword in signatures["encoder_keywords"]:
            if keyword in encoder:
                confidence += 0.4
        
        # Verifica tags de formato
        for tag_key in signatures["format_tags"]:
            if tag_key in all_tags:
                confidence += 0.3
        
        # Verifica keywords em software
        software = str(all_tags.get("software", "")).lower()
        for keyword in signatures["software_keywords"]:
            if keyword in software:
                confidence += 0.3
        
        if confidence > 0.3:
            detected_tools.append({
                "tool": tool_name,
                "confidence": min(confidence, 0.95),
                "indicators": []
            })
    
    return detected_tools


def detect_metadata_spoofing(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Detecta spoofing de metadados (metadados falsos ou copiados).
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com análise de spoofing
    """
    tags = metadata.get("tags", {})
    format_tags = metadata.get("format_tags", {})
    all_tags = {**tags, **format_tags}
    
    encoder = (metadata.get("encoder") or "").lower()
    codec = (metadata.get("codec_name") or "").lower()
    
    spoof_indicators = []
    confidence = 0.0
    
    # Contradição 1: Make: Apple mas encoder é libx264/libx265 (re-encode)
    make = (all_tags.get("Make") or all_tags.get("make") or 
            all_tags.get("com.apple.quicktime.make") or "").lower()
    
    if "apple" in make and ("libx264" in encoder or "libx265" in encoder):
        spoof_indicators.append("Make Apple com encoder de re-encode")
        confidence += 0.4
    
    # Contradição 2: major_brand incompatível com codec
    major_brand = (metadata.get("major_brand") or "").lower()
    if major_brand == "qt" and codec == "av1":
        spoof_indicators.append("QuickTime brand com codec AV1 (incompatível)")
        confidence += 0.3
    
    # Contradição 3: Metadados de câmera mas encoder minimalista
    has_camera_metadata = (
        make or
        all_tags.get("Model") or
        all_tags.get("com.apple.quicktime.model")
    )
    
    if has_camera_metadata and ("lavf" in encoder or len(encoder) < 10):
        spoof_indicators.append("Metadados de câmera com encoder minimalista")
        confidence += 0.35
    
    # Contradição 4: Metadados copiados (mesmos valores em vídeos diferentes)
    # Verifica se tem metadados muito genéricos que podem ser copiados
    if make == "apple" and not all_tags.get("com.apple.quicktime.model"):
        spoof_indicators.append("Make Apple sem Model específico (possível cópia)")
        confidence += 0.2
    
    # Contradição 5: Encoder não corresponde ao codec esperado
    if codec == "h264" and "libx265" in encoder:
        spoof_indicators.append("Codec H.264 com encoder HEVC")
        confidence += 0.25
    
    # Contradição 6: Metadados muito limpos para um vídeo re-encodado
    if ("libx264" in encoder or "libx265" in encoder) and len(all_tags) < 5:
        spoof_indicators.append("Re-encode detectado mas metadados muito limpos")
        confidence += 0.3
    
    is_spoofed = confidence > 0.4
    
    return {
        "is_spoofed": is_spoofed,
        "confidence": min(confidence, 0.95),
        "spoof_indicators": spoof_indicators,
        "has_camera_metadata": bool(has_camera_metadata),
        "has_contradictions": len(spoof_indicators) > 0
    }


def detect_copied_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Detecta se metadados foram copiados de outro vídeo.
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com análise de metadados copiados
    """
    tags = metadata.get("tags", {})
    format_tags = metadata.get("format_tags", {})
    all_tags = {**tags, **format_tags}
    
    # Metadados copiados geralmente têm:
    # 1. Valores muito genéricos
    # 2. Ausência de campos específicos de câmera
    # 3. Inconsistências temporais
    
    indicators = []
    confidence = 0.0
    
    # Verifica se tem Make mas não tem Model (genérico demais)
    make = all_tags.get("Make") or all_tags.get("make")
    model = all_tags.get("Model") or all_tags.get("model")
    
    if make and not model:
        indicators.append("Make sem Model (genérico)")
        confidence += 0.3
    
    # Verifica se tem location mas não tem timestamp consistente
    has_location = bool(
        all_tags.get("location") or
        all_tags.get("com.apple.quicktime.location.ISO6709")
    )
    creation_date = (
        all_tags.get("creation_time") or
        all_tags.get("com.apple.quicktime.creationdate")
    )
    
    if has_location and not creation_date:
        indicators.append("Location sem timestamp (possível cópia)")
        confidence += 0.25
    
    # Verifica se metadados são muito escassos para um vídeo de câmera
    if make and len(all_tags) < 8:
        indicators.append("Metadados muito escassos para câmera real")
        confidence += 0.2
    
    return {
        "is_copied": confidence > 0.4,
        "confidence": min(confidence, 0.90),
        "indicators": indicators
    }


def analyze_metadata_integrity(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Análise completa de integridade de metadados.
    
    Args:
        metadata: Metadados do vídeo
        
    Returns:
        Dicionário com análise completa
    """
    tool_signatures = detect_tool_signatures(metadata)
    spoofing_analysis = detect_metadata_spoofing(metadata)
    copied_analysis = detect_copied_metadata(metadata)
    
    # Determina status geral
    integrity_status = "valid"
    if spoofing_analysis["is_spoofed"]:
        integrity_status = "spoofed"
    elif copied_analysis["is_copied"]:
        integrity_status = "copied"
    elif tool_signatures:
        integrity_status = "edited"
    
    return {
        "integrity_status": integrity_status,
        "tool_signatures": tool_signatures,
        "spoofing_analysis": spoofing_analysis,
        "copied_metadata_analysis": copied_analysis,
        "overall_confidence": max(
            spoofing_analysis["confidence"],
            copied_analysis["confidence"],
            max([t["confidence"] for t in tool_signatures], default=0.0)
        )
    }

