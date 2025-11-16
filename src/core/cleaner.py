"""Módulo de limpeza e reconstrução de vídeo sem fingerprints de IA."""
import subprocess
import random
from pathlib import Path
from typing import Any, Optional


def remove_metadata(input_path: str, output_path: str) -> bool:
    """
    Remove todos os metadados do vídeo.
    
    Args:
        input_path: Caminho do vídeo de entrada
        output_path: Caminho do vídeo de saída sem metadados
        
    Returns:
        True se sucesso, False caso contrário
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-map_metadata", "-1",  # Remove todos os metadados
        "-c:v", "copy",
        "-c:a", "copy",
        "-y",  # Sobrescreve se existir
        output_path
    ]
    
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=300
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def reencode_neutral(input_path: str, output_path: str) -> bool:
    """
    Re-encoda vídeo com preset neutro e naturalizado.
    
    Args:
        input_path: Caminho do vídeo de entrada
        output_path: Caminho do vídeo de saída
        
    Returns:
        True se sucesso, False caso contrário
    """
    # CRF 17 = alta qualidade, preset slow = mais natural
    # Adiciona leve randomização no QP para simular câmera real
    crf = 17 + random.randint(-2, 2)  # Varia entre 15-19
    
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y",
        output_path
    ]
    
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=600
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def add_temporal_jitter(input_path: str, output_path: str) -> bool:
    """
    Adiciona jitter microtemporal artificial para simular câmera real.
    
    Args:
        input_path: Caminho do vídeo de entrada
        output_path: Caminho do vídeo de saída
        
    Returns:
        True se sucesso, False caso contrário
    """
    # Usa filtro de vídeo para adicionar leve variação temporal
    # Isso quebra padrões temporais perfeitos de IA
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vf", "noise=alls=2:allf=t+u",  # Adiciona ruído temporal mínimo
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "copy",
        "-y",
        output_path
    ]
    
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=600
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        # Se falhar, retorna o vídeo sem jitter (ainda limpo)
        return False


def clean_video(input_path: str, output_path: str) -> dict[str, Any]:
    """
    Pipeline completo de limpeza de vídeo.
    
    Args:
        input_path: Caminho do vídeo original
        output_path: Caminho do vídeo limpo final
        
    Returns:
        Dicionário com status do processo
    """
    temp_dir = Path(output_path).parent
    temp_no_meta = temp_dir / "temp_no_meta.mp4"
    temp_reencoded = temp_dir / "temp_reencoded.mp4"
    
    results = {
        "metadata_removed": False,
        "reencoded": False,
        "jitter_added": False,
        "success": False,
        "errors": []
    }
    
    # Passo 1: Remove metadados
    if remove_metadata(input_path, str(temp_no_meta)):
        results["metadata_removed"] = True
    else:
        results["errors"].append("Falha ao remover metadados")
        # Continua mesmo se falhar
    
    # Passo 2: Re-encode neutro
    source_for_reencode = str(temp_no_meta) if results["metadata_removed"] else input_path
    
    if reencode_neutral(source_for_reencode, str(temp_reencoded)):
        results["reencoded"] = True
    else:
        results["errors"].append("Falha no re-encode")
        # Usa arquivo sem metadados se re-encode falhar
        if results["metadata_removed"]:
            temp_reencoded = temp_no_meta
    
    # Passo 3: Adiciona jitter (opcional, pode falhar)
    source_for_jitter = str(temp_reencoded) if results["reencoded"] else source_for_reencode
    
    if add_temporal_jitter(source_for_jitter, output_path):
        results["jitter_added"] = True
        results["success"] = True
    else:
        # Se jitter falhar, copia o vídeo re-encodado
        if results["reencoded"]:
            import shutil
            shutil.copy2(str(temp_reencoded), output_path)
            results["success"] = True
        else:
            results["errors"].append("Falha ao adicionar jitter e re-encode")
    
    # Limpa arquivos temporários
    try:
        if temp_no_meta.exists():
            temp_no_meta.unlink()
        if temp_reencoded.exists() and results["jitter_added"]:
            temp_reencoded.unlink()
    except Exception:
        pass  # Ignora erros na limpeza
    
    return results


def generate_clean_video(
    input_path: str,
    output_dir: str,
    output_filename: Optional[str] = None
) -> Optional[Path]:
    """
    Gera vídeo limpo sem fingerprints de IA.
    
    Args:
        input_path: Caminho do vídeo original
        output_dir: Diretório de saída
        output_filename: Nome do arquivo de saída (opcional)
        
    Returns:
        Caminho do arquivo gerado ou None se falhar
    """
    from src.utils import generate_clean_filename
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if output_filename:
        clean_file = output_path / output_filename
    else:
        clean_file = output_path / generate_clean_filename(input_path)
    
    results = clean_video(input_path, str(clean_file))
    
    if results["success"]:
        return clean_file
    else:
        return None

