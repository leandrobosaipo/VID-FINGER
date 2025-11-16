"""Detector PRNU (Photo Response Non-Uniformity) para identificar origem de câmera."""
import cv2
import numpy as np
from typing import Any, Optional
from pathlib import Path


def extract_frames_from_video(video_path: str, max_frames: int = 30) -> list[np.ndarray]:
    """
    Extrai frames do vídeo para análise PRNU.
    
    Args:
        video_path: Caminho do vídeo
        max_frames: Número máximo de frames a extrair
        
    Returns:
        Lista de frames como arrays numpy
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    
    if not cap.isOpened():
        return frames
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, total_frames // max_frames)
    
    frame_idx = 0
    while len(frames) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # Converte para escala de cinza se necessário
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        frames.append(frame)
        frame_idx += frame_interval
    
    cap.release()
    return frames


def extract_prnu_noise(frame: np.ndarray) -> np.ndarray:
    """
    Extrai ruído PRNU de um frame usando filtro de alta frequência.
    
    Args:
        frame: Frame em escala de cinza
        
    Returns:
        Ruído PRNU extraído
    """
    # Converte para float32 para processamento
    frame_float = frame.astype(np.float32)
    
    # Aplica filtro de Wiener simplificado para extrair ruído
    # Usa filtro de alta frequência para isolar ruído do sensor
    kernel = np.array([[-1, -1, -1],
                       [-1,  8, -1],
                       [-1, -1, -1]]) / 9.0
    
    noise = cv2.filter2D(frame_float, -1, kernel)
    
    # Normaliza
    noise = noise - np.mean(noise)
    noise = noise / (np.std(noise) + 1e-10)
    
    return noise


def analyze_prnu_pattern(frames: list[np.ndarray]) -> dict[str, Any]:
    """
    Analisa padrão PRNU de múltiplos frames.
    
    Args:
        frames: Lista de frames para análise
        
    Returns:
        Dicionário com análise PRNU
    """
    if not frames:
        return {
            "prnu_detected": False,
            "noise_consistency": 0.0,
            "noise_variance": 0.0,
            "is_perfect_noise": False,
            "is_physical_sensor": False,
            "confidence": 0.0
        }
    
    # Extrai PRNU de todos os frames
    prnu_noises = [extract_prnu_noise(frame) for frame in frames]
    
    # Calcula consistência do ruído entre frames
    # Ruído de sensor real deve ser consistente entre frames
    noise_variances = [np.var(noise) for noise in prnu_noises]
    avg_variance = np.mean(noise_variances)
    variance_std = np.std(noise_variances)
    
    # Calcula correlação entre ruídos de frames consecutivos
    correlations = []
    for i in range(len(prnu_noises) - 1):
        corr = np.corrcoef(
            prnu_noises[i].flatten(),
            prnu_noises[i+1].flatten()
        )[0, 1]
        if not np.isnan(corr):
            correlations.append(corr)
    
    avg_correlation = np.mean(correlations) if correlations else 0.0
    
    # Ruído "perfeito demais" (muito baixa variância) indica IA
    is_perfect_noise = avg_variance < 0.01 and variance_std < 0.005
    
    # Ruído físico de sensor tem características específicas
    # Variância moderada e correlação entre frames
    is_physical_sensor = (
        0.01 < avg_variance < 0.5 and
        avg_correlation > 0.1 and
        variance_std > 0.001
    )
    
    # Calcula confiança
    confidence = 0.0
    if is_perfect_noise:
        confidence = 0.85  # Alto indicador de IA
    elif is_physical_sensor:
        confidence = 0.75  # Alto indicador de câmera real
    elif avg_variance < 0.005:
        confidence = 0.70  # Suspeito de IA
    elif avg_correlation < 0.05:
        confidence = 0.60  # Ruído inconsistente (pode ser spoof)
    
    return {
        "prnu_detected": True,
        "noise_consistency": avg_correlation,
        "noise_variance": avg_variance,
        "noise_variance_std": variance_std,
        "is_perfect_noise": is_perfect_noise,
        "is_physical_sensor": is_physical_sensor,
        "confidence": confidence,
        "frames_analyzed": len(frames)
    }


def analyze_prnu_per_frame(video_path: str, sample_rate: int = 10) -> list[dict[str, Any]]:
    """
    Analisa PRNU frame a frame para construir timeline.
    
    Args:
        video_path: Caminho do vídeo
        sample_rate: Taxa de amostragem (analisa 1 a cada N frames)
        
    Returns:
        Lista de análises por frame
    """
    cap = cv2.VideoCapture(video_path)
    results = []
    
    if not cap.isOpened():
        return results
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % sample_rate == 0:
            # Converte para escala de cinza
            if len(frame.shape) == 3:
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                frame_gray = frame
            
            # Extrai PRNU
            noise = extract_prnu_noise(frame_gray)
            noise_var = np.var(noise)
            
            # Classifica origem baseado no ruído
            origin = "unknown"
            confidence = 0.5
            
            if noise_var < 0.01:
                origin = "ai"
                confidence = 0.80
            elif noise_var > 0.1:
                origin = "real_camera"
                confidence = 0.70
            else:
                origin = "unknown"
                confidence = 0.50
            
            results.append({
                "frame": frame_idx,
                "origin": origin,
                "confidence": confidence,
                "noise_variance": float(noise_var)
            })
        
        frame_idx += 1
    
    cap.release()
    return results


def detect_prnu(video_path: str, baseline_profile: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Detecta padrões PRNU no vídeo completo, opcionalmente comparando com baseline.
    
    Args:
        video_path: Caminho do vídeo
        baseline_profile: Perfil baseline do sensor (opcional)
        
    Returns:
        Dicionário com análise PRNU completa
    """
    # Extrai frames para análise geral
    frames = extract_frames_from_video(video_path, max_frames=30)
    general_analysis = analyze_prnu_pattern(frames)
    
    # Análise frame a frame (amostragem)
    frame_analysis = analyze_prnu_per_frame(video_path, sample_rate=10)
    
    # Compara com baseline se disponível
    baseline_comparison = None
    if baseline_profile:
        from src.core.sensor_calibration import compare_with_baseline
        baseline_comparison = compare_with_baseline(general_analysis, baseline_profile)
        
        # Ajusta análise frame a frame baseado em baseline
        if baseline_comparison and not baseline_comparison.get("match", False):
            # Se não match com baseline, aumenta probabilidade de IA
            for frame_data in frame_analysis:
                if frame_data["origin"] == "real_camera":
                    # Reduz confiança de "real_camera" se não match baseline
                    baseline_confidence = baseline_comparison.get("confidence", 0.0)
                    if baseline_confidence < 0.60:
                        frame_data["origin"] = "ai"
                        frame_data["confidence"] = max(frame_data.get("confidence", 0.5), 0.70)
    
    result = {
        "general_analysis": general_analysis,
        "frame_analysis": frame_analysis,
        "total_frames_analyzed": len(frame_analysis)
    }
    
    if baseline_comparison:
        result["baseline_comparison"] = baseline_comparison
    
    return result

