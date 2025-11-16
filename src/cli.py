"""Interface de linha de comando para VID-FINGER V3."""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Ajusta o path para importar módulos locais
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.ffprobe_reader import extract_metadata, estimate_gop_size, estimate_gop_regularity
from src.core.fingerprint_logic import calculate_fingerprint
from src.core.video_classifier import classify_video
from src.core.prnu_detector import detect_prnu, analyze_prnu_per_frame
from src.core.fft_temporal import detect_diffusion_signature, analyze_temporal_jitter
from src.core.metadata_integrity import analyze_metadata_integrity
from src.core.timeline_analyzer import analyze_timeline
from src.core.cleaner import generate_clean_video
from src.utils import (
    generate_output_filename, validate_file, copy_file_to_output,
    ensure_output_dirs, generate_clean_filename
)


def create_forensic_report(
    video_path: str,
    metadata: dict,
    fingerprint: dict,
    classification: dict,
    prnu_analysis: dict,
    fft_analysis: dict,
    metadata_integrity: dict,
    timeline_analysis: dict,
    tool_signatures: list
) -> dict:
    """
    Cria relatório pericial completo em formato JSON.
    
    Args:
        video_path: Caminho do arquivo de vídeo
        metadata: Metadados extraídos
        fingerprint: Fingerprint calculado
        classification: Classificação do vídeo
        prnu_analysis: Análise PRNU
        fft_analysis: Análise FFT temporal
        metadata_integrity: Análise de integridade
        timeline_analysis: Análise de timeline
        tool_signatures: Assinaturas de ferramentas detectadas
        
    Returns:
        Dicionário com relatório pericial completo
    """
    model_probs = classification.get("model_probabilities", {})
    
    # Encontra modelo mais provável
    most_likely_model = None
    max_prob = 0.0
    for model, prob in model_probs.items():
        if prob > max_prob:
            max_prob = prob
            most_likely_model = model
    
    # Determina nível de confiança
    confidence_level = "baixa"
    conf_value = classification.get("confidence", 0.0)
    if conf_value >= 0.80:
        confidence_level = "alta"
    elif conf_value >= 0.60:
        confidence_level = "média"
    
    return {
        "file": str(Path(video_path).name),
        "file_path": video_path,
        "codec": metadata.get("codec_name"),
        "encoder": metadata.get("encoder"),
        "major_brand": metadata.get("major_brand"),
        "compatible_brands": metadata.get("compatible_brands"),
        "duration": metadata.get("duration"),
        "bit_rate": metadata.get("bit_rate"),
        "frame_rate": metadata.get("frame_rate"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "gop_estimate": metadata.get("gop_size") or fingerprint.get("gop_analysis", {}).get("gop_size"),
        "qp_pattern": fingerprint.get("qp_analysis", {}).get("pattern"),
        "classification": classification.get("classification"),
        "confidence": classification.get("confidence"),
        "confidence_level": confidence_level,
        "reason": classification.get("reason"),
        "most_likely_model": most_likely_model,
        "model_probabilities": model_probs,
        "prnu_analysis": prnu_analysis,
        "fft_analysis": fft_analysis,
        "metadata_integrity": metadata_integrity,
        "timeline": timeline_analysis.get("timeline", []),
        "hybrid_analysis": timeline_analysis.get("hybrid_analysis", {}),
        "timeline_summary": timeline_analysis.get("summary", {}),
        "tool_signatures": tool_signatures,
        "fingerprint": fingerprint
    }


def convert_to_json_serializable(obj):
    """
    Converte objetos numpy e outros tipos não serializáveis para tipos Python nativos.
    
    Args:
        obj: Objeto a converter
        
    Returns:
        Objeto convertido
    """
    import numpy as np
    
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (bool, int, float, str, type(None))):
        return obj
    else:
        return str(obj)


