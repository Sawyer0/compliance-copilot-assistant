"""Standalone FastAPI application with Inngest integration."""

import logging
import os
import sys
from pathlib import Path

# Add current directory to Python path to enable absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import inngest
import inngest.fast_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Inngest client
inngest_client = inngest.Inngest(
    app_id="compliance-ingestion",
    logger=logging.getLogger("inngest"),
)

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

# Simple Inngest function
@inngest_client.create_function(
    fn_id="hello_world",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def hello_world(ctx: inngest.Context) -> dict:
    """Simple hello world function."""
    ctx.logger.info(f"Hello from Inngest! Event: {ctx.event.name}")
    return {"message": "Hello from Inngest!", "event_data": ctx.event.data}

# Trigger test event endpoint
@app.post("/trigger-test")
async def trigger_test():
    """Trigger a test Inngest function."""
    await inngest_client.send(
        inngest.Event(
            name="test/hello",
            data={"message": "Hello from API!"}
        )
    )
    return {"status": "triggered", "event": "test/hello"}

# Serve Inngest functions
inngest.fast_api.serve(
    app=app,
    client=inngest_client,
    functions=[hello_world],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 