"""Módulo para análise de conteúdo do vídeo e geração de nomes SEO-friendly."""
import cv2
import numpy as np
import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple, Any


def extract_relevant_frame(video_path: str, frame_position: str = "middle") -> Optional[np.ndarray]:
    """
    Extrai um frame relevante do vídeo para análise de conteúdo.
    
    Args:
        video_path: Caminho do vídeo
        frame_position: Posição do frame ("middle", "start", "end", ou número de frame)
        
    Returns:
        Frame extraído ou None se falhar
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if total_frames == 0:
        cap.release()
        return None
    
    # Determina qual frame extrair
    if frame_position == "middle":
        target_frame = total_frames // 2
    elif frame_position == "start":
        target_frame = 0
    elif frame_position == "end":
        target_frame = total_frames - 1
    elif isinstance(frame_position, int):
        target_frame = min(frame_position, total_frames - 1)
    else:
        target_frame = total_frames // 2
    
    # Vai para o frame desejado
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        return frame
    return None


def analyze_frame_content(frame: np.ndarray) -> dict[str, Any]:
    """
    Analisa conteúdo visual do frame para gerar descrição.
    
    Args:
        frame: Frame do vídeo
        
    Returns:
        Dicionário com características do frame
    """
    if frame is None:
        return {}
    
    # Converte para escala de cinza
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    
    # Características básicas
    height, width = gray.shape[:2]
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)
    
    # Detecta bordas (indica movimento ou objetos)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (height * width)
    
    # Detecta contornos (objetos)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    num_objects = len([c for c in contours if cv2.contourArea(c) > 100])
    
    # Classifica tipo de cena baseado em características
    scene_type = "unknown"
    if edge_density < 0.05:
        scene_type = "static"
    elif edge_density > 0.2:
        scene_type = "dynamic"
    elif num_objects > 5:
        scene_type = "complex"
    
    # Gera hash visual para identificação única
    frame_hash = hashlib.md5(gray.tobytes()).hexdigest()[:8]
    
    return {
        "width": width,
        "height": height,
        "brightness": float(mean_brightness),
        "contrast": float(std_brightness),
        "edge_density": float(edge_density),
        "num_objects": num_objects,
        "scene_type": scene_type,
        "visual_hash": frame_hash
    }


def generate_seo_friendly_name(
    video_path: str,
    classification: Optional[str] = None,
    metadata: Optional[dict] = None,
    frame_analysis: Optional[dict] = None
) -> str:
    """
    Gera nome SEO-friendly baseado no conteúdo do vídeo.
    
    Args:
        video_path: Caminho do vídeo
        classification: Classificação do vídeo (AI_HEVC, REAL_CAMERA, etc.)
        metadata: Metadados do vídeo
        frame_analysis: Análise do frame (opcional)
        
    Returns:
        Nome SEO-friendly sanitizado
    """
    # Extrai frame se não fornecido
    if frame_analysis is None:
        frame = extract_relevant_frame(video_path)
        if frame is not None:
            frame_analysis = analyze_frame_content(frame)
    
    # Componentes do nome
    name_parts = []
    
    # 1. Tipo de conteúdo baseado em classificação
    if classification:
        if classification == "AI_HEVC":
            name_parts.append("ai-generated")
        elif classification == "AI_AV1":
            name_parts.append("ai-generated")
        elif classification == "REAL_CAMERA":
            name_parts.append("real-camera")
        elif classification == "SPOOFED_METADATA":
            name_parts.append("spoofed")
        elif classification == "HYBRID_CONTENT":
            name_parts.append("hybrid")
    
    # 2. Características do frame
    if frame_analysis:
        scene_type = frame_analysis.get("scene_type", "unknown")
        if scene_type != "unknown":
            name_parts.append(scene_type)
        
        # Adiciona resolução se disponível
        width = frame_analysis.get("width", 0)
        height = frame_analysis.get("height", 0)
        if width > 0 and height > 0:
            if width >= 1920 or height >= 1080:
                name_parts.append("hd")
            elif width >= 1280 or height >= 720:
                name_parts.append("sd")
    
    # 3. Metadados se disponíveis
    if metadata:
        codec = metadata.get("codec_name", "").lower()
        if codec:
            name_parts.append(codec)
    
    # 4. Hash visual curto para unicidade
    if frame_analysis and frame_analysis.get("visual_hash"):
        name_parts.append(frame_analysis["visual_hash"])
    
    # Se não tem partes suficientes, usa nome do arquivo original sanitizado
    if len(name_parts) < 2:
        input_name = Path(video_path).stem
        # Remove caracteres especiais e espaços
        sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '-', input_name)
        sanitized = re.sub(r'-+', '-', sanitized).strip('-')
        if sanitized:
            name_parts.insert(0, sanitized[:30])  # Limita tamanho
    
    # Junta tudo com hífens
    seo_name = "-".join(name_parts).lower()
    
    # Remove hífens duplicados e limita tamanho
    seo_name = re.sub(r'-+', '-', seo_name)
    seo_name = seo_name[:80]  # Limita a 80 caracteres para SEO
    
    return seo_name.strip('-')


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres problemáticos.
    
    Args:
        filename: Nome original
        max_length: Tamanho máximo
        
    Returns:
        Nome sanitizado
    """
    # Remove caracteres especiais, mantém apenas alfanuméricos, hífens e underscores
    sanitized = re.sub(r'[^a-zA-Z0-9\-_.]', '-', filename)
    
    # Remove hífens/underscores duplicados
    sanitized = re.sub(r'[-_]+', '-', sanitized)
    
    # Remove hífens no início e fim
    sanitized = sanitized.strip('-_.')
    
    # Limita tamanho
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('-_.')
    
    return sanitized or "video"


def generate_output_filenames(
    video_path: str,
    classification: Optional[str] = None,
    metadata: Optional[dict] = None,
    file_type: str = "report"
) -> dict[str, str]:
    """
    Gera nomes SEO-friendly para todos os arquivos de saída.
    
    Args:
        video_path: Caminho do vídeo
        classification: Classificação do vídeo
        metadata: Metadados do vídeo
        file_type: Tipo de arquivo ("report", "original", "clean")
        
    Returns:
        Dicionário com nomes gerados
    """
    # Extrai frame e analisa conteúdo
    frame = extract_relevant_frame(video_path)
    frame_analysis = analyze_frame_content(frame) if frame is not None else None
    
    # Gera nome base SEO-friendly
    base_name = generate_seo_friendly_name(video_path, classification, metadata, frame_analysis)
    
    # Adiciona timestamp para unicidade
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Gera nomes específicos por tipo
    filenames = {}
    
    if file_type == "report":
        filenames["report"] = sanitize_filename(f"{base_name}-forensic-report-{timestamp}.json")
        filenames["original"] = sanitize_filename(f"{base_name}-original{Path(video_path).suffix}")
        filenames["clean"] = sanitize_filename(f"{base_name}-clean-ai-version-{timestamp}.mp4")
    elif file_type == "original":
        filenames["original"] = sanitize_filename(f"{base_name}-original{Path(video_path).suffix}")
    elif file_type == "clean":
        filenames["clean"] = sanitize_filename(f"{base_name}-clean-ai-version-{timestamp}.mp4")
    
    return filenames

