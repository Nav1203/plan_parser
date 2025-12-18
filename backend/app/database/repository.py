"""Repository for production items database operations."""

from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database.models import (
    ProductionItemModel,
    ProductionDates,
    ProductionSource,
    COLLECTION_NAME,
)


class ProductionRepository:
    """Repository for production items CRUD operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[COLLECTION_NAME]

    async def create(self, item: ProductionItemModel) -> ProductionItemModel:
        """Insert a new production item into the database."""
        doc = item.to_document()
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()

        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)

        return ProductionItemModel.from_document(doc)

    async def create_many(self, items: list[ProductionItemModel]) -> list[ProductionItemModel]:
        """Insert multiple production items into the database."""
        if not items:
            return []

        docs = []
        for item in items:
            doc = item.to_document()
            doc["created_at"] = datetime.utcnow()
            doc["updated_at"] = datetime.utcnow()
            docs.append(doc)

        result = await self.collection.insert_many(docs)

        # Update docs with inserted IDs
        for doc, inserted_id in zip(docs, result.inserted_ids):
            doc["_id"] = str(inserted_id)

        return [ProductionItemModel.from_document(doc) for doc in docs]

    async def get_by_id(self, item_id: str) -> Optional[ProductionItemModel]:
        """Get a production item by its ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(item_id)})
            if doc:
                return ProductionItemModel.from_document(doc)
        except Exception:
            pass
        return None

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        style: Optional[str] = None,
        status: Optional[str] = None,
        order_number: Optional[str] = None,
    ) -> tuple[list[ProductionItemModel], int]:
        """Get all production items with optional filtering and pagination."""
        query = {}

        if style:
            query["style"] = {"$regex": style, "$options": "i"}
        if status:
            query["status"] = status
        if order_number:
            query["order_number"] = {"$regex": order_number, "$options": "i"}

        total = await self.collection.count_documents(query)

        cursor = self.collection.find(query).skip(skip).limit(limit)
        items = []

        async for doc in cursor:
            items.append(ProductionItemModel.from_document(doc))

        return items, total

    async def update(self, item_id: str, update_data: dict) -> Optional[ProductionItemModel]:
        """Update a production item by its ID."""
        try:
            update_data["updated_at"] = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(item_id)},
                {"$set": update_data},
                return_document=True,
            )

            if result:
                return ProductionItemModel.from_document(result)
        except Exception:
            pass
        return None

    async def delete(self, item_id: str) -> bool:
        """Delete a production item by its ID."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(item_id)})
            return result.deleted_count > 0
        except Exception:
            return False

    async def delete_many(self, query: dict) -> int:
        """Delete multiple production items matching a query."""
        result = await self.collection.delete_many(query)
        return result.deleted_count

    async def find_by_order_number(self, order_number: str) -> Optional[ProductionItemModel]:
        """Find a production item by order number."""
        doc = await self.collection.find_one({"order_number": order_number})
        if doc:
            return ProductionItemModel.from_document(doc)
        return None

    async def find_by_source(self, file: str, sheet: str) -> list[ProductionItemModel]:
        """Find all production items from a specific source file and sheet."""
        cursor = self.collection.find({
            "source.file": file,
            "source.sheet": sheet,
        })

        items = []
        async for doc in cursor:
            items.append(ProductionItemModel.from_document(doc))

        return items

    async def upsert_by_order_number(self, item: ProductionItemModel) -> ProductionItemModel:
        """Insert or update a production item based on order_number."""
        doc = item.to_document()
        now = datetime.utcnow()
        doc["updated_at"] = now

        result = await self.collection.find_one_and_update(
            {"order_number": item.order_number},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )

        return ProductionItemModel.from_document(result)
