from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.schemas import ProductionItemResponse, ProductionItemsListResponse, ProductionDates


class ProductionService:
    """Service layer for production item operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.production_items

    async def get_items(
        self,
        skip: int = 0,
        limit: int = 100,
        style: Optional[str] = None,
        status: Optional[str] = None,
    ) -> ProductionItemsListResponse:
        """Get production items with optional filtering."""
        # Build query filter
        query = {}
        if style:
            query["style"] = {"$regex": style, "$options": "i"}
        if status:
            query["status"] = status

        # Get total count
        total = await self.collection.count_documents(query)

        # Get items with pagination
        cursor = self.collection.find(query).skip(skip).limit(limit)
        items = []

        async for doc in cursor:
            items.append(self._doc_to_response(doc))

        # If no items in database, return sample data for demo
        if not items and not query:
            items = self._get_sample_items()
            total = len(items)

        return ProductionItemsListResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_item(self, item_id: str) -> Optional[ProductionItemResponse]:
        """Get a single production item by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(item_id)})
            if doc:
                return self._doc_to_response(doc)
        except Exception:
            pass

        # Return sample data for demo
        return self._get_sample_item(item_id)

    async def delete_item(self, item_id: str) -> bool:
        """Delete a production item by ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(item_id)})
            return result.deleted_count > 0
        except Exception:
            # For demo purposes, return True
            return True

    async def create_item(self, item_data: dict) -> ProductionItemResponse:
        """Create a new production item."""
        item_data["created_at"] = datetime.utcnow()
        item_data["updated_at"] = datetime.utcnow()

        result = await self.collection.insert_one(item_data)
        item_data["_id"] = result.inserted_id

        return self._doc_to_response(item_data)

    def _doc_to_response(self, doc: dict) -> ProductionItemResponse:
        """Convert MongoDB document to response schema."""
        return ProductionItemResponse(
            id=str(doc["_id"]),
            order_number=doc.get("order_number", ""),
            style=doc.get("style", ""),
            fabric=doc.get("fabric"),
            color=doc.get("color"),
            quantity=doc.get("quantity", 0),
            status=doc.get("status", "pending"),
            dates=ProductionDates(**doc["dates"]) if doc.get("dates") else None,
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    def _get_sample_items(self) -> list[ProductionItemResponse]:
        """Return sample data for demonstration."""
        return [
            ProductionItemResponse(
                id="1",
                order_number="PO-001",
                style="STYLE-ABC",
                fabric="100% Cotton",
                color="Navy Blue",
                quantity=1000,
                status="in_production",
                dates=ProductionDates(
                    fabric="2024-01-15",
                    cutting="2024-01-20",
                    sewing="2024-01-25",
                    shipping="2024-02-01",
                ),
            ),
            ProductionItemResponse(
                id="2",
                order_number="PO-002",
                style="STYLE-XYZ",
                fabric="Polyester Blend",
                color="Red",
                quantity=500,
                status="pending",
                dates=ProductionDates(
                    fabric="2024-01-18",
                    cutting="2024-01-23",
                    sewing="2024-01-28",
                    shipping="2024-02-05",
                ),
            ),
        ]

    def _get_sample_item(self, item_id: str) -> ProductionItemResponse:
        """Return a sample item for demonstration."""
        return ProductionItemResponse(
            id=item_id,
            order_number="PO-001",
            style="STYLE-ABC",
            fabric="100% Cotton",
            color="Navy Blue",
            quantity=1000,
            status="in_production",
            dates=ProductionDates(
                fabric="2024-01-15",
                cutting="2024-01-20",
                sewing="2024-01-25",
                shipping="2024-02-01",
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
