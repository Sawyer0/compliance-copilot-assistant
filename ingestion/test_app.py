"""Simple test FastAPI application with Inngest integration and error handling."""

import logging
import traceback
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import inngest
import inngest.fast_api

# Set environment variables for Inngest dev mode
os.environ['INNGEST_DEV'] = '1'
os.environ['INNGEST_BASE_URL'] = 'http://localhost:8910'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Inngest client 
inngest_client = inngest.Inngest(
    app_id="test-compliance",
    logger=logger,
)

# Create FastAPI app
app = FastAPI(
    title="Test Compliance API",
    description="Simple test API with Inngest",
    version="1.0.0"
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "test-compliance", "timestamp": "2025-07-02"}

# Simple endpoint that returns test data
@app.get("/test-data")
async def get_test_data():
    """Return sample compliance data."""
    return {
        "documents": [
            {
                "id": 1,
                "title": "NIST AI Risk Management Framework",
                "type": "framework",
                "status": "active",
                "url": "https://www.nist.gov/itl/ai-risk-management-framework"
            },
            {
                "id": 2, 
                "title": "EU AI Act Regulation",
                "type": "regulation",
                "status": "active",
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689"
            }
        ],
        "total": 2,
        "timestamp": "2025-07-02T01:30:00Z"
    }

# Simple Inngest function
@inngest_client.create_function(
    fn_id="process_document",
    trigger=inngest.TriggerEvent(event="document/process"),
)
async def process_document(ctx: inngest.Context) -> dict:
    """Process a document."""
    try:
        event_data = ctx.event.data
        doc_id = event_data.get("document_id", "unknown")
        
        ctx.logger.info(f"Processing document {doc_id}")
        
        # Simulate processing
        result = {
            "document_id": doc_id,
            "status": "processed",
            "processed_at": "2025-07-02T01:30:00Z",
            "content_length": len(str(event_data)),
            "metadata": {
                "processor": "test-processor",
                "version": "1.0.0"
            }
        }
        
        ctx.logger.info(f"Document {doc_id} processed successfully")
        return result
        
    except Exception as e:
        ctx.logger.error(f"Error processing document: {str(e)}")
        raise

# Test trigger endpoint with error handling
@app.post("/trigger-document")
async def trigger_document_processing():
    """Trigger document processing with error handling."""
    try:
        # Create test event
        event = inngest.Event(
            name="document/process",
            data={
                "document_id": "test-doc-123",
                "title": "Test Compliance Document",
                "source": "manual-trigger"
            }
        )
        
        # Send event
        result = await inngest_client.send(event)
        logger.info(f"Event sent successfully: {result}")
        
        return {
            "status": "success",
            "event_sent": "document/process",
            "document_id": "test-doc-123",
            "timestamp": "2025-07-02T01:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error sending event: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to trigger event: {str(e)}"
        )

# List functions endpoint
@app.get("/functions")
async def list_functions():
    """List available Inngest functions."""
    return {
        "functions": [
            {
                "id": "process_document",
                "name": "Process Document",
                "trigger": "document/process",
                "description": "Processes compliance documents"
            }
        ],
        "total": 1,
        "inngest_client_id": inngest_client.app_id
    }

# Simple local processing endpoint (doesn't use Inngest)
@app.post("/process-local")
async def process_document_locally():
    """Process a document locally without Inngest to test data flow."""
    try:
        # Simulate getting document data
        document_data = {
            "document_id": "local-test-456",
            "title": "NIST AI Risk Management Framework - Local Test",
            "source": "local-processing",
            "content": "This document provides guidance on AI risk management..."
        }
        
        # Simulate processing
        processed_result = {
            "document_id": document_data["document_id"],
            "status": "processed",
            "processed_at": "2025-07-02T01:45:00Z",
            "content_length": len(document_data["content"]),
            "word_count": len(document_data["content"].split()),
            "metadata": {
                "processor": "local-processor",
                "version": "1.0.0",
                "processing_time_ms": 150
            },
            "extracted_data": {
                "key_topics": ["AI risk", "management", "framework"],
                "compliance_level": "high",
                "document_type": "guidance"
            }
        }
        
        logger.info(f"Processed document locally: {document_data['document_id']}")
        
        return {
            "status": "success",
            "input": document_data,
            "output": processed_result,
            "processing_method": "local"
        }
        
    except Exception as e:
        logger.error(f"Error in local processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Local processing failed: {str(e)}"
        )

# Serve Inngest functions
inngest.fast_api.serve(
    app=app,
    client=inngest_client,
    functions=[process_document],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "test_app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 