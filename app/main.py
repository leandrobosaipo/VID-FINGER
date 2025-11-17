"""Aplicação FastAPI principal."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_router

# Configurar logging humanizado
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def format_log_message(emoji: str, message: str) -> str:
    """Formata mensagem de log com emoji."""
    return f"{emoji} {message}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de ciclo de vida da aplicação."""
    # Startup
    logger.info(format_log_message("🚀", "Iniciando aplicação VID-FINGER..."))
    logger.info(format_log_message("📋", f"Versão: {settings.APP_VERSION}"))
    logger.info(format_log_message("🔧", f"Modo DEBUG: {'Ativado' if settings.DEBUG else 'Desativado'}"))
    
    # Verificar configurações importantes (sem senhas)
    if settings.UPLOAD_TO_CDN:
        logger.info(format_log_message("☁️", "Upload para CDN: Habilitado"))
        if settings.DO_SPACES_BUCKET:
            logger.info(format_log_message("📦", f"Bucket CDN: {settings.DO_SPACES_BUCKET}"))
        else:
            logger.warning(format_log_message("⚠️", "Bucket CDN não configurado"))
    else:
        logger.info(format_log_message("💾", "Upload para CDN: Desabilitado (armazenamento local)"))
    
    # Verificar banco de dados
    db_type = "PostgreSQL" if "postgresql" in settings.DATABASE_URL else "SQLite"
    logger.info(format_log_message("🗄️", f"Banco de dados: {db_type}"))
    
    # Verificar Redis
    if settings.REDIS_URL:
        logger.info(format_log_message("🔴", f"Redis: {settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else 'Configurado'}"))
    
    logger.info(format_log_message("✅", "Aplicação inicializada com sucesso"))
    
    yield
    
    # Shutdown
    logger.info(format_log_message("🛑", "Encerrando aplicação..."))
    logger.info(format_log_message("👋", "Aplicação encerrada"))

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Sistema Forense de Detecção de Vídeos Gerados por IA
    
    API RESTful completa para análise forense de vídeos, com suporte a:
    
    - ✅ Upload chunked de vídeos grandes (até 10GB)
    - ✅ Upload automático para DigitalOcean Spaces CDN
    - ✅ Análise multi-camada (PRNU, FFT, Metadados)
    - ✅ Webhooks para notificações em tempo real
    - ✅ Relatórios periciais completos em JSON
    - ✅ Geração de vídeos limpos (sem fingerprints de IA)
    
    ### Funcionalidades Principais
    
    1. **Upload Chunked**: Suporte a uploads grandes divididos em chunks de 5MB
    2. **CDN Integration**: Upload automático para DigitalOcean Spaces com expiração de 7 dias
    3. **Análise Forense**: Múltiplas técnicas de detecção de IA
    4. **Webhooks**: Notificações em tempo real via HTTP POST
    5. **Swagger/OpenAPI**: Documentação interativa completa
    
    ### Configuração
    
    Configure as variáveis de ambiente no arquivo `.env`:
    - `UPLOAD_TO_CDN=True` para habilitar upload automático para Spaces
    - `DO_SPACES_*` para credenciais do DigitalOcean Spaces
    - `WEBHOOK_URL` pode ser passado em cada requisição de upload
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "VID-FINGER API Support",
        "url": "https://github.com/your-repo/vid-finger"
    },
    license_info={
        "name": "MIT",
    },
    tags_metadata=[
        {
            "name": "upload",
            "description": "Endpoints para upload chunked de vídeos. Suporta arquivos grandes divididos em chunks.",
        },
        {
            "name": "analysis",
            "description": "Endpoints para consultar status e resultados de análises forenses.",
        },
        {
            "name": "files",
            "description": "Endpoints para download de arquivos gerados (original, relatório, vídeo limpo).",
        },
        {
            "name": "reports",
            "description": "Endpoints para download de relatórios periciais em JSON.",
        },
    ]
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.get("/health/dependencies")
async def health_dependencies():
    """Health check de dependências."""
    from app.api.v1.endpoints.debug import health_dependencies as check_deps
    return await check_deps()



