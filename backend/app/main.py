"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.endpoints import auth, captures
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# Import models to register them with Base before creating tables
from app.models.capture import Capture, Draft  # noqa: F401
from app.models.user import Session as UserSession  # noqa: F401
from app.models.user import User  # noqa: F401

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize rate limiter with storage backend
# Use Redis if available, otherwise fall back to in-memory storage
storage_uri = settings.REDIS_URL if settings.REDIS_URL else "memory://"
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=storage_uri,
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent productivity tool for capturing tasks and events",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])

app.include_router(
    captures.router, prefix=f"{settings.API_V1_PREFIX}/captures", tags=["captures"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
    }


@app.get("/health")
@limiter.exempt
async def health_check():
    """Health check endpoint (exempt from rate limiting)."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
