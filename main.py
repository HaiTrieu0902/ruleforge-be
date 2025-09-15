from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from app.core.config import settings
from app.api import documents, health

app = FastAPI(
    title="RuleForge Backend",
    description="Contract Summarizer & Rule Generator API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )