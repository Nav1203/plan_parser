"""Production database models for MongoDB."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


# Database and collection names
DATABASE_NAME = "production"
COLLECTION_NAME = "production_items"
EXTRACTION_METADATA_COLLECTION = "extraction_metadata"


class ProductionDates(BaseModel):
    """Production milestone dates."""

    fabric: Optional[str] = None
    cutting: Optional[str] = None
    sewing: Optional[str] = None
    shipping: Optional[str] = None


class StageData(BaseModel):
    """Data for a single production stage."""
    
    stage_name: str
    fields: Dict[str, Any] = Field(default_factory=dict)  # field_name -> value


class ProductionSource(BaseModel):
    """Source file information."""

    file: str
    sheet: str


class ProductionItemModel(BaseModel):
    """MongoDB document model for production items."""

    id: Optional[str] = Field(default=None, alias="_id")

    order_number: str
    style: str
    fabric: Optional[str] = None
    color: Optional[str] = None

    quantity: int

    status: str = "pending"

    dates: Optional[ProductionDates] = None
    
    stages: Dict[str, StageData] = Field(default_factory=dict)  # stage_name -> StageData

    stage_order: list[str] = Field(
        default_factory=lambda: ["fabric", "cutting", "sewing", "shipping"]
    )

    source: Optional[ProductionSource] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

    def to_document(self) -> dict:
        """Convert model to MongoDB document for insertion."""
        doc = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in doc and doc["_id"] is None:
            del doc["_id"]
        return doc

    @classmethod
    def from_document(cls, doc: dict) -> "ProductionItemModel":
        """Create model instance from MongoDB document."""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)


class ExtractionMetadataModel(BaseModel):
    """MongoDB document model for extraction metadata."""

    id: Optional[str] = Field(default=None, alias="_id")

    file_name: str
    upload_date: datetime

    # Processing info from process_excel_file_with_info
    header_row_count: int
    original_shape: tuple[int, int]
    final_shape: tuple[int, int]
    final_columns: list[str]
    columns_filled: list[str]
    rows_affected: int

    # Column mapping from LLM
    column_mapping: dict

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

    def to_document(self) -> dict:
        """Convert model to MongoDB document for insertion."""
        doc = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in doc and doc["_id"] is None:
            del doc["_id"]
        return doc

    @classmethod
    def from_document(cls, doc: dict) -> "ExtractionMetadataModel":
        """Create model instance from MongoDB document."""
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
