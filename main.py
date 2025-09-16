from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os

from app.core.config import settings
from app.api import documents, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.upload_folder, exist_ok=True)
    print(f"✅ Upload folder created: {settings.upload_folder}")
    
    # Initialize database
    from app.models.database import init_db
    if init_db():
        print("✅ Database initialized successfully")
    else:
        print("❌ Database initialization failed - check PostgreSQL connection")
        # Don't exit, let the app start anyway for debugging
    
    # Initialize MinIO storage
    from app.services.minio_storage import minio_storage
    if await minio_storage.initialize_bucket():
        print("✅ MinIO storage initialized successfully")
    else:
        print("❌ MinIO storage initialization failed - check MinIO connection")
    
    yield
    # Shutdown
    minio_storage.close()
    # Note: ContractSummarizer cleanup is handled per-instance

app = FastAPI(
    title="RuleForge Backend",
    description="Contract Summarizer & Rule Generator API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )