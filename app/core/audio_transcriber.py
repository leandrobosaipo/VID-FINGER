"""Módulo de transcrição de áudio para extrair palavras-chave descritivas."""
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import re


def extract_audio(video_path: str, output_audio_path: Optional[str] = None) -> Optional[str]:
    """
    Extrai áudio do vídeo usando FFmpeg.
    
    Args:
        video_path: Caminho do vídeo
        output_audio_path: Caminho de saída do áudio (opcional, cria temp se None)
        
    Returns:
        Caminho do arquivo de áudio extraído ou None se falhar
    """
    if output_audio_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        output_audio_path = temp_file.name
        temp_file.close()
    
    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # Sem vídeo
            "-acodec", "pcm_s16le",  # WAV
            "-ar", "16000",  # 16kHz (suficiente para transcrição)
            "-ac", "1",  # Mono
            "-y",  # Sobrescrever
            output_audio_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_audio_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def has_audio_track(video_path: str) -> bool:
    """
    Verifica se o vídeo tem faixa de áudio.
    
    Args:
        video_path: Caminho do vídeo
        
    Returns:
        True se tem áudio, False caso contrário
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.DEVNULL)
        return result.returncode == 0 and "audio" in result.stdout
    except FileNotFoundError:
        return False


def transcribe_with_whisper(audio_path: str) -> Optional[str]:
    """
    Transcreve áudio usando Whisper (OpenAI).
    
    Args:
        audio_path: Caminho do arquivo de áudio
        
    Returns:
        Texto transcrito ou None se falhar
    """
    try:
        import whisper
        
        # Carrega modelo base (mais rápido, suficiente para palavras-chave)
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language="pt")
        
        return result.get("text", "")
    except ImportError:
        # Whisper não instalado
        return None
    except Exception:
        # Erro na transcrição
        return None


def extract_keywords_from_text(text: str, max_keywords: int = 3) -> List[str]:
    """
    Extrai palavras-chave principais do texto transcrito.
    
    Args:
        text: Texto transcrito
        max_keywords: Número máximo de palavras-chave
        
    Returns:
        Lista de palavras-chave em português
    """
    if not text:
        return []
    
    # Remove pontuação e converte para minúsculas
    text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Remove acentos básicos (simplificado)
    text_clean = text_clean.replace('á', 'a').replace('à', 'a').replace('ã', 'a').replace('â', 'a')
    text_clean = text_clean.replace('é', 'e').replace('ê', 'e')
    text_clean = text_clean.replace('í', 'i').replace('î', 'i')
    text_clean = text_clean.replace('ó', 'o').replace('ô', 'o').replace('õ', 'o')
    text_clean = text_clean.replace('ú', 'u').replace('û', 'u')
    text_clean = text_clean.replace('ç', 'c')
    
    # Palavras comuns a ignorar (stop words em português)
    stop_words = {
        'o', 'a', 'os', 'as', 'um', 'uma', 'de', 'do', 'da', 'dos', 'das',
        'em', 'no', 'na', 'nos', 'nas', 'para', 'com', 'por', 'que', 'e',
        'é', 'são', 'foi', 'ser', 'estar', 'ter', 'há', 'tem', 'têm',
        'me', 'te', 'se', 'lhe', 'nos', 'vos', 'lhes', 'meu', 'minha',
        'seu', 'sua', 'nossa', 'nossos', 'deles', 'delas', 'isso', 'isto',
        'aquilo', 'este', 'esta', 'esse', 'essa', 'aquele', 'aquela'
    }
    
    # Separa palavras
    words = text_clean.split()
    
    # Filtra stop words e palavras muito curtas
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    
    # Conta frequência
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Ordena por frequência e retorna top N
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    
    return [word for word, _ in sorted_words[:max_keywords]]


def transcribe_video(video_path: str) -> Dict[str, Any]:
    """
    Transcreve áudio do vídeo e extrai palavras-chave.
    
    Args:
        video_path: Caminho do vídeo
        
    Returns:
        Dicionário com transcrição e palavras-chave
    """
    # Verifica se tem áudio
    if not has_audio_track(video_path):
        return {
            "success": False,
            "has_audio": False,
            "transcription": "",
            "keywords": []
        }
    
    # Extrai áudio
    audio_path = extract_audio(video_path)
    if not audio_path:
        return {
            "success": False,
            "has_audio": True,
            "transcription": "",
            "keywords": []
        }
    
    try:
        # Tenta transcrever com Whisper
        transcription = transcribe_with_whisper(audio_path)
        
        if transcription:
            keywords = extract_keywords_from_text(transcription, max_keywords=3)
            
            return {
                "success": True,
                "has_audio": True,
                "transcription": transcription,
                "keywords": keywords
            }
        else:
            # Whisper não disponível ou falhou
            return {
                "success": False,
                "has_audio": True,
                "transcription": "",
                "keywords": [],
                "reason": "whisper_not_available"
            }
    finally:
        # Limpa arquivo temporário
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass

