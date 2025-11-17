"""Configuração do banco de dados."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def validate_database_url(url: str, is_async: bool = True) -> None:
    """
    Valida formato de DATABASE_URL.
    
    Args:
        url: URL do banco de dados
        is_async: Se True, valida que URL usa driver assíncrono
        
    Raises:
        ValueError: Se formato estiver incorreto
    """
    if not url:
        raise ValueError("DATABASE_URL não pode estar vazio")
    
    if is_async:
        # Verificar se está usando postgresql:// sem +asyncpg
        if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            error_msg = (
                "\n" + "="*70 + "\n"
                "❌ ERRO: DATABASE_URL está usando driver síncrono (postgresql://)\n"
                "\n"
                "💡 CORREÇÃO NECESSÁRIA:\n"
                "   No EasyPanel, vá para 'Environment Variables' e altere:\n"
                "\n"
                "   DE:   postgresql://postgres:senha@host:5432/database\n"
                "   PARA: postgresql+asyncpg://postgres:senha@host:5432/database\n"
                "\n"
                "   (Adicione '+asyncpg' após 'postgresql')\n"
                "\n"
                "📝 Exemplo completo:\n"
                f"   DATABASE_URL=postgresql+asyncpg://postgres:AA393A2FC576136C7FE79B523924A@criadordigital_postgres:5432/criadordigital?sslmode=disable\n"
                "\n"
                "="*70 + "\n"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Verificar se está usando asyncpg
        if not url.startswith("postgresql+asyncpg://"):
            logger.warning(
                f"⚠️  DATABASE_URL não está usando formato assíncrono esperado: "
                f"{url[:50]}..."
            )


# Validar DATABASE_URL antes de criar engines
try:
    validate_database_url(settings.DATABASE_URL, is_async=True)
    logger.info("✅ DATABASE_URL validado: usando driver assíncrono (asyncpg)")
except ValueError as e:
    # Re-raise para parar a aplicação com erro claro
    raise

# Async engine para FastAPI
try:
    logger.info("🔄 Criando conexão assíncrona com banco de dados...")
    async_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    logger.info("✅ Conexão assíncrona criada com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao criar conexão assíncrona: {e}")
    raise

# Sync engine para Alembic e Celery
try:
    logger.info("🔄 Criando conexão síncrona com banco de dados (para Alembic)...")
    sync_engine = create_engine(
        settings.DATABASE_URL_SYNC,
        echo=settings.DEBUG,
        future=True,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL_SYNC else {}
    )
    logger.info("✅ Conexão síncrona criada com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao criar conexão síncrona: {e}")
    raise

# Session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base para modelos
Base = declarative_base()


async def get_db():
    """Dependency para obter sessão do banco de dados."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

