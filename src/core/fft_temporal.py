"""Análise FFT Temporal para detectar padrões de difusão e assinaturas de IA."""
import cv2
import numpy as np
from scipy import fft, signal
from typing import Any, Optional


def extract_temporal_features(video_path: str, max_frames: int = 100) -> dict[str, Any]:
    """
    Extrai features temporais do vídeo para análise FFT.
    
    Args:
        video_path: Caminho do vídeo
        max_frames: Número máximo de frames a analisar
        
    Returns:
        Dicionário com features temporais
    """
    cap = cv2.VideoCapture(video_path)
    features = {
        "luminance": [],
        "motion": [],
        "texture": []
    }
    
    if not cap.isOpened():
        return features
    
    prev_frame = None
    frame_count = 0
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Converte para escala de cinza
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Luminância média
        luminance = np.mean(gray)
        features["luminance"].append(luminance)
        
        # Movimento (diferença entre frames)
        if prev_frame is not None:
            motion = np.mean(np.abs(gray.astype(float) - prev_frame.astype(float)))
            features["motion"].append(motion)
        else:
            features["motion"].append(0.0)
        
        # Textura (variação espacial)
        texture = np.std(gray)
        features["texture"].append(texture)
        
        prev_frame = gray
        frame_count += 1
    
    cap.release()
    return features


