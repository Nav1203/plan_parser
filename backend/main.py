from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:pass1234@localhost:27017/production?authSource=admin")
client: Optional[AsyncIOMotorClient] = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global client, db
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.production
        await client.server_info()  # Test connection
        logger.info("Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

    yield

    # Shutdown
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")

# Create FastAPI app
app = FastAPI(
    title="Production Planning Parser API",
    description="API for parsing and managing production planning data",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Production Planning Parser API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        if client:
            await client.server_info()
            mongo_status = "connected"
        else:
            mongo_status = "disconnected"
    except:
        mongo_status = "error"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mongodb": mongo_status
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and parse production planning sheet
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an Excel file (.xlsx or .xls)"
        )

    # TODO: Implement file parsing logic
    # For now, return a placeholder response
    return JSONResponse(
        status_code=200,
        content={
            "message": "File received successfully",
            "filename": file.filename,
            "size": file.size,
            "status": "pending_processing"
        }
    )

@app.get("/api/production-items")
async def get_production_items(
    skip: int = 0,
    limit: int = 100,
    style: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Get production line items with optional filtering
    """
    # TODO: Implement database query logic
    # For now, return sample data
    sample_items = [
        {
            "id": "1",
            "order_number": "PO-001",
            "style": "STYLE-ABC",
            "fabric": "100% Cotton",
            "color": "Navy Blue",
            "quantity": 1000,
            "status": "in_production",
            "dates": {
                "fabric": "2024-01-15",
                "cutting": "2024-01-20",
                "sewing": "2024-01-25",
                "shipping": "2024-02-01"
            }
        },
        {
            "id": "2",
            "order_number": "PO-002",
            "style": "STYLE-XYZ",
            "fabric": "Polyester Blend",
            "color": "Red",
            "quantity": 500,
            "status": "pending",
            "dates": {
                "fabric": "2024-01-18",
                "cutting": "2024-01-23",
                "sewing": "2024-01-28",
                "shipping": "2024-02-05"
            }
        }
    ]

    return {
        "items": sample_items,
        "total": len(sample_items),
        "skip": skip,
        "limit": limit
    }

@app.get("/api/production-items/{item_id}")
async def get_production_item(item_id: str):
    """
    Get a specific production item by ID
    """
    # TODO: Implement database query logic
    return {
        "id": item_id,
        "order_number": "PO-001",
        "style": "STYLE-ABC",
        "fabric": "100% Cotton",
        "color": "Navy Blue",
        "quantity": 1000,
        "status": "in_production",
        "dates": {
            "fabric": "2024-01-15",
            "cutting": "2024-01-20",
            "sewing": "2024-01-25",
            "shipping": "2024-02-01"
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

@app.delete("/api/production-items/{item_id}")
async def delete_production_item(item_id: str):
    """
    Delete a production item
    """
    # TODO: Implement database deletion logic
    return {
        "message": f"Item {item_id} deleted successfully",
        "id": item_id
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)