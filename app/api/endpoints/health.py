from fastapi import APIRouter

router = APIRouter()


@router.get("/app-health", summary="Health Check", response_model=dict)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status message
    """
    return {"status": "healthy"} 