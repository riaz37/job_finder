"""
FastAPI main application entry point for AI Job Agent
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.api.v1.api import api_router
from app.db.database import init_database, close_database
from app.services.redis_service import redis_service
from app.services.ai_service import ai_service
from app.services.cloudinary_service import cloudinary_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        await init_database()
        await redis_service.connect()

        # Initialize AI service if API key is available
        if settings.GEMINI_API_KEY:
            await ai_service.initialize()
            print("AI service initialized")
        else:
            print("Warning: GEMINI_API_KEY not set, AI features will use fallback methods")

        # Initialize Cloudinary service
        await cloudinary_service.initialize()

        print("Application startup completed")
    except Exception as e:
        print(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        await close_database()
        await redis_service.disconnect()
        print("Application shutdown completed")
    except Exception as e:
        print(f"Shutdown error: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI Job Agent - Automated job search and application system",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "AI Job Agent API", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        from app.db.database import db_service
        db_healthy = await db_service.health_check()
        
        # Check Redis connection
        redis_healthy = redis_service.redis_client is not None
        
        return {
            "status": "healthy" if db_healthy and redis_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "redis": "connected" if redis_healthy else "disconnected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }