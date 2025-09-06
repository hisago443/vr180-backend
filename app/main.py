"""
Main FastAPI application for VR 180 Video Processing Platform.
"""
import os
import logging
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.middleware.auth_middleware import AuthMiddleware, OptionalAuthMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware, EndpointRateLimitMiddleware
from app.middleware.cors_middleware import setup_cors_middleware
from app.routes import auth_router, videos_router, system_router, internal_router
from app.models.system import ErrorResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting VR 180 Video Processing Platform")
    
    try:
        # Initialize services
        settings = get_settings()
        logger.info(f"Application starting in {settings.environment} mode")
        
        # Log configuration (without sensitive data)
        logger.info(
            "Configuration loaded",
            app_name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            firebase_project_id=settings.firebase_project_id,
            gcs_bucket=settings.google_cloud_storage_bucket
        )
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down VR 180 Video Processing Platform")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="VR 180 Video Processing Platform - Convert 2D videos to immersive VR 180° format using AI-powered depth estimation",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
        lifespan=lifespan
    )
    
    # Setup CORS middleware
    setup_cors_middleware(app)
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute
    )
    
    # Add endpoint-specific rate limiting
    app.add_middleware(EndpointRateLimitMiddleware)
    
    # Add authentication middleware (exclude certain paths)
    excluded_auth_paths = [
        "/",
        "/health",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/auth/register",
        "/auth/login",
        "/system/health",
        "/system/status"
    ]
    app.add_middleware(
        AuthMiddleware,
        excluded_paths=excluded_auth_paths
    )
    
    # Add optional authentication middleware for internal routes
    app.add_middleware(OptionalAuthMiddleware)
    
    # Include routers
    app.include_router(auth_router)
    app.include_router(videos_router)
    app.include_router(system_router)
    app.include_router(internal_router)
    
    # Add root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "VR 180 Video Processing Platform API",
            "version": settings.app_version,
            "environment": settings.environment,
            "docs_url": "/docs" if settings.environment == "development" else None,
            "health_check": "/health"
        }
    
    # Add health check endpoint (without auth)
    @app.get("/health", tags=["Health"])
    async def health():
        """Simple health check endpoint."""
        return {
            "status": "healthy",
            "service": "vr180-video-processing",
            "version": settings.app_version
        }
    
    # Global exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP Error",
                message=exc.detail,
                timestamp=exc.timestamp if hasattr(exc, 'timestamp') else None
            ).dict()
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        logger.warning(
            "Starlette HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP Error",
                message=exc.detail
            ).dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="Validation Error",
                message="Request validation failed",
                details={"errors": exc.errors()}
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method,
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Internal Server Error",
                message="An unexpected error occurred"
            ).dict()
        )
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,                # disable reload in production
        log_level="info",            # or settings.log_level.lower()
        access_log=True
    )


