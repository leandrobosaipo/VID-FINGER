"""Script para inicializar banco de dados."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app.config import settings


async def init_db():
    """Cria todas as tabelas no banco de dados."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("Banco de dados inicializado com sucesso!")


if __name__ == "__main__":
    asyncio.run(init_db())

