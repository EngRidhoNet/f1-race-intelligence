"""
F1 Race Intelligence Backend - FastAPI Application
"""
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.core.logging import setup_logging, get_logger

import app.routers.health as health
# import app.routers.races as races
import app.routers.telemetry as telemetry
import app.routers.chat as chat
# import app.routers.realtime as realtime


# Setup logging
setup_logging()
logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"LLM Model: {settings.llm_model_name}")
    logger.info(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    F1 Race Intelligence Backend API
    
    Features:
    - Race data and telemetry from FastF1
    - Real-time race replay via WebSocket
    - AI-powered race analysis chatbot using open-source LLMs (Llama/Mistral/Qwen)
    
    The chatbot uses actual race data to provide insights about driver performance,
    strategy, and race events.
    """,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
# app.include_router(races.router)
app.include_router(telemetry.router)
app.include_router(chat.router)
# app.include_router(realtime.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )