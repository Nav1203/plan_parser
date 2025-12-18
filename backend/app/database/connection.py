"""MongoDB database connection manager."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

from app.config import get_settings
from app.database.models import DATABASE_NAME

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        settings = get_settings()
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[DATABASE_NAME]
            await self.client.server_info()  # Test connection
            logger.info(f"Connected to MongoDB database: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def is_connected(self) -> bool:
        """Check if database is connected."""
        if not self.client:
            return False
        try:
            await self.client.server_info()
            return True
        except Exception:
            return False


# Global database instance
database = Database()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    if database.db is None:
        raise RuntimeError("Database not initialized")
    return database.db
