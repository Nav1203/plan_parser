from fastapi import APIRouter
from datetime import datetime

from app.database import database
from app.config import get_settings

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    settings = get_settings()
    return {
        "message": settings.app_name,
        "status": "running",
        "version": settings.app_version,
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    is_connected = await database.is_connected()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mongodb": "connected" if is_connected else "disconnected",
    }
