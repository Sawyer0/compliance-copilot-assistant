"""Scheduled ingestion job functions."""

from typing import Dict, Any
import inngest
from .client import inngest_client
from core.logging import get_logger
from core.registry import SourceRegistry

logger = get_logger(__name__)


@inngest_client.create_function(
    fn_id="scheduled_ingestion",
    trigger=inngest.TriggerCron("0 2 * * *"),  # Daily at 2 AM
)
async def scheduled_ingestion(ctx: inngest.Context) -> Dict[str, Any]:
    """Scheduled ingestion trigger."""
    ctx.logger.info("Running scheduled ingestion")
    
    try:
        registry = SourceRegistry()
        active_sources = registry.list_sources(active_only=True)
        
        if not active_sources:
            ctx.logger.info("No active sources found")
            return {"sourcesDue": 0, "triggered": False}
        
        # Filter sources that are due for update based on their fetch_frequency
        sources_due = []
        for source in active_sources:
            # Simple logic - can be enhanced with more sophisticated scheduling
            if _is_source_due_for_update(source):
                sources_due.append(source)
        
        if not sources_due:
            ctx.logger.info("No sources due for update")
            return {"sourcesDue": 0, "triggered": False}
        
        # Trigger ingestion for due sources
        source_ids = [str(source.config.source_id) for source in sources_due]
        
        await inngest_client.send(
            inngest.Event(
                name="ingestion/job.triggered",
                data={
                    "jobId": f"scheduled-{ctx.run_id}",
                    "jobType": "scheduled_update",
                    "sourceIds": source_ids,
                    "priority": 3,
                }
            )
        )
        
        ctx.logger.info(f"Triggered scheduled ingestion for {len(source_ids)} sources")
        
        return {
            "sourcesDue": len(source_ids),
            "triggered": True,
            "sourceNames": [s.config.name for s in sources_due],
        }
    
    except Exception as e:
        ctx.logger.error(f"Scheduled ingestion failed: {str(e)}")
        raise


@inngest_client.create_function(
    fn_id="weekly_maintenance",
    trigger=inngest.TriggerCron("0 1 * * 0"),  # Weekly on Sunday at 1 AM
)
async def weekly_maintenance(ctx: inngest.Context) -> Dict[str, Any]:
    """Weekly maintenance tasks."""
    ctx.logger.info("Running weekly maintenance")
    
    try:
        # Add maintenance tasks here:
        # - Clean up old files
        # - Update source statistics
        # - Health checks
        
        maintenance_tasks = []
        
        # Example: Clean up old logs (older than 30 days)
        from core.config import get_settings
        settings = get_settings()
        
        log_cleanup_count = _cleanup_old_logs(settings.logs_output_path, days=30)
        maintenance_tasks.append(f"Cleaned up {log_cleanup_count} old log files")
        
        # Example: Update source health status
        registry = SourceRegistry()
        sources = registry.list_sources()
        health_checks = []
        
        for source in sources:
            if source.config.is_active:
                # This would be a health check implementation
                health_checks.append(source.config.name)
        
        maintenance_tasks.append(f"Health checked {len(health_checks)} sources")
        
        ctx.logger.info("Weekly maintenance completed", extra={
            "tasks_completed": len(maintenance_tasks),
            "tasks": maintenance_tasks
        })
        
        return {
            "status": "completed",
            "tasks_completed": len(maintenance_tasks),
            "tasks": maintenance_tasks,
        }
    
    except Exception as e:
        ctx.logger.error(f"Weekly maintenance failed: {str(e)}")
        raise


def _is_source_due_for_update(source) -> bool:
    """Check if a source is due for update based on its frequency."""
    from datetime import datetime, timedelta
    
    if not source.config.last_fetched:
        return True  # Never fetched, so it's due
    
    now = datetime.utcnow()
    last_fetched = source.config.last_fetched
    
    frequency_map = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1), 
        "monthly": timedelta(days=30),
        "quarterly": timedelta(days=90),
    }
    
    frequency = source.config.fetch_frequency.lower()
    interval = frequency_map.get(frequency, timedelta(weeks=1))  # Default to weekly
    
    return (now - last_fetched) >= interval


def _cleanup_old_logs(logs_dir, days: int = 30) -> int:
    """Clean up log files older than specified days."""
    from datetime import datetime, timedelta
    import os
    
    if not logs_dir.exists():
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days)
    cleaned_count = 0
    
    try:
        for log_file in logs_dir.glob("*.log"):
            if log_file.is_file():
                file_time = datetime.fromtimestamp(os.path.getctime(log_file))
                if file_time < cutoff_date:
                    log_file.unlink()
                    cleaned_count += 1
    except Exception as e:
        logger.warning(f"Error during log cleanup: {str(e)}")
    
    return cleaned_count 