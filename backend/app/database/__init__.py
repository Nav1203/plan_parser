# Database module
from app.database.connection import Database, database, get_database
from app.database.models import (
    ProductionItemModel,
    ProductionDates,
    ProductionSource,
    ExtractionMetadataModel,
    DATABASE_NAME,
    COLLECTION_NAME,
    EXTRACTION_METADATA_COLLECTION,
)
from app.database.repository import ProductionRepository

__all__ = [
    # Connection
    "Database",
    "database",
    "get_database",
    # Models
    "ProductionItemModel",
    "ProductionDates",
    "ProductionSource",
    "ExtractionMetadataModel",
    "DATABASE_NAME",
    "COLLECTION_NAME",
    "EXTRACTION_METADATA_COLLECTION",
    # Repository
    "ProductionRepository",
]
