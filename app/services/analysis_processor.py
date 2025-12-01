"""Processador de análise de vídeo."""
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import numpy as np

from app.models.analysis import Analysis, AnalysisStatus
from app.models.file import File, FileType
from app.models.analysis_step import AnalysisStep, StepName, StepStatus
from app.services.file_service import FileService
from app.core.ffprobe_reader import extract_metadata, estimate_gop_size, estimate_gop_regularity
from app.core.fingerprint_logic import calculate_fingerprint
from app.core.video_classifier import classify_video
from app.core.prnu_detector import detect_prnu
from app.core.fft_temporal import detect_diffusion_signature, analyze_temporal_jitter
from app.core.metadata_integrity import analyze_metadata_integrity
from app.core.timeline_analyzer import analyze_timeline
from app.core.cleaner import generate_clean_video
from app.services.webhook_service import WebhookService
from app.services.storage_service import storage_service
from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AnalysisProcessor:
    """Processa análises de vídeo."""
    
    @staticmethod
    async def process_analysis(analysis_id: str, db: AsyncSession):
        """
        Processa análise completa de vídeo.
        
        Executa todas as etapas:
        1. Extração de metadados
        2. Análise PRNU
        3. Análise FFT
        4. Classificação
        5. Geração de relatório
        6. Geração de vídeo limpo
        """
        try:
            # Buscar análise
            analysis_uuid = uuid.UUID(analysis_id)
            result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_uuid)
            )
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                logger.error(f"Análise não encontrada: {analysis_id}")
                return
            
            # Buscar arquivo original
            if not analysis.original_file_id:
                logger.error(f"Arquivo original não encontrado para análise {analysis_id}")
                return
            
            result = await db.execute(
                select(File).where(File.id == analysis.original_file_id)
            )
            original_file = result.scalar_one_or_none()
            
            if not original_file:
                logger.error(f"Arquivo original não encontrado: {analysis.original_file_id}")
                return
            
            video_path = Path(original_file.file_path)
            if not video_path.exists():
                logger.error(f"Arquivo de vídeo não encontrado: {video_path}")
                return
            
            # Atualizar status para analyzing
            analysis.status = AnalysisStatus.analyzing
            analysis.started_at = datetime.utcnow()
            await db.commit()
            await db.refresh(analysis)
            
            # Enviar webhook de início
            if analysis.webhook_url:
                try:
                    await WebhookService.send_webhook(
                        webhook_url=analysis.webhook_url,
                        event="analysis.started",
                        analysis_id=analysis_id,
                        data={"status": "analyzing"}
                    )
                except Exception as e:
                    logger.error(f"Erro ao enviar webhook: {e}")
            
            # 1. Extração de metadados
            logger.info(f"[{analysis_id}] ===== INICIANDO ETAPA: metadata_extraction =====")
            await AnalysisProcessor._update_step(
                analysis_id, StepName.metadata_extraction, StepStatus.running, 0, db
            )
            
            # Enviar webhook de início da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.metadata_extraction,
                        is_starting=True,
                        db=db
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de início: {e}")
            
            logger.info(f"[{analysis_id}] Extraindo metadados do arquivo: {video_path}")
            metadata = extract_metadata(str(video_path))
            gop_size = estimate_gop_size(str(video_path))
            gop_regularity = estimate_gop_regularity(str(video_path))
            fingerprint = calculate_fingerprint(metadata, gop_size, gop_regularity)
            
            # Salvar metadados na análise (como JSON string)
            try:
                analysis.video_metadata = json.dumps(metadata) if isinstance(metadata, dict) else metadata
            except (TypeError, ValueError) as e:
                logger.warning(f"[{analysis_id}] Erro ao serializar metadados: {e}")
                analysis.video_metadata = json.dumps({"error": "Failed to serialize metadata"})
            await db.commit()
            
            await AnalysisProcessor._update_step(
                analysis_id, StepName.metadata_extraction, StepStatus.completed, 100, db
            )
            await db.refresh(analysis)
            
            # Enviar webhook de conclusão da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.metadata_extraction,
                        is_starting=False,
                        db=db,
                        step_result={"metadata": metadata}
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
            
            logger.info(f"[{analysis_id}] ===== ETAPA CONCLUÍDA: metadata_extraction =====")
            
            # 2. Análise PRNU
            logger.info(f"[{analysis_id}] ===== INICIANDO ETAPA: prnu =====")
            await AnalysisProcessor._update_step(
                analysis_id, StepName.prnu, StepStatus.running, 0, db
            )
            
            # Enviar webhook de início da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.prnu,
                        is_starting=True,
                        db=db
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de início: {e}")
            
            logger.info(f"[{analysis_id}] Analisando PRNU (ruído do sensor)...")
            baseline_profile = None  # TODO: Carregar baseline se disponível
            prnu_analysis = detect_prnu(str(video_path), baseline_profile)
            prnu_frame_analysis = prnu_analysis.get("frame_analysis", [])
            
            await AnalysisProcessor._update_step(
                analysis_id, StepName.prnu, StepStatus.completed, 100, db
            )
            await db.refresh(analysis)
            
            # Enviar webhook de conclusão da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.prnu,
                        is_starting=False,
                        db=db,
                        step_result=prnu_analysis
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
            
            logger.info(f"[{analysis_id}] ===== ETAPA CONCLUÍDA: prnu =====")
            
            # 3. Análise FFT
            logger.info(f"[{analysis_id}] ===== INICIANDO ETAPA: fft =====")
            await AnalysisProcessor._update_step(
                analysis_id, StepName.fft, StepStatus.running, 0, db
            )
            
            # Enviar webhook de início da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.fft,
                        is_starting=True,
                        db=db
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de início: {e}")
            
            logger.info(f"[{analysis_id}] Analisando FFT temporal...")
            fft_analysis = detect_diffusion_signature(str(video_path))
            jitter_analysis = analyze_temporal_jitter(str(video_path))
            fft_analysis["jitter_analysis"] = jitter_analysis
            
            await AnalysisProcessor._update_step(
                analysis_id, StepName.fft, StepStatus.completed, 100, db
            )
            await db.refresh(analysis)
            
            # Enviar webhook de conclusão da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.fft,
                        is_starting=False,
                        db=db,
                        step_result=fft_analysis
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
            
            logger.info(f"[{analysis_id}] ===== ETAPA CONCLUÍDA: fft =====")
            
            # 4. Integridade de metadados
            metadata_integrity = analyze_metadata_integrity(metadata)
            tool_signatures = metadata_integrity.get("tool_signatures", [])
            
            # 5. Classificação preliminar
            preliminary_classification = classify_video(
                fingerprint,
                metadata_integrity,
                None
            )
            macro_classification = preliminary_classification.get("classification")
            
            # 6. Análise de timeline
            timeline_analysis = analyze_timeline(
                prnu_frame_analysis,
                fft_analysis,
                metadata_integrity,
                fingerprint,
                macro_classification
            )
            
            # 7. Classificação final
            logger.info(f"[{analysis_id}] ===== INICIANDO ETAPA: classification =====")
            await AnalysisProcessor._update_step(
                analysis_id, StepName.classification, StepStatus.running, 0, db
            )
            
            # Enviar webhook de início da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.classification,
                        is_starting=True,
                        db=db
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de início: {e}")
            
            logger.info(f"[{analysis_id}] Classificando vídeo com base em todas as análises...")
            classification = classify_video(
                fingerprint,
                metadata_integrity,
                timeline_analysis
            )
            
            final_classification = classification.get("classification")
            confidence = classification.get("confidence", 0.0)
            
            analysis.classification = final_classification
            analysis.confidence = confidence
            await db.commit()
            
            await AnalysisProcessor._update_step(
                analysis_id, StepName.classification, StepStatus.completed, 100, db
            )
            await db.refresh(analysis)
            
            # Enviar webhook de conclusão da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.classification,
                        is_starting=False,
                        db=db,
                        step_result=classification
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
            
            logger.info(f"[{analysis_id}] ===== ETAPA CONCLUÍDA: classification (Classificação: {final_classification}, Confiança: {confidence:.2%}) =====")
            
            # 8. Gerar relatório
            logger.info(f"[{analysis_id}] ===== INICIANDO ETAPA: report_generation =====")
            report_start_time = datetime.utcnow()
            
            # Enviar webhook de início da etapa (report_generation não tem AnalysisStep)
            if analysis.webhook_url:
                try:
                    stats = await WebhookService._collect_step_statistics(analysis_id, db)
                    await WebhookService.send_webhook(
                        webhook_url=analysis.webhook_url,
                        event="analysis.step.started",
                        analysis_id=analysis_id,
                        data={
                            "current_step": {
                                "name": "report_generation",
                                "status": "running",
                                "started_at": report_start_time.isoformat() + "Z"
                            },
                            "completed_steps": stats["completed_steps"],
                            "pending_steps": ["cleaning"],
                            "statistics": stats["statistics"],
                            "analysis": stats["analysis"]
                        }
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de início: {e}")
            
            logger.info(f"[{analysis_id}] Gerando relatório forense completo...")
            try:
                report = AnalysisProcessor._create_report(
                    str(video_path),
                    metadata,
                    fingerprint,
                    classification,
                    prnu_analysis,
                    fft_analysis,
                    metadata_integrity,
                    timeline_analysis,
                    tool_signatures
                )
                
                # Salvar relatório
                report_dir = FileService.generate_storage_path(str(analysis_id), FileType.report)
                report_dir.mkdir(parents=True, exist_ok=True)
                report_filename = FileService.generate_filename(
                    original_file.original_filename,
                    FileType.report
                )
                report_path = report_dir / report_filename
                
                logger.info(f"[{analysis_id}] Salvando relatório em: {report_path}")
                # Converter valores numpy para tipos Python nativos antes de serializar
                report_serializable = AnalysisProcessor._convert_to_serializable(report)
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(report_serializable, f, indent=2, ensure_ascii=False)
                
                # Verificar se arquivo foi criado
                if not report_path.exists():
                    raise FileNotFoundError(f"Relatório não foi criado: {report_path}")
                
                # Obter tamanho do arquivo
                report_size = report_path.stat().st_size
                if report_size == 0:
                    raise ValueError(f"Relatório está vazio: {report_path}")
                
                # Criar registro de arquivo de relatório
                logger.info(f"[{analysis_id}] Criando registro de arquivo de relatório no banco...")
                report_file_id = uuid.uuid4()
                report_file = File(
                    id=report_file_id,
                    analysis_id=analysis_uuid,
                    file_type=FileType.report,
                    original_filename=report_filename,
                    stored_filename=report_filename,
                    file_path=str(report_path),
                    file_size=report_size,
                    mime_type="application/json",
                    checksum=FileService.calculate_checksum(report_path)
                )
                logger.info(f"[{analysis_id}] Adicionando report_file ao banco: {report_file_id}")
                db.add(report_file)
                
                # Buscar análise novamente para garantir que está na sessão atual
                logger.info(f"[{analysis_id}] Buscando análise novamente na sessão atual...")
                result = await db.execute(
                    select(Analysis).where(Analysis.id == analysis_uuid)
                )
                analysis = result.scalar_one_or_none()
                
                if not analysis:
                    raise ValueError(f"Análise não encontrada após buscar novamente: {analysis_id}")
                
                logger.info(f"[{analysis_id}] Setando report_file_id na análise: {report_file_id}")
                analysis.report_file_id = report_file_id
                
                logger.info(f"[{analysis_id}] Fazendo commit do relatório...")
                try:
                    await db.commit()
                    logger.info(f"[{analysis_id}] Commit concluído com sucesso")
                except Exception as commit_error:
                    logger.error(f"[{analysis_id}] ❌ ERRO no commit: {commit_error}", exc_info=True)
                    await db.rollback()
                    raise
                
                logger.info(f"[{analysis_id}] Fazendo refresh da análise...")
                await db.refresh(analysis)
                
                # Verificar se commit realmente funcionou
                if analysis.report_file_id != report_file_id:
                    logger.error(f"[{analysis_id}] ⚠️ ATENÇÃO: report_file_id não foi salvo após refresh! Esperado: {report_file_id}, Atual: {analysis.report_file_id}")
                    # Tentar buscar novamente e atualizar
                    result = await db.execute(
                        select(Analysis).where(Analysis.id == analysis_uuid)
                    )
                    analysis = result.scalar_one_or_none()
                    if analysis and not analysis.report_file_id:
                        logger.info(f"[{analysis_id}] Tentando corrigir: atualizando report_file_id novamente...")
                        analysis.report_file_id = report_file_id
                        await db.commit()
                        await db.refresh(analysis)
                        logger.info(f"[{analysis_id}] Após correção: report_file_id = {analysis.report_file_id}")
                
                logger.info(f"[{analysis_id}] Refresh concluído. report_file_id na análise: {analysis.report_file_id}")
                
                # Upload para CDN se configurado
                if settings.UPLOAD_TO_CDN and storage_service.s3_client:
                    try:
                        logger.info(f"[{analysis_id}] Fazendo upload do relatório para CDN...")
                        key = storage_service.generate_key(
                            str(analysis_id),
                            "report",
                            report_filename
                        )
                        cdn_url = storage_service.upload_file(
                            report_path,
                            key,
                            content_type="application/json",
                            analysis_id=str(analysis_id)
                        )
                        if cdn_url:
                            report_file.cdn_url = cdn_url
                            report_file.cdn_uploaded = True
                            await db.commit()
                            await db.refresh(report_file)
                            logger.info(f"[{analysis_id}] ✅ Relatório enviado para CDN: {cdn_url}")
                        else:
                            logger.warning(f"[{analysis_id}] ⚠️ Falha ao fazer upload do relatório para CDN")
                    except Exception as cdn_error:
                        logger.error(f"[{analysis_id}] Erro ao fazer upload do relatório para CDN: {cdn_error}", exc_info=True)
                        # Não falhar análise por causa do upload CDN
                
                logger.info(f"[{analysis_id}] ✅ Relatório salvo com sucesso: {report_file_id}")
                
                # Enviar webhook de conclusão da etapa report_generation
                if analysis.webhook_url:
                    try:
                        report_end_time = datetime.utcnow()
                        report_duration = (report_end_time - report_start_time).total_seconds()
                        
                        # Buscar report_file atualizado para obter CDN URL
                        result = await db.execute(
                            select(File).where(File.id == report_file_id)
                        )
                        report_file_updated = result.scalar_one_or_none()
                        cdn_url = None
                        if report_file_updated and report_file_updated.cdn_url:
                            cdn_url = report_file_updated.cdn_url
                        
                        stats = await WebhookService._collect_step_statistics(analysis_id, db)
                        await WebhookService.send_webhook(
                            webhook_url=analysis.webhook_url,
                            event="analysis.step.completed",
                            analysis_id=analysis_id,
                            data={
                                "current_step": {
                                    "name": "report_generation",
                                    "status": "completed",
                                    "started_at": report_start_time.isoformat() + "Z",
                                    "completed_at": report_end_time.isoformat() + "Z",
                                    "duration_seconds": round(report_duration, 2),
                                    "result": {
                                        "report_generated": True,
                                        "report_file_id": str(report_file_id),
                                        "cdn_url": cdn_url
                                    }
                                },
                                "completed_steps": stats["completed_steps"] + [{
                                    "name": "report_generation",
                                    "status": "completed",
                                    "started_at": report_start_time.isoformat() + "Z",
                                    "completed_at": report_end_time.isoformat() + "Z",
                                    "duration_seconds": round(report_duration, 2),
                                    "result": {
                                        "report_generated": True,
                                        "report_file_id": str(report_file_id),
                                        "cdn_url": cdn_url
                                    }
                                }],
                                "pending_steps": ["cleaning"],
                                "statistics": stats["statistics"],
                                "analysis": stats["analysis"]
                            }
                        )
                    except Exception as e:
                        logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
                
                logger.info(f"[{analysis_id}] ===== ETAPA CONCLUÍDA: report_generation =====")
            except Exception as report_error:
                logger.error(f"[{analysis_id}] Erro ao salvar relatório: {report_error}", exc_info=True)
                logger.warning(f"[{analysis_id}] ===== ETAPA FALHOU: report_generation (continuando análise) =====")
                # Não falhar análise completa por causa do relatório, apenas logar erro
                # Continuar processamento mesmo se relatório falhar
            
            # 9. Gerar vídeo limpo (opcional, não bloqueia análise se falhar)
            logger.info(f"[{analysis_id}] ===== INICIANDO ETAPA: cleaning =====")
            await AnalysisProcessor._update_step(
                analysis_id, StepName.cleaning, StepStatus.running, 0, db
            )
            
            # Enviar webhook de início da etapa
            if analysis.webhook_url:
                try:
                    await WebhookService.send_step_update(
                        webhook_url=analysis.webhook_url,
                        analysis_id=analysis_id,
                        step_name=StepName.cleaning,
                        is_starting=True,
                        db=db
                    )
                except Exception as e:
                    logger.error(f"[{analysis_id}] Erro ao enviar webhook de início: {e}")
            
            logger.info(f"[{analysis_id}] Gerando vídeo limpo (removendo fingerprints de IA)...")
            
            # Verificar se FFmpeg está disponível antes de tentar
            from app.core.cleaner import check_ffmpeg_available
            ffmpeg_available = check_ffmpeg_available()
            if not ffmpeg_available:
                logger.warning(f"[{analysis_id}] FFmpeg não disponível, pulando geração de vídeo limpo")
                await AnalysisProcessor._update_step(
                    analysis_id, StepName.cleaning, StepStatus.completed, 100, db
                )
                await db.refresh(analysis)
                
                # Enviar webhook de conclusão da etapa (pulada)
                if analysis.webhook_url:
                    try:
                        await WebhookService.send_step_update(
                            webhook_url=analysis.webhook_url,
                            analysis_id=analysis_id,
                            step_name=StepName.cleaning,
                            is_starting=False,
                            db=db,
                            step_result={"skipped": True, "reason": "FFmpeg não disponível"}
                        )
                    except Exception as e:
                        logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
            else:
                clean_dir = FileService.generate_storage_path(str(analysis_id), FileType.clean_video)
                clean_dir.mkdir(parents=True, exist_ok=True)
                clean_filename = FileService.generate_filename(
                    original_file.original_filename,
                    FileType.clean_video
                )
                
                # generate_clean_video retorna Path ou None
                clean_result = None
                try:
                    clean_result = generate_clean_video(
                        str(video_path),
                        str(clean_dir),
                        clean_filename
                    )
                except Exception as clean_error:
                    logger.error(f"[{analysis_id}] Erro ao gerar vídeo limpo: {clean_error}", exc_info=True)
                    clean_result = None
                
                if clean_result and Path(clean_result).exists():
                    try:
                        clean_file_id = uuid.uuid4()
                        clean_file = File(
                            id=clean_file_id,
                            analysis_id=analysis_uuid,
                            file_type=FileType.clean_video,
                            original_filename=clean_filename,
                            stored_filename=clean_filename,
                            file_path=str(clean_result),
                            file_size=Path(clean_result).stat().st_size,
                            mime_type=original_file.mime_type,
                            checksum=FileService.calculate_checksum(Path(clean_result))
                        )
                        logger.info(f"[{analysis_id}] Adicionando clean_file ao banco: {clean_file_id}")
                        db.add(clean_file)
                        
                        # Fazer flush para garantir que clean_file seja inserido antes de atualizar analysis
                        await db.flush()
                        logger.info(f"[{analysis_id}] Flush concluído, clean_file inserido no banco")
                        
                        # Buscar análise novamente para garantir que está na sessão atual
                        logger.info(f"[{analysis_id}] Buscando análise novamente na sessão atual...")
                        result = await db.execute(
                            select(Analysis).where(Analysis.id == analysis_uuid)
                        )
                        analysis = result.scalar_one_or_none()
                        
                        if not analysis:
                            raise ValueError(f"Análise não encontrada após buscar novamente: {analysis_id}")
                        
                        logger.info(f"[{analysis_id}] Setando clean_video_id na análise: {clean_file_id}")
                        analysis.clean_video_id = clean_file_id
                        
                        logger.info(f"[{analysis_id}] Fazendo commit do vídeo limpo...")
                        try:
                            await db.commit()
                            logger.info(f"[{analysis_id}] Commit concluído com sucesso")
                        except Exception as commit_error:
                            logger.error(f"[{analysis_id}] ❌ ERRO no commit: {commit_error}", exc_info=True)
                            await db.rollback()
                            raise
                        
                        await db.refresh(analysis)
                        logger.info(f"[{analysis_id}] Vídeo limpo salvo: {clean_file_id}")
                        
                        # Upload para CDN se configurado
                        if settings.UPLOAD_TO_CDN and storage_service.s3_client:
                            try:
                                logger.info(f"[{analysis_id}] Fazendo upload do vídeo limpo para CDN...")
                                key = storage_service.generate_key(
                                    str(analysis_id),
                                    "clean_video",
                                    clean_filename
                                )
                                cdn_url = storage_service.upload_file(
                                    Path(clean_result),
                                    key,
                                    content_type=original_file.mime_type,
                                    analysis_id=str(analysis_id)
                                )
                                if cdn_url:
                                    clean_file.cdn_url = cdn_url
                                    clean_file.cdn_uploaded = True
                                    await db.commit()
                                    await db.refresh(clean_file)
                                    logger.info(f"[{analysis_id}] ✅ Vídeo limpo enviado para CDN: {cdn_url}")
                                else:
                                    logger.warning(f"[{analysis_id}] ⚠️ Falha ao fazer upload do vídeo limpo para CDN")
                            except Exception as cdn_error:
                                logger.error(f"[{analysis_id}] Erro ao fazer upload do vídeo limpo para CDN: {cdn_error}", exc_info=True)
                                # Não falhar análise por causa do upload CDN
                    except Exception as save_error:
                        logger.error(f"[{analysis_id}] ❌ Erro ao salvar vídeo limpo no banco: {save_error}", exc_info=True)
                        # Fazer rollback para limpar a sessão
                        try:
                            await db.rollback()
                            logger.info(f"[{analysis_id}] Rollback executado após erro ao salvar vídeo limpo")
                        except Exception as rollback_error:
                            logger.error(f"[{analysis_id}] Erro ao fazer rollback: {rollback_error}", exc_info=True)
                        # Continuar mesmo se falhar ao salvar no banco - análise pode ser concluída sem vídeo limpo
                        logger.warning(f"[{analysis_id}] Continuando análise sem vídeo limpo devido ao erro")
                
                await AnalysisProcessor._update_step(
                    analysis_id, StepName.cleaning, StepStatus.completed, 100, db
                )
                await db.refresh(analysis)
                
                # Enviar webhook de conclusão da etapa
                if analysis.webhook_url:
                    try:
                        clean_result_data = {}
                        if analysis.clean_video_id:
                            clean_result_data = {
                                "clean_video_generated": True,
                                "clean_video_id": str(analysis.clean_video_id)
                            }
                            # Tentar obter URL do CDN se disponível
                            result = await db.execute(
                                select(File).where(File.id == analysis.clean_video_id)
                            )
                            clean_file_obj = result.scalar_one_or_none()
                            if clean_file_obj and clean_file_obj.cdn_url:
                                clean_result_data["cdn_url"] = clean_file_obj.cdn_url
                        
                        await WebhookService.send_step_update(
                            webhook_url=analysis.webhook_url,
                            analysis_id=analysis_id,
                            step_name=StepName.cleaning,
                            is_starting=False,
                            db=db,
                            step_result=clean_result_data if clean_result_data else None
                        )
                    except Exception as e:
                        logger.error(f"[{analysis_id}] Erro ao enviar webhook de conclusão: {e}")
                
                logger.info(f"[{analysis_id}] ===== ETAPA CONCLUÍDA: cleaning =====")
            
            # Finalizar análise
            logger.info(f"[{analysis_id}] ===== FINALIZANDO ANÁLISE =====")
            
            # Buscar análise novamente para garantir que está na sessão atual
            result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_uuid)
            )
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                raise ValueError(f"Análise não encontrada ao finalizar: {analysis_id}")
            
            logger.info(f"[{analysis_id}] Status atual: {analysis.status}")
            logger.info(f"[{analysis_id}] report_file_id atual: {analysis.report_file_id}")
            
            analysis.status = AnalysisStatus.completed
            analysis.completed_at = datetime.utcnow()
            await db.commit()
            await db.refresh(analysis)
            
            logger.info(f"[{analysis_id}] Após finalizar - report_file_id: {analysis.report_file_id}")
            
            logger.info(f"[{analysis_id}] ✅✅✅ ANÁLISE CONCLUÍDA COM SUCESSO! ✅✅✅")
            logger.info(f"[{analysis_id}] - Classificação: {final_classification}")
            logger.info(f"[{analysis_id}] - Confiança: {confidence:.2%}")
            logger.info(f"[{analysis_id}] - Relatório: {'Sim' if analysis.report_file_id else 'Não'}")
            logger.info(f"[{analysis_id}] - Vídeo limpo: {'Sim' if analysis.clean_video_id else 'Não'}")
            
            # Enviar webhook de conclusão
            if analysis.webhook_url:
                try:
                    await WebhookService.send_webhook(
                        webhook_url=analysis.webhook_url,
                        event="analysis.completed",
                        analysis_id=analysis_id,
                        data={
                            "status": "completed",
                            "classification": final_classification,
                            "confidence": confidence
                        }
                    )
                except Exception as e:
                    logger.error(f"Erro ao enviar webhook: {e}")
        
        except Exception as e:
            logger.error(f"Erro ao processar análise {analysis_id}: {e}", exc_info=True)
            
            # Marcar como falha
            try:
                # Buscar análise novamente para garantir que está na sessão atual
                result = await db.execute(
                    select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
                )
                analysis = result.scalar_one_or_none()
                
                if analysis:
                    analysis.status = AnalysisStatus.failed
                    analysis.error_message = str(e)
                    await db.commit()
                    await db.refresh(analysis)
                
                # Enviar webhook de falha
                if analysis.webhook_url:
                    try:
                        await WebhookService.send_webhook(
                            webhook_url=analysis.webhook_url,
                            event="analysis.failed",
                            analysis_id=analysis_id,
                            data={"status": "failed", "error": str(e)}
                        )
                    except:
                        pass
            except:
                pass
    
    @staticmethod
    async def _update_step(
        analysis_id: str,
        step_name: StepName,
        status: StepStatus,
        progress: int,
        db: AsyncSession
    ):
        """Atualiza status de um step."""
        analysis_uuid = uuid.UUID(analysis_id)
        result = await db.execute(
            select(AnalysisStep)
            .where(AnalysisStep.analysis_id == analysis_uuid)
            .where(AnalysisStep.step_name == step_name)
        )
        step = result.scalar_one_or_none()
        
        if step:
            step.status = status
            step.progress = progress
            if status == StepStatus.running and not step.started_at:
                step.started_at = datetime.utcnow()
            if status == StepStatus.completed:
                step.completed_at = datetime.utcnow()
            await db.commit()
    
    @staticmethod
    def _create_report(
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
        """Cria relatório forense completo."""
        return {
            "file": Path(video_path).name,
            "file_path": video_path,
            "codec": metadata.get("codec_name"),
            "encoder": metadata.get("encoder"),
            "major_brand": metadata.get("major_brand"),
            "compatible_brands": metadata.get("compatible_brands", []),
            "duration": metadata.get("duration"),
            "bit_rate": metadata.get("bit_rate"),
            "frame_rate": metadata.get("r_frame_rate"),
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "gop_estimate": fingerprint.get("gop_analysis", {}).get("gop_size"),
            "qp_pattern": fingerprint.get("qp_analysis", {}).get("pattern"),
            "classification": classification.get("classification"),
            "confidence": classification.get("confidence"),
            "confidence_level": AnalysisProcessor._get_confidence_level(classification.get("confidence", 0.0)),
            "reason": classification.get("reason"),
            "most_likely_model": classification.get("model_probabilities", {}),
            "model_probabilities": classification.get("model_probabilities", {}),
            "prnu_analysis": prnu_analysis,
            "fft_analysis": fft_analysis,
            "metadata_integrity": metadata_integrity,
            "timeline": timeline_analysis.get("timeline", []),
            "hybrid_analysis": timeline_analysis.get("hybrid_analysis", {}),
            "timeline_summary": timeline_analysis.get("summary", {}),
            "tool_signatures": tool_signatures,
            "fingerprint": fingerprint
        }
    
    @staticmethod
    def _convert_to_serializable(obj: Any) -> Any:
        """
        Converte valores numpy e outros tipos não serializáveis para tipos Python nativos.
        
        Converte:
        - numpy.float32, numpy.float64 -> float
        - numpy.int32, numpy.int64 -> int
        - numpy.ndarray -> list
        - Outros tipos numpy -> tipos Python equivalentes
        """
        # Verificar tipos numpy (compatível com NumPy 1.x e 2.x)
        if hasattr(np, 'integer') and isinstance(obj, np.integer):
            return int(obj)
        elif hasattr(np, 'floating') and isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(np, 'bool_') and isinstance(obj, np.bool_):
            return bool(obj)
        # Verificar tipos específicos do NumPy
        elif type(obj).__module__ == 'numpy' and 'float' in str(type(obj)):
            return float(obj)
        elif type(obj).__module__ == 'numpy' and 'int' in str(type(obj)):
            return int(obj)
        elif isinstance(obj, dict):
            return {key: AnalysisProcessor._convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AnalysisProcessor._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # Tentar converter para string se não for serializável
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    @staticmethod
    def _get_confidence_level(confidence: float) -> str:
        """Retorna nível de confiança."""
        if confidence >= 0.8:
            return "alta"
        elif confidence >= 0.6:
            return "média"
        else:
            return "baixa"

