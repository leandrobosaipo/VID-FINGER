"""Router principal da API v1."""
from fastapi import APIRouter
from app.api.v1.endpoints import upload, analysis, status, reports, files, debug

api_router = APIRouter()

# Incluir endpoints
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(status.router, prefix="/status", tags=["status"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(debug.router, prefix="", tags=["debug"])

