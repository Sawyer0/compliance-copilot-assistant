"""API routes for compliance document ingestion."""

from .health import router as health_router
from .ingestion import router as ingestion_router
from .sources import router as sources_router

__all__ = ["health_router", "ingestion_router", "sources_router"] 