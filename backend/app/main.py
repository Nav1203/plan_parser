from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.database import database
from app.api.routes import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    try:
        await database.connect()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")

    yield

    # Shutdown
    await database.disconnect()


def create_app() -> FastAPI:
    """Application factory to create FastAPI app instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="API for parsing and managing production planning data",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router)
    app.include_router(api_router, prefix="/api")

    return app


# Create app instance
app = create_app()
