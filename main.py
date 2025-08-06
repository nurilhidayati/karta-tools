from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from api.database.connection import engine, Base
from api.routers import country
from api.routers import geospatial
from api.routers import boundary
from api.routers import chatbot
from api.routers import campaign
from config import Settings

# Initialize settings
settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")

app = FastAPI(
    title="Karta Tools API",
    description="""
    """,
    version="1.0.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": f"http://{settings.API_HOST}:{settings.API_PORT}", "description": "Local development server"},
    ]
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(country.router, prefix="/api/v1")
app.include_router(geospatial.router, prefix="/api/v1")
app.include_router(boundary.router, prefix="/api/v1")
app.include_router(chatbot.router, prefix="/api/v1")
app.include_router(campaign.router, prefix="/api/v1")

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Welcome endpoint with API information"""
    return {
        "message": "🌍 Welcome to Karta Tools API",
        "version": "1.0.0",
        "description": "Geospatial Analysis and Management Platform",
        "docs_url": "/docs",
        "health_check": "/api/v1/geospatial/health",
        "features": [
            "Geohash Grid Generation",
            "POI Density Analysis", 
            "Road Network Analysis",
            "Complete Workflow Automation",
            "PostgreSQL Data Storage"
        ]
    }

@app.get("/health", tags=["health"])
async def health_check():
    """General API health check"""
    try:
        # Test database connection by importing and checking
        from api.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # Will be dynamic in real implementation
            "services": {
                "api": "online",
                "database": "connected",
                "geospatial": "available"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "services": {
                    "api": "online",
                    "database": "disconnected",
                    "geospatial": "unavailable"
                }
            }
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please check the logs for details.",
            "type": type(exc).__name__
        }
    )

# Application events
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 Karta Tools API starting up...")
    logger.info(f"📊 Database: {settings.DATABASE_NAME}")
    logger.info(f"🌐 Server: http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"📚 Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    
    # Database initialization removed per user request

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 Karta Tools API shutting down...")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 