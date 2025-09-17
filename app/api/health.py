from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "message": "RuleForge Backend is running",
            "version": "1.0.0"
        }
    )
    
