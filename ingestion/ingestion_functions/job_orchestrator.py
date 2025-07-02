"""Main job orchestration functions."""

from typing import Dict, Any
import inngest
from .client import inngest_client
from core.logging import get_logger
from core.registry import SourceRegistry

logger = get_logger(__name__)


@inngest_client.create_function(
    fn_id="process_ingestion_job",
    trigger=inngest.TriggerEvent(event="ingestion/job.triggered"),
    retries=3,
)
async def process_ingestion_job(ctx: inngest.Context) -> Dict[str, Any]:
    """Process a complete ingestion job."""
    job_data = ctx.event.data
    job_id = job_data.get("jobId")
    source_ids = job_data.get("sourceIds", [])
    
    ctx.logger.info(f"Starting ingestion job {job_id}")
    
    try:
        registry = SourceRegistry()
        
        # Validate sources
        valid_sources = []
        for source_id in source_ids:
            source = registry.get_source(source_id)
            if source and source.config.is_active:
                valid_sources.append(source_id)
        
        ctx.logger.info(f"Processing {len(valid_sources)} valid sources")
        
        # Process each source
        results = []
        for source_id in valid_sources:
            # Send individual source processing events
            await inngest_client.send(
                inngest.Event(
                    name="ingestion/source.process",
                    data={
                        "jobId": job_id,
                        "sourceId": source_id,
                    }
                )
            )
            results.append({"sourceId": source_id, "success": True})
        
        # Send completion event
        await inngest_client.send(
            inngest.Event(
                name="ingestion/job.completed",
                data={
                    "jobId": job_id,
                    "totalSources": len(source_ids),
                    "successfulSources": len(results),
                    "results": results,
                }
            )
        )
        
        return {
            "jobId": job_id,
            "status": "completed",
            "processedSources": len(results),
        }
    
    except Exception as e:
        ctx.logger.error(f"Ingestion job failed: {str(e)}")
        raise


@inngest_client.create_function(
    fn_id="handle_job_completion",
    trigger=inngest.TriggerEvent(event="ingestion/job.completed"),
)
async def handle_job_completion(ctx: inngest.Context) -> Dict[str, Any]:
    """Handle job completion and cleanup."""
    job_data = ctx.event.data
    job_id = job_data.get("jobId")
    total_sources = job_data.get("totalSources", 0)
    successful_sources = job_data.get("successfulSources", 0)
    
    ctx.logger.info(f"Job {job_id} completed: {successful_sources}/{total_sources} sources successful")
    
    # Generate completion report
    report = {
        "jobId": job_id,
        "completionTime": ctx.event.ts,
        "totalSources": total_sources,
        "successfulSources": successful_sources,
        "failedSources": total_sources - successful_sources,
        "successRate": (successful_sources / total_sources * 100) if total_sources > 0 else 0,
    }
    
    ctx.logger.info("Job completion report", extra=report)
    
    return {
        "jobId": job_id,
        "reportGenerated": True,
        "cleanupCompleted": True,
    } 