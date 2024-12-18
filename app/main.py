from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.core.config import settings
from app.database import Base, engine
from app.core.cache import setup_cache
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from app.services.metrics import MetricsService, MetricsMiddleware


metrics_service = MetricsService()
limiter = Limiter(key_func=get_remote_address)
# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize cache on startup"""
    await setup_cache()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(MetricsMiddleware, metrics_service=metrics_service)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin)
                       for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Root endpoint that returns basic API information."""
    return {
        "message": "Welcome to the Blog Platform API",
        "version": "1.0.0",
        "documentation": f"/docs",
        "openapi": f"{settings.API_V1_STR}/openapi.json"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint, includes detailed metrics"""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "metrics": metrics_service.get_metrics()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
