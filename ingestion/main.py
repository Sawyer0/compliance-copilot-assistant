"""Main FastAPI application for compliance document ingestion."""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import inngest.fast_api
from ingestion_functions.client import inngest_client
from core.logging import setup_logging
from api.health import router as health_router
from api.ingestion import router as ingestion_router  
from api.sources import router as sources_router
from api.documents import router as documents_router
from workflows.compliance_workflow import (
    trigger_compliance_ingestion,
    fetch_document,
    extract_content,
    process_content,
    save_document
)
from workflows.scheduled_workflow import (
    daily_compliance_check,
    weekly_maintenance
)

# Set environment variables for Inngest dev mode
os.environ['INNGEST_DEV'] = '1'
os.environ['INNGEST_BASE_URL'] = 'http://localhost:8288'
os.environ['INNGEST_SIGNING_KEY'] = 'signkey-dev-0000000000000000000000000000000000000000000000000000000000000000'

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Compliance Document Ingestion API",
    description="Enterprise-grade compliance document ingestion using Inngest workflows",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(sources_router)
app.include_router(documents_router)

# Serve all Inngest workflow functions
inngest.fast_api.serve(
    app=app,
    client=inngest_client,
    functions=[
        # Main workflow functions
        trigger_compliance_ingestion,
        fetch_document,
        extract_content,
        process_content,
        save_document,
        # Scheduled functions
        daily_compliance_check,
        weekly_maintenance,
    ],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
