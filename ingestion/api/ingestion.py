"""Ingestion trigger and management endpoints using Inngest workflows."""

import datetime
import logging
from typing import Dict, Any

import inngest
from fastapi import APIRouter, HTTPException

from ingestion_functions.client import inngest_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/trigger-ingestion")
async def trigger_compliance_ingestion() -> Dict[str, Any]:
    """Trigger compliance document ingestion using Inngest workflow."""
    try:
        # Send event to Inngest workflow orchestrator
        event = inngest.Event(
            name="compliance/ingestion.start",
            data={
                "triggered_by": "api",
                "triggered_at": datetime.datetime.now().isoformat()
            }
        )
        
        result = await inngest_client.send(event)
        logger.info("Triggered Inngest compliance workflow")
        
        return {
            "status": "success",
            "message": "Compliance document ingestion workflow triggered",
            "workflow_triggered": True,
            "inngest_event_id": str(result) if result else None,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering Inngest workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger compliance ingestion workflow: {str(e)}"
        )


@router.post("/trigger-source/{source_name}")
async def trigger_single_source(source_name: str) -> Dict[str, Any]:
    """Trigger processing for a single compliance source."""
    try:
        # This could be extended to load specific source config and trigger just that source
        event = inngest.Event(
            name="compliance/source.process",  # Could create a more specific event
            data={
                "source_name": source_name,
                "triggered_by": "api",
                "triggered_at": datetime.datetime.now().isoformat()
            }
        )
        
        result = await inngest_client.send(event)
        logger.info(f"Triggered processing for source: {source_name}")
        
        return {
            "status": "success",
            "message": f"Processing triggered for source: {source_name}",
            "source_name": source_name,
            "inngest_event_id": str(result) if result else None,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering source processing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger processing for {source_name}: {str(e)}"
        ) 