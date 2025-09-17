from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os

from app.core.config import settings
from app.api import documents, health, variables

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    # Create uploads directory if it doesn't exist
    os.makedirs(settings.upload_folder, exist_ok=True)
    print(f"✅ Upload folder created: {settings.upload_folder}")
    
    # Initialize database and create tables
    from app.models.database import init_db, engine, Base
    if init_db():
        print("✅ Database initialized successfully")
        
        # Create all tables including the new variables table
        Base.metadata.create_all(bind=engine)
        print("✅ All database tables created/updated successfully")
    else:
        print("❌ Database initialization failed - check PostgreSQL connection")
        # Don't exit, let the app start anyway for debugging
    
    # Initialize MinIO storage
    from app.services.minio_storage import minio_storage
    if await minio_storage.initialize_bucket():
        print("✅ MinIO storage initialized successfully")
    else:
        print("❌ MinIO storage initialization failed - check MinIO connection")
    
    # Auto-sync variables to Qdrant
    from app.services.qdrant_service import qdrant_service
    sync_result = await qdrant_service.sync_variables_from_database()
    if sync_result["success"]:
        print(f"✅ Variables sync completed: {sync_result['message']}")
    else:
        print(f"⚠️ Variables sync failed: {sync_result['message']}")
    
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
app.include_router(variables.router, prefix="/api/v1", tags=["variables"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )