from fastapi import APIRouter

from app.api.routes import health, production

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(production.router, prefix="/production-items", tags=["production"])