def save_report(report: dict, output_dir: Path, filename: str) -> Path:
    """
    Salva relatório em arquivo JSON.
    
    Args:
        report: Relatório a ser salvo
        output_dir: Diretório de saída
        filename: Nome do arquivo
        
    Returns:
        Caminho do arquivo salvo
    """
    file_path = output_dir / filename
    
    # Converte para tipos JSON serializáveis
    serializable_report = convert_to_json_serializable(report)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(serializable_report, f, indent=2, ensure_ascii=False)
    
    return file_path


def print_summary(report: dict, original_file: Path, report_file: Path, clean_file: Optional[Path]):
    """
    Imprime resumo no terminal.
    
    Args:
        report: Relatório gerado
        original_file: Caminho do arquivo original copiado
        report_file: Caminho do relatório JSON
        clean_file: Caminho do vídeo limpo (opcional)
    """
    classification = report.get("classification", "UNKNOWN")
    confidence = report.get("confidence", 0.0)
    confidence_level = report.get("confidence_level", "baixa")
    reason = report.get("reason", "")
    timeline_summary = report.get("timeline_summary", {})
    hybrid_analysis = report.get("hybrid_analysis", {})
    tool_signatures = report.get("tool_signatures", [])
    
    print("\n" + "=" * 70)
    print("VID-FINGER V3 - Relatório Forense de Análise")
    print("=" * 70)
    print(f"\nArquivo: {report.get('file', 'N/A')}")
    print(f"Codec: {report.get('codec', 'N/A')}")
    print(f"Encoder: {report.get('encoder', 'N/A')}")
    print(f"Resolução: {report.get('width', 'N/A')}x{report.get('height', 'N/A')}")
    print(f"Frame Rate: {report.get('frame_rate', 'N/A')} fps")
    print(f"Duração: {report.get('duration', 'N/A')}s")
    
    print("\n" + "-" * 70)
    print(f"Classificação: {classification}")
    print(f"Confiança: {confidence:.2%} ({confidence_level})")
    print(f"Razão: {reason}")
    
    # Mostra análise híbrida se aplicável
    if hybrid_analysis.get("is_hybrid"):
        print(f"\nConteúdo Híbrido Detectado:")
        print(f"  - Real: {hybrid_analysis.get('real_percentage', 0):.1f}%")
        print(f"  - IA: {hybrid_analysis.get('ai_percentage', 0):.1f}%")
        print(f"  - Transições: {len(hybrid_analysis.get('transitions', []))}")
    
    # Mostra ferramentas detectadas
    if tool_signatures:
        print(f"\nFerramentas Detectadas:")
        for tool in tool_signatures:
            print(f"  • {tool.get('tool', 'N/A')} (confiança: {tool.get('confidence', 0):.1%})")
    
    # Mostra resumo da timeline
    if timeline_summary:
        origin_dist = timeline_summary.get("origin_distribution", {})
        if origin_dist:
            print(f"\nDistribuição de Origem:")
            for origin, pct in origin_dist.items():
                print(f"  - {origin}: {pct:.1f}%")
    
    print("-" * 70)
    print(f"\nEntregáveis Gerados:")
    print(f"  1. Original: {original_file}")
    print(f"  2. Relatório: {report_file}")
    if clean_file:
        print(f"  3. Vídeo Limpo: {clean_file}")
    else:
        print(f"  3. Vídeo Limpo: (não gerado)")
    print("=" * 70 + "\n")


