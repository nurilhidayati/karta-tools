#!/usr/bin/env python3
"""
Script to run the Karta Tools FastAPI server
"""

import uvicorn
from config import settings

if __name__ == "__main__":
    print("🚀 Starting Karta Tools FastAPI Server...")
    print(f"📊 Database: {settings.DATABASE_NAME}")
    print(f"🌐 Server: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"📚 Swagger UI: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print("-" * 50)
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 