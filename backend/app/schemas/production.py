from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductionDates(BaseModel):
    """Production milestone dates."""

    fabric: Optional[str] = None
    cutting: Optional[str] = None
    sewing: Optional[str] = None
    shipping: Optional[str] = None


class ProductionItemBase(BaseModel):
    """Base schema for production items."""

    order_number: str
    style: str
    fabric: Optional[str] = None
    color: Optional[str] = None
    quantity: int
    status: str = "pending"
    dates: Optional[ProductionDates] = None


class ProductionItemCreate(ProductionItemBase):
    """Schema for creating a production item."""

    pass


class ProductionItem(ProductionItemBase):
    """Schema for production item from database."""

    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class ProductionItemResponse(ProductionItemBase):
    """Schema for production item API response."""

    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProductionItemsListResponse(BaseModel):
    """Schema for paginated list of production items."""

    items: list[ProductionItemResponse]
    total: int
    skip: int
    limit: int