def main():
    """Função principal do CLI."""
    parser = argparse.ArgumentParser(
        description="VID-FINGER V3 - Forensic AI Fingerprint Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 src/cli.py --input "/caminho/do/video.mp4"
  python3 src/cli.py --input video.mp4 --output-dir ./output
        """
    )
    
    parser.add_argument(
        "--input",
        "-i",
        required=False,
        help="Caminho para o arquivo de vídeo (obrigatório se não usar --calibrate)"
    )
    
    parser.add_argument(
        "--output-dir",
        "-o",
        default="output",
        help="Diretório base para salvar entregáveis (padrão: output)"
    )
    
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Pula geração do vídeo limpo (mais rápido)"
    )
    
    parser.add_argument(
        "--calibrate",
        metavar="VIDEO",
        help="Calibra sensor usando vídeo real (ex: vídeo do iPhone)"
    )
    
    parser.add_argument(
        "--baseline-profile",
        metavar="PATH",
        help="Caminho para arquivo de perfil baseline (padrão: sensor_profile.json)"
    )
    
    args = parser.parse_args()
    
    # Se modo calibração, executa e sai
    if args.calibrate:
        from src.core.sensor_calibration import extract_sensor_fingerprint, save_sensor_profile
        
        print("Calibrando sensor...")
        print(f"Analisando vídeo: {args.calibrate}")
        
        fingerprint = extract_sensor_fingerprint(args.calibrate)
        
        if fingerprint:
            profile_path = args.baseline_profile or "sensor_profile.json"
            if save_sensor_profile(fingerprint, profile_path):
                print(f"✓ Perfil do sensor salvo em: {profile_path}")
                print(f"  - Variância PRNU média: {fingerprint['prnu_characteristics']['avg_variance']:.6f}")
                print(f"  - Correlação média: {fingerprint['prnu_characteristics']['avg_correlation']:.4f}")
                print(f"  - Frames analisados: {fingerprint['temporal_characteristics']['frames_analyzed']}")
            else:
                print("ERRO: Falha ao salvar perfil do sensor", file=sys.stderr)
                sys.exit(1)
        else:
            print("ERRO: Falha ao extrair fingerprint do sensor", file=sys.stderr)
            sys.exit(1)
        
        sys.exit(0)
    
    # Valida que --input foi fornecido se não está em modo calibração
    if not args.input:
        print("ERRO: --input é obrigatório quando não está em modo calibração", file=sys.stderr)
        sys.exit(1)
    
    # Valida arquivo
    is_valid, error_msg = validate_file(args.input)
    if not is_valid:
        print(f"ERRO: {error_msg}", file=sys.stderr)
        sys.exit(1)
    
    # Garante estrutura de diretórios
    output_dirs = ensure_output_dirs(args.output_dir)
    
    try:
        # 1. Extrai metadados (necessário para gerar nomes SEO-friendly)
        print("Extraindo metadados do vídeo...")
        metadata = extract_metadata(args.input)
        
        # 2. Estima GOP
        print("Estimando tamanho do GOP e regularidade...")
        gop_size = estimate_gop_size(args.input)
        gop_regularity = estimate_gop_regularity(args.input)
        
        # 3. Calcula fingerprint técnico
        print("Calculando fingerprint técnico...")
        fingerprint = calculate_fingerprint(metadata, gop_size, gop_regularity)
        
        # 4. Carrega baseline se disponível
        baseline_profile = None
        baseline_path = args.baseline_profile or "sensor_profile.json"
        if Path(baseline_path).exists():
            from src.core.sensor_calibration import load_sensor_profile
            baseline_profile = load_sensor_profile(baseline_path)
            if baseline_profile:
                print(f"Baseline carregado: {baseline_path}")
        
        # 5. Análise PRNU (com baseline se disponível)
        print("Analisando PRNU (ruído do sensor)...")
        prnu_analysis = detect_prnu(args.input, baseline_profile)
        prnu_frame_analysis = prnu_analysis.get("frame_analysis", [])
        
        # 6. Análise FFT Temporal
        print("Analisando padrões FFT temporais...")
        fft_analysis = detect_diffusion_signature(args.input)
        jitter_analysis = analyze_temporal_jitter(args.input)
        fft_analysis["jitter_analysis"] = jitter_analysis
        
        # 7. Integridade de Metadados
        print("Verificando integridade de metadados...")
        metadata_integrity = analyze_metadata_integrity(metadata)
        tool_signatures = metadata_integrity.get("tool_signatures", [])
        
        # 8. Classificação Preliminar (para override de timeline)
        print("Classificando vídeo...")
        preliminary_classification = classify_video(
            fingerprint,
            metadata_integrity,
            None  # Sem timeline ainda
        )
        macro_classification = preliminary_classification.get("classification")
        
        # 9. Análise de Timeline (com override baseado em classificação)
        print("Gerando timeline frame a frame...")
        timeline_analysis = analyze_timeline(
            prnu_frame_analysis,
            fft_analysis,
            metadata_integrity,
            fingerprint,
            macro_classification  # Passa classificação para override
        )
        
        # 10. Classificação Final (com timeline completa)
        classification = classify_video(
            fingerprint,
            metadata_integrity,
            timeline_analysis
        )
        final_classification = classification.get("classification")
        
        # 10. Gera nomes SEO-friendly para todos os arquivos
        from src.core.video_content_analyzer import generate_seo_friendly_name, sanitize_filename
        
        seo_base = generate_seo_friendly_name(args.input, final_classification, metadata)
        
        # Nome do arquivo original com SEO
        original_ext = Path(args.input).suffix
        original_seo_name = sanitize_filename(f"{seo_base}-original{original_ext}")
        
        # Copia arquivo original com nome SEO-friendly
        print("Copiando arquivo original...")
        original_file = copy_file_to_output(
            args.input,
            args.output_dir,
            "original",
            original_seo_name
        )
        
        # 11. Cria relatório pericial
        print("Gerando relatório pericial...")
        report = create_forensic_report(
            args.input,
            metadata,
            fingerprint,
            classification,
            prnu_analysis,
            fft_analysis,
            metadata_integrity,
            timeline_analysis,
            tool_signatures
        )
        
        # 12. Salva relatório com nome SEO-friendly
        report_filename = generate_output_filename(args.input, final_classification, metadata)
        report_file = save_report(report, output_dirs["reports"], report_filename)
        
        # 13. Análise de conteúdo para nome descritivo (se não foi pulado)
        visual_analysis = None
        audio_analysis = None
        if not args.skip_clean:
            print("Analisando conteúdo do vídeo para nome descritivo...")
            from src.core.content_analyzer import analyze_visual_content
            from src.core.audio_transcriber import transcribe_video
            
            # Análise visual
            try:
                visual_analysis = analyze_visual_content(args.input)
            except Exception as e:
                print(f"Aviso: Falha na análise visual: {e}")
                visual_analysis = {"success": False}
            
            # Transcrição de áudio (opcional, pode falhar se Whisper não disponível)
            try:
                audio_analysis = transcribe_video(args.input)
                if not audio_analysis.get("success"):
                    # Não é erro crítico se não tiver áudio ou Whisper não disponível
                    pass
            except Exception as e:
                print(f"Aviso: Transcrição de áudio não disponível: {e}")
                audio_analysis = {"success": False, "has_audio": False}
        
        # 14. Gera vídeo limpo (se não foi pulado) com nome descritivo humano
        clean_file = None
        if not args.skip_clean:
            print("Gerando vídeo limpo (sem fingerprints de IA)...")
            clean_filename = generate_clean_filename(args.input, visual_analysis, audio_analysis)
            clean_file = generate_clean_video(
                args.input,
                str(output_dirs["clean"]),
                clean_filename
            )
            if clean_file:
                print(f"Vídeo limpo gerado: {clean_file}")
            else:
                print("Aviso: Falha ao gerar vídeo limpo")
        
        # 15. Exibe resumo
        print_summary(report, original_file, report_file, clean_file)
        
    except FileNotFoundError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        print("\nInstale FFmpeg: https://ffmpeg.org/download.html", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        error_report = {
            "error": True,
            "message": str(e),
            "traceback": traceback.format_exc(),
            "file": args.input
        }
        error_file = output_dirs["reports"] / "error_report.json"
        
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(error_report, f, indent=2, ensure_ascii=False)
        
        print(f"ERRO: {e}", file=sys.stderr)
        print(f"Relatório de erro salvo em: {error_file}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
