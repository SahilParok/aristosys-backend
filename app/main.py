"""
Aristosys API
AI-Powered Recruitment Screening Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import screening_router, clients_router, jobs_router


# Initialize settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(screening_router)
app.include_router(clients_router)
app.include_router(jobs_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Aristosys API",
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.api_version,
        "environment": settings.environment
    }
