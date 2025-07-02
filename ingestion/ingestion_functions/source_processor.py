"""Source-specific processing functions."""

from typing import Dict, Any
import inngest
from .client import inngest_client
from core.logging import get_logger
from services.ingestion_engine import IngestionEngine
from core.registry import SourceRegistry

logger = get_logger(__name__)


@inngest_client.create_function(
    fn_id="process_source",
    trigger=inngest.TriggerEvent(event="ingestion/source.process"),
    retries=2,
)
async def process_source(ctx: inngest.Context) -> Dict[str, Any]:
    """Process documents from a single source."""
    job_data = ctx.event.data
    source_id = job_data.get("sourceId")
    job_id = job_data.get("jobId")
    
    ctx.logger.info(f"Processing source {source_id} for job {job_id}")
    
    try:
        engine = IngestionEngine()
        registry = SourceRegistry()
        
        source = registry.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        # Process the source using the ingestion engine
        result = await engine.process_single_source(source.config.name)
        
        ctx.logger.info(
            f"Source processing completed",
            extra={
                "sourceId": source_id,
                "documentsProcessed": result.total_documents_processed,
                "successful": result.successful_documents,
                "failed": result.failed_documents,
            }
        )
        
        return {
            "sourceId": source_id,
            "jobId": job_id,
            "processedDocuments": result.total_documents_processed,
            "successfulDocuments": result.successful_documents,
            "failedDocuments": result.failed_documents,
            "executionTime": result.total_execution_time,
        }
    
    except Exception as e:
        ctx.logger.error(f"Source processing failed: {str(e)}")
        raise 