def analyze_fft_spectrum(signal_data: list[float]) -> dict[str, Any]:
    """
    Analisa espectro FFT de um sinal temporal.
    
    Args:
        signal_data: Lista de valores temporais
        
    Returns:
        Dicionário com análise espectral
    """
    if len(signal_data) < 10:
        return {
            "dominant_frequency": 0.0,
            "spectral_entropy": 0.0,
            "is_smooth": False,
            "has_ai_pattern": False
        }
    
    # Converte para array numpy
    signal_array = np.array(signal_data)
    
    # Remove tendência linear
    signal_detrended = signal.detrend(signal_array)
    
    # Aplica FFT
    fft_result = fft.fft(signal_detrended)
    fft_magnitude = np.abs(fft_result)
    frequencies = fft.fftfreq(len(signal_detrended))
    
    # Frequência dominante
    dominant_idx = np.argmax(fft_magnitude[1:len(fft_magnitude)//2]) + 1
    dominant_frequency = abs(frequencies[dominant_idx])
    
    # Entropia espectral (mede regularidade)
    # Sinal muito regular tem baixa entropia (típico de IA)
    fft_normalized = fft_magnitude / (np.sum(fft_magnitude) + 1e-10)
    spectral_entropy = -np.sum(fft_normalized * np.log(fft_normalized + 1e-10))
    
    # Detecta padrão de IA: movimento muito suave (baixa variância em frequências altas)
    high_freq_energy = np.sum(fft_magnitude[len(fft_magnitude)//4:])
    total_energy = np.sum(fft_magnitude)
    high_freq_ratio = high_freq_energy / (total_energy + 1e-10)
    
    # IA geralmente tem baixa energia em altas frequências (movimento suave)
    has_ai_pattern = (
        spectral_entropy < 3.0 and  # Baixa entropia = muito regular
        high_freq_ratio < 0.2  # Pouca energia em altas frequências
    )
    
    # Movimento muito suave indica IA
    is_smooth = np.std(signal_detrended) < np.mean(np.abs(signal_detrended)) * 0.3
    
    return {
        "dominant_frequency": float(dominant_frequency),
        "spectral_entropy": float(spectral_entropy),
        "high_freq_ratio": float(high_freq_ratio),
        "is_smooth": is_smooth,
        "has_ai_pattern": has_ai_pattern,
        "signal_variance": float(np.var(signal_detrended))
    }


def detect_diffusion_signature(video_path: str) -> dict[str, Any]:
    """
    Detecta assinatura de difusão temporal (típica de modelos de IA).
    
    Args:
        video_path: Caminho do vídeo
        
    Returns:
        Dicionário com análise de assinatura de difusão
    """
    # Extrai features temporais
    features = extract_temporal_features(video_path, max_frames=100)
    
    if not features["luminance"]:
        return {
            "diffusion_detected": False,
            "confidence": 0.0,
            "model_signatures": {}
        }
    
    # Analisa cada feature temporal
    luminance_analysis = analyze_fft_spectrum(features["luminance"])
    motion_analysis = analyze_fft_spectrum(features["motion"])
    texture_analysis = analyze_fft_spectrum(features["texture"])
    
    # Detecta padrões específicos de modelos
    model_signatures = {}
    
    # Sora: movimento muito suave, baixa variação temporal
    sora_score = 0.0
    if motion_analysis["is_smooth"] and motion_analysis["has_ai_pattern"]:
        sora_score += 0.4
    if luminance_analysis["spectral_entropy"] < 2.5:
        sora_score += 0.3
    if texture_analysis["signal_variance"] < 10.0:
        sora_score += 0.3
    model_signatures["Sora"] = min(sora_score, 0.95)
    
    # Runway: similar a Sora mas com mais variação
    runway_score = 0.0
    if motion_analysis["has_ai_pattern"]:
        runway_score += 0.3
    if 2.5 < luminance_analysis["spectral_entropy"] < 4.0:
        runway_score += 0.3
    if texture_analysis["signal_variance"] < 20.0:
        runway_score += 0.2
    model_signatures["Runway"] = min(runway_score, 0.85)
    
    # Veo: padrão mais complexo, mas ainda detectável
    veo_score = 0.0
    if motion_analysis["high_freq_ratio"] < 0.15:
        veo_score += 0.4
    if luminance_analysis["spectral_entropy"] < 3.5:
        veo_score += 0.3
    model_signatures["Veo"] = min(veo_score, 0.80)
    
    # Pika/Luma: padrões intermediários
    pika_score = 0.0
    if motion_analysis["is_smooth"]:
        pika_score += 0.3
    if texture_analysis["has_ai_pattern"]:
        pika_score += 0.3
    model_signatures["Pika"] = min(pika_score, 0.75)
    model_signatures["Luma"] = min(pika_score * 0.9, 0.70)
    
    # Confiança geral de detecção de difusão
    diffusion_detected = (
        motion_analysis["has_ai_pattern"] or
        luminance_analysis["has_ai_pattern"] or
        max(model_signatures.values()) > 0.5
    )
    
    confidence = max(model_signatures.values()) if model_signatures else 0.0
    
    return {
        "diffusion_detected": diffusion_detected,
        "confidence": confidence,
        "model_signatures": model_signatures,
        "luminance_analysis": luminance_analysis,
        "motion_analysis": motion_analysis,
        "texture_analysis": texture_analysis
    }


def analyze_temporal_jitter(video_path: str) -> dict[str, Any]:
    """
    Analisa jitter temporal (ausência indica IA).
    
    Args:
        video_path: Caminho do vídeo
        
    Returns:
        Dicionário com análise de jitter
    """
    features = extract_temporal_features(video_path, max_frames=100)
    
    if not features["motion"] or len(features["motion"]) < 10:
        return {
            "has_jitter": False,
            "jitter_variance": 0.0,
            "is_ai_like": True
        }
    
    motion = np.array(features["motion"])
    
    # Calcula variação de movimento frame a frame
    motion_diff = np.diff(motion)
    jitter_variance = np.var(motion_diff)
    
    # IA tem movimento muito suave (baixo jitter)
    has_jitter = jitter_variance > 50.0
    is_ai_like = jitter_variance < 10.0
    
    return {
        "has_jitter": has_jitter,
        "jitter_variance": float(jitter_variance),
        "is_ai_like": is_ai_like,
        "motion_smoothness": float(np.std(motion))
    }

