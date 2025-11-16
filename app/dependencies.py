"""Dependências FastAPI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

# Dependência de banco de dados
def get_database_session() -> AsyncSession:
    """Retorna sessão do banco de dados."""
    return Depends(get_db)

