"""Leitor de metadados de vídeo usando ffprobe."""
import json
import subprocess
from typing import Any, Optional


def run_ffprobe(video_path: str) -> dict[str, Any]:
    """
    Executa ffprobe e retorna metadados em formato JSON.
    
    Args:
        video_path: Caminho para o arquivo de vídeo
        
    Returns:
        Dicionário com metadados do vídeo
        
    Raises:
        subprocess.CalledProcessError: Se ffprobe falhar
        FileNotFoundError: Se ffprobe não estiver instalado
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-i", video_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao executar ffprobe: {e.stderr}")
    except FileNotFoundError:
        raise FileNotFoundError(
            "ffprobe não encontrado. Instale FFmpeg: https://ffmpeg.org/download.html"
        )


def extract_video_stream(probe_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Extrai o stream de vídeo dos dados do ffprobe.
    
    Args:
        probe_data: Dados retornados pelo ffprobe
        
    Returns:
        Dicionário com informações do stream de vídeo ou None
    """
    streams = probe_data.get("streams", [])
    for stream in streams:
        if stream.get("codec_type") == "video":
            return stream
    return None


def extract_format_info(probe_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extrai informações do formato do vídeo.
    
    Args:
        probe_data: Dados retornados pelo ffprobe
        
    Returns:
        Dicionário com informações de formato
    """
    return probe_data.get("format", {})


def extract_metadata(video_path: str) -> dict[str, Any]:
    """
    Extrai todos os metadados relevantes do vídeo.
    
    Args:
        video_path: Caminho para o arquivo de vídeo
        
    Returns:
        Dicionário com metadados extraídos
    """
    probe_data = run_ffprobe(video_path)
    video_stream = extract_video_stream(probe_data)
    format_info = extract_format_info(probe_data)
    
    metadata = {
        "codec_name": None,
        "encoder": None,
        "major_brand": None,
        "compatible_brands": None,
        "duration": None,
        "bit_rate": None,
        "frame_rate": None,
        "width": None,
        "height": None,
        "gop_size": None,
        "qp_avg": None,
        "tags": {},
        "format_tags": format_info.get("tags", {})
    }
    
    if video_stream:
        metadata["codec_name"] = video_stream.get("codec_name")
        metadata["encoder"] = video_stream.get("tags", {}).get("encoder")
        metadata["width"] = video_stream.get("width")
        metadata["height"] = video_stream.get("height")
        
        # Frame rate
        r_frame_rate = video_stream.get("r_frame_rate", "")
        if r_frame_rate:
            try:
                num, den = map(int, r_frame_rate.split("/"))
                if den > 0:
                    metadata["frame_rate"] = round(num / den, 2)
            except (ValueError, ZeroDivisionError):
                pass
        
        # Tags do stream
        metadata["tags"] = video_stream.get("tags", {})
        
        # GOP size (tentativa de estimativa)
        gop_size = video_stream.get("gop_size")
        if gop_size:
            metadata["gop_size"] = int(gop_size)
    
    # Informações do formato
    if format_info:
        metadata["major_brand"] = format_info.get("format_name", "").split(",")[0] if format_info.get("format_name") else None
        metadata["compatible_brands"] = format_info.get("format_name")
        
        duration = format_info.get("duration")
        if duration:
            try:
                metadata["duration"] = float(duration)
            except (ValueError, TypeError):
                pass
        
        bit_rate = format_info.get("bit_rate")
        if bit_rate:
            try:
                metadata["bit_rate"] = int(bit_rate)
            except (ValueError, TypeError):
                pass
    
    return metadata


def estimate_gop_size(video_path: str) -> Optional[int]:
    """
    Estima o tamanho do GOP analisando frames I.
    Usa múltiplas estratégias para melhorar a detecção.
    
    Args:
        video_path: Caminho para o arquivo de vídeo
        
    Returns:
        Tamanho estimado do GOP ou None
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "frame=pict_type",
        "-of", "csv=p=0",
        video_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=15  # Aumentado para vídeos maiores
        )
        
        frame_types = [ft.strip() for ft in result.stdout.strip().split("\n") if ft.strip()]
        
        if not frame_types:
            return None
        
        i_frame_indices = [
            i for i, frame_type in enumerate(frame_types)
            if frame_type == "I"
        ]
        
        if len(i_frame_indices) < 2:
            # Se tem apenas 1 I-frame, tenta estimar pelo total de frames
            if len(i_frame_indices) == 1 and len(frame_types) > 10:
                # Assume GOP baseado no número de frames até o primeiro I
                return i_frame_indices[0] if i_frame_indices[0] > 0 else None
            return None
        
        # Calcula diferenças entre I-frames consecutivos
        gaps = [
            i_frame_indices[i+1] - i_frame_indices[i]
            for i in range(len(i_frame_indices) - 1)
        ]
        
        if not gaps:
            return None
        
        # Calcula média
        avg_gop = sum(gaps) / len(gaps)
        
        # Calcula mediana para ser mais robusto a outliers
        sorted_gaps = sorted(gaps)
        median_gop = sorted_gaps[len(sorted_gaps) // 2]
        
        # Se média e mediana estão próximas, GOP é regular (típico de IA)
        # Se muito diferentes, GOP é irregular (típico de câmera)
        if abs(avg_gop - median_gop) < 2:
            # GOP regular, usa mediana
            return int(median_gop)
        else:
            # GOP irregular, usa média
            return int(avg_gop)
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None


def estimate_gop_regularity(video_path: str) -> Optional[dict[str, Any]]:
    """
    Estima o tamanho do GOP e sua regularidade.
    
    Args:
        video_path: Caminho para o arquivo de vídeo
        
    Returns:
        Dicionário com GOP size, regularidade e padrão, ou None
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "frame=pict_type",
        "-of", "csv=p=0",
        video_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=15
        )
        
        frame_types = [ft.strip() for ft in result.stdout.strip().split("\n") if ft.strip()]
        
        if not frame_types:
            return None
        
        i_frame_indices = [
            i for i, frame_type in enumerate(frame_types)
            if frame_type == "I"
        ]
        
        if len(i_frame_indices) < 2:
            return None
        
        # Calcula diferenças entre I-frames consecutivos
        gaps = [
            i_frame_indices[i+1] - i_frame_indices[i]
            for i in range(len(i_frame_indices) - 1)
        ]
        
        if not gaps:
            return None
        
        avg_gop = sum(gaps) / len(gaps)
        sorted_gaps = sorted(gaps)
        median_gop = sorted_gaps[len(sorted_gaps) // 2]
        
        # Calcula variância para medir regularidade
        variance = sum((g - avg_gop) ** 2 for g in gaps) / len(gaps)
        std_dev = variance ** 0.5
        
        # Coeficiente de variação (CV) - menor = mais regular
        cv = std_dev / avg_gop if avg_gop > 0 else float('inf')
        
        # Determina regularidade
        is_regular = cv < 0.15  # CV < 15% = muito regular (suspeito de IA)
        
        # Determina padrão
        if is_regular:
            pattern = "regular"
        elif cv < 0.30:
            pattern = "moderately_regular"
        else:
            pattern = "irregular"
        
        return {
            "gop_size": int(median_gop if abs(avg_gop - median_gop) < 2 else avg_gop),
            "is_regular": is_regular,
            "pattern": pattern,
            "variance": variance,
            "std_dev": std_dev,
            "coefficient_of_variation": cv,
            "gaps_sample": gaps[:10] if len(gaps) > 10 else gaps  # Amostra para debug
        }
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None

