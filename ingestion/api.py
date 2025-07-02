"""FastAPI application with Inngest integration."""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

import inngest.fast_api
from ingestion_functions import inngest_client, inngest_functions
from core.config import get_settings
from core.logging import setup_logging

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Compliance Ingestion API",
    description="Enterprise compliance document ingestion engine",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "compliance-ingestion"}

# Trigger ingestion job endpoint
@app.post("/trigger-ingestion")
async def trigger_ingestion(source_ids: list[str] = None):
    """Manually trigger an ingestion job."""
    from uuid import uuid4
    
    if not source_ids:
        from core.registry import SourceRegistry
        registry = SourceRegistry()
        sources = registry.list_sources(active_only=True)
        source_ids = [str(s.config.source_id) for s in sources]
    
    job_id = str(uuid4())
    
    # Send event to Inngest
    await inngest_client.send(
        inngest.Event(
            name="ingestion/job.triggered",
            data={
                "jobId": job_id,
                "jobType": "manual",
                "sourceIds": source_ids,
                "priority": 5,
            }
        )
    )
    
    return {"jobId": job_id, "status": "triggered", "sourceCount": len(source_ids)}

# Serve Inngest functions
inngest.fast_api.serve(
    app=app,
    client=inngest_client,
    functions=inngest_functions,
)

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    ) 