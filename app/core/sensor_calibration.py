"""Módulo de calibração de sensor para criar baseline de referência."""
import cv2
import numpy as np
import json
from pathlib import Path
from typing import Optional, Dict, Any


def extract_sensor_fingerprint(video_path: str, max_frames: int = 50) -> Dict[str, Any]:
    """
    Extrai fingerprint PRNU e características do sensor de um vídeo real.
    
    Args:
        video_path: Caminho do vídeo real (ex: captura de iPhone)
        max_frames: Número máximo de frames para análise
        
    Returns:
        Dicionário com fingerprint do sensor
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {}
    
    frames = []
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Extrai frames espaçados para melhor representação
    if total_frames > 0:
        frame_indices = np.linspace(0, total_frames - 1, min(max_frames, total_frames), dtype=int)
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
                frames.append(gray)
                frame_count += 1
    else:
        # Se não consegue obter total, lê sequencialmente
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            frames.append(gray)
            frame_count += 1
    
    cap.release()
    
    if not frames:
        return {}
    
    # Analisa PRNU dos frames
    prnu_patterns = []
    noise_variances = []
    noise_correlations = []
    
    for i, frame in enumerate(frames):
        # Extrai ruído residual (simplificado)
        # Em implementação real, usaria filtro de alta frequência mais sofisticado
        blurred = cv2.GaussianBlur(frame.astype(np.float32), (5, 5), 0)
        noise = frame.astype(np.float32) - blurred
        noise_variances.append(np.var(noise))
        
        if i > 0:
            # Correlação entre ruídos consecutivos
            corr = np.corrcoef(
                noise.flatten(),
                prnu_patterns[-1].flatten()
            )[0, 1]
            if not np.isnan(corr):
                noise_correlations.append(corr)
        
        prnu_patterns.append(noise)
    
    # Calcula características do sensor
    avg_variance = np.mean(noise_variances)
    variance_std = np.std(noise_variances)
    avg_correlation = np.mean(noise_correlations) if noise_correlations else 0.0
    
    # PRNU médio (fingerprint do sensor)
    prnu_fingerprint = np.mean(prnu_patterns, axis=0) if prnu_patterns else None
    
    # Análise de jitter temporal (variação de luminância entre frames)
    luminance_series = [np.mean(frame) for frame in frames]
    luminance_variance = np.var(luminance_series)
    luminance_std = np.std(np.diff(luminance_series))  # Jitter
    
    fingerprint = {
        "sensor_type": "calibrated",
        "prnu_characteristics": {
            "avg_variance": float(avg_variance),
            "variance_std": float(variance_std),
            "avg_correlation": float(avg_correlation),
            "prnu_fingerprint_shape": list(prnu_fingerprint.shape) if prnu_fingerprint is not None else None
        },
        "temporal_characteristics": {
            "luminance_variance": float(luminance_variance),
            "jitter_std": float(luminance_std),
            "frames_analyzed": len(frames)
        },
        "calibration_source": str(Path(video_path).name),
        "calibration_date": None  # Será preenchido ao salvar
    }
    
    # Salva fingerprint como array numpy (opcional, para uso futuro)
    # Por enquanto, só salva características estatísticas
    
    return fingerprint


def save_sensor_profile(fingerprint: Dict[str, Any], output_path: str) -> bool:
    """
    Salva perfil do sensor em arquivo JSON.
    
    Args:
        fingerprint: Fingerprint do sensor
        output_path: Caminho do arquivo de saída
        
    Returns:
        True se salvou com sucesso
    """
    try:
        from datetime import datetime
        fingerprint["calibration_date"] = datetime.now().isoformat()
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(fingerprint, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Erro ao salvar perfil do sensor: {e}")
        return False


def load_sensor_profile(profile_path: str) -> Optional[Dict[str, Any]]:
    """
    Carrega perfil do sensor de arquivo JSON.
    
    Args:
        profile_path: Caminho do arquivo de perfil
        
    Returns:
        Dicionário com fingerprint ou None se falhar
    """
    try:
        profile_file = Path(profile_path)
        if not profile_file.exists():
            return None
        
        with open(profile_file, "r", encoding="utf-8") as f:
            fingerprint = json.load(f)
        
        return fingerprint
    except Exception as e:
        print(f"Erro ao carregar perfil do sensor: {e}")
        return None


def compare_with_baseline(
    video_prnu: Dict[str, Any],
    baseline_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compara características PRNU do vídeo com baseline calibrado.
    
    Args:
        video_prnu: Características PRNU do vídeo analisado
        baseline_profile: Perfil baseline do sensor
        
    Returns:
        Dicionário com resultado da comparação
    """
    if not baseline_profile:
        return {"match": False, "confidence": 0.0, "reason": "No baseline available"}
    
    baseline_prnu = baseline_profile.get("prnu_characteristics", {})
    baseline_variance = baseline_prnu.get("avg_variance", 0.0)
    baseline_correlation = baseline_prnu.get("avg_correlation", 0.0)
    
    video_variance = video_prnu.get("noise_variance", 0.0)
    video_correlation = video_prnu.get("noise_consistency", 0.0)
    
    # Calcula similaridade
    variance_diff = abs(video_variance - baseline_variance)
    correlation_diff = abs(video_correlation - baseline_correlation)
    
    # Thresholds para match (ajustáveis)
    variance_threshold = baseline_variance * 0.3  # 30% de tolerância
    correlation_threshold = 0.2  # Diferença máxima de correlação
    
    variance_match = variance_diff < variance_threshold
    correlation_match = correlation_diff < correlation_threshold
    
    # Confiança baseada em quão próximo está do baseline
    if variance_match and correlation_match:
        confidence = 0.85
        match = True
        reason = "PRNU matches baseline sensor characteristics"
    elif variance_match or correlation_match:
        confidence = 0.60
        match = False
        reason = "Partial PRNU match - may be different sensor or processed"
    else:
        confidence = 0.30
        match = False
        reason = "PRNU does not match baseline - likely different source or AI-generated"
    
    return {
        "match": match,
        "confidence": confidence,
        "reason": reason,
        "variance_diff": float(variance_diff),
        "correlation_diff": float(correlation_diff),
        "variance_match": variance_match,
        "correlation_match": correlation_match
    }

