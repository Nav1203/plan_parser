from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.schemas import ProductionItemResponse, ProductionItemsListResponse
from app.services import ProductionService
from app.services.data_parser.core import DataParser

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and parse production planning sheet."""
    # Validate file type
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)",
        )

    data_parser = DataParser()
    items = await data_parser.parse_data_from_excel(file)

    return JSONResponse(
        status_code=200,
        content={
            "message": "File processed successfully",
            "filename": file.filename,
            "items_created": len(items),
        },
    )


@router.get("", response_model=ProductionItemsListResponse)
async def get_production_items(
    skip: int = 0,
    limit: int = 100,
    style: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get production line items with optional filtering."""
    service = ProductionService(db)
    return await service.get_items(skip=skip, limit=limit, style=style, status=status)


@router.get("/{item_id}", response_model=ProductionItemResponse)
async def get_production_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get a specific production item by ID."""
    service = ProductionService(db)
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/{item_id}")
async def delete_production_item(
    item_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a production item."""
    service = ProductionService(db)
    deleted = await service.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": f"Item {item_id} deleted successfully", "id": item_id}
