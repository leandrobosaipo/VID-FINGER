"""Módulo de análise de conteúdo visual avançada para gerar descrições humanas."""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List


def extract_multiple_frames(video_path: str, num_frames: int = 5) -> List[np.ndarray]:
    """
    Extrai múltiplos frames espaçados do vídeo para análise.
    
    Args:
        video_path: Caminho do vídeo
        num_frames: Número de frames para extrair
        
    Returns:
        Lista de frames extraídos
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        cap.release()
        return []
    
    frames = []
    # Extrai frames espaçados (início, meio, fim)
    if num_frames == 1:
        frame_indices = [total_frames // 2]
    elif num_frames == 2:
        frame_indices = [0, total_frames - 1]
    else:
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    
    cap.release()
    return frames


def detect_environment(frame: np.ndarray) -> str:
    """
    Detecta se o ambiente é interno ou externo baseado em luminosidade e cores.
    
    Args:
        frame: Frame do vídeo
        
    Returns:
        "interno" ou "exterior"
    """
    if frame is None or frame.size == 0:
        return "desconhecido"
    
    # Converte para HSV para análise de cores
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Analisa luminosidade média
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    
    # Analisa presença de verde (vegetação) e azul (céu)
    # Verde: H entre 40-80, S > 50, V > 50
    green_mask = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))
    green_ratio = np.sum(green_mask > 0) / (frame.shape[0] * frame.shape[1])
    
    # Azul: H entre 100-130
    blue_mask = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
    blue_ratio = np.sum(blue_mask > 0) / (frame.shape[0] * frame.shape[1])
    
    # Heurística: exterior tem mais verde/azul e luminosidade variável
    if green_ratio > 0.15 or blue_ratio > 0.20:
        return "exterior"
    elif mean_brightness < 80:
        return "interno"
    elif green_ratio < 0.05 and blue_ratio < 0.10:
        return "interno"
    else:
        return "exterior"


def detect_time_of_day(frame: np.ndarray) -> str:
    """
    Detecta se é dia ou noite baseado na luminosidade.
    
    Args:
        frame: Frame do vídeo
        
    Returns:
        "dia" ou "noite"
    """
    if frame is None or frame.size == 0:
        return "desconhecido"
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    
    # Limiar empírico: < 60 = noite, >= 60 = dia
    if mean_brightness < 60:
        return "noite"
    else:
        return "dia"


def detect_movement_type(frames: List[np.ndarray]) -> str:
    """
    Detecta tipo de movimento analisando diferenças entre frames.
    
    Args:
        frames: Lista de frames do vídeo
        
    Returns:
        Tipo de movimento: "estatico", "caminhada", "corrida", "veiculo", "desconhecido"
    """
    if len(frames) < 2:
        return "estatico"
    
    # Calcula diferença média entre frames consecutivos
    diffs = []
    for i in range(len(frames) - 1):
        gray1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frames[i+1], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        diffs.append(np.mean(diff))
    
    avg_diff = np.mean(diffs)
    
    # Limiares empíricos
    if avg_diff < 5:
        return "estatico"
    elif avg_diff < 15:
        return "caminhada"
    elif avg_diff < 30:
        return "corrida"
    elif avg_diff < 50:
        return "veiculo"
    else:
        return "movimento-rapido"


def detect_main_objects(frame: np.ndarray) -> List[str]:
    """
    Detecta objetos principais usando análise de contornos e formas.
    
    Args:
        frame: Frame do vídeo
        
    Returns:
        Lista de objetos detectados em português
    """
    if frame is None or frame.size == 0:
        return []
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detecta bordas
    edges = cv2.Canny(gray, 50, 150)
    
    # Encontra contornos
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    objects = []
    
    # Analisa contornos grandes (objetos principais)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1000:  # Ignora objetos muito pequenos
            continue
        
        # Aproxima contorno para detectar formas
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Detecta formas básicas
        if len(approx) >= 4:
            # Retângulo ou quadrado (pode ser pessoa, veículo, objeto)
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h
            
            if 0.3 < aspect_ratio < 0.7:  # Formato vertical (pessoa)
                if "pessoa" not in objects:
                    objects.append("pessoa")
            elif 1.2 < aspect_ratio < 3.0:  # Formato horizontal (veículo)
                if "veiculo" not in objects:
                    objects.append("veiculo")
    
    # Detecta padrões de cor para identificar objetos comuns
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Detecta verde (vegetação)
    green_mask = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))
    if np.sum(green_mask > 0) / (frame.shape[0] * frame.shape[1]) > 0.1:
        if "vegetacao" not in objects:
            objects.append("vegetacao")
    
    # Detecta azul (céu/água)
    blue_mask = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
    if np.sum(blue_mask > 0) / (frame.shape[0] * frame.shape[1]) > 0.15:
        if "ceu" not in objects:
            objects.append("ceu")
    
    return objects[:3]  # Limita a 3 objetos principais


def analyze_visual_content(video_path: str) -> Dict[str, Any]:
    """
    Analisa conteúdo visual do vídeo e gera descrição em português.
    
    Args:
        video_path: Caminho do vídeo
        
    Returns:
        Dicionário com análise visual e descrições
    """
    frames = extract_multiple_frames(video_path, num_frames=5)
    
    if not frames:
        return {
            "success": False,
            "description": "video-conteudo-desconhecido",
            "keywords": []
        }
    
    # Analisa frame do meio (mais representativo)
    middle_frame = frames[len(frames) // 2]
    
    # Detecta ambiente
    environment = detect_environment(middle_frame)
    time_of_day = detect_time_of_day(middle_frame)
    
    # Detecta movimento
    movement = detect_movement_type(frames)
    
    # Detecta objetos principais
    objects = detect_main_objects(middle_frame)
    
    # Gera palavras-chave
    keywords = []
    
    if environment != "desconhecido":
        keywords.append(environment)
    
    if time_of_day != "desconhecido" and environment == "exterior":
        keywords.append(time_of_day)
    
    if movement != "desconhecido" and movement != "estatico":
        keywords.append(movement)
    
    # Adiciona objetos principais
    keywords.extend(objects[:2])  # Máximo 2 objetos
    
    # Gera descrição
    if keywords:
        description = "-".join(keywords)
    else:
        description = "video-conteudo-desconhecido"
    
    return {
        "success": True,
        "description": description,
        "keywords": keywords,
        "environment": environment,
        "time_of_day": time_of_day,
        "movement": movement,
        "objects": objects
    }

