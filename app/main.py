from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import logging

from app.core.config import settings
from app.api.router import api_router
from app.db.async_session import startup_async_database, shutdown_async_database
from app.services.async_monitoring import start_database_monitoring, stop_database_monitoring
from app.services.async_metrics import get_metrics_collector
from app.services.async_error_tracking import get_error_tracker, log_alert_handler

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    redirect_slashes=False,  # Prevent automatic trailing slash redirects that cause HTTPS->HTTP issues
)

# Custom OpenAPI schema with explicit security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.PROJECT_DESCRIPTION,
        routes=app.routes,
    )
    
    # Add OAuth2 password bearer scheme
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": f"{settings.API_V1_PREFIX}/auth/token",
                    "scopes": {}
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    try:
        logger.info("Starting up Bitewise API...")
        
        # Initialize async database connections
        await startup_async_database()
        logger.info("Async database initialized successfully")
        
        # Initialize metrics collector
        metrics_collector = get_metrics_collector()
        logger.info("Database metrics collector initialized")
        
        # Initialize error tracker with notification handlers
        error_tracker = get_error_tracker()
        error_tracker.add_notification_handler(log_alert_handler)
        logger.info("Database error tracker initialized with alert handlers")
        
        # Start database monitoring service
        await start_database_monitoring()
        logger.info("Database monitoring service started")
        
        logger.info("Bitewise API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to start up application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown."""
    try:
        logger.info("Shutting down Bitewise API...")
        
        # Stop database monitoring service
        await stop_database_monitoring()
        logger.info("Database monitoring service stopped")
        
        # Clean up async database connections
        await shutdown_async_database()
        logger.info("Async database connections closed")
        
        logger.info("Bitewise API shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Welcome to Bitewise API"} 