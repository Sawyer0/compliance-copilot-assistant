"""Scheduled workflows using Inngest's native cron capabilities."""

import datetime
import logging
from typing import Dict, Any

import inngest
from ingestion_functions.client import inngest_client

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="daily_compliance_check",
    trigger=inngest.TriggerCron(cron="0 2 * * *"),  # Daily at 2 AM
)
async def daily_compliance_check(ctx: inngest.Context) -> Dict[str, Any]:
    """Daily scheduled compliance document ingestion using Inngest cron."""
    
    ctx.logger.info("Starting daily compliance document check")
    
    # Send event to trigger the main workflow
    await inngest_client.send(inngest.Event(
        name="compliance/ingestion.start",
        data={
            "triggered_by": "daily_schedule",
            "triggered_at": datetime.datetime.now().isoformat(),
            "schedule_type": "daily"
        }
    ))
    
    return {
        "status": "daily_check_triggered",
        "triggered_at": datetime.datetime.now().isoformat(),
        "next_run": "tomorrow at 2 AM"
    }


@inngest_client.create_function(
    fn_id="weekly_maintenance",
    trigger=inngest.TriggerCron(cron="0 1 * * 0"),  # Weekly on Sunday at 1 AM
)
async def weekly_maintenance(ctx: inngest.Context) -> Dict[str, Any]:
    """Weekly maintenance tasks using Inngest scheduling."""
    
    ctx.logger.info("Starting weekly maintenance")
    
    # Use Inngest steps for maintenance tasks
    cleanup_count = await ctx.step.run("cleanup_old_files", _cleanup_old_files_step)
    health_check = await ctx.step.run("health_check", _system_health_check_step)
    
    # Send notification event
    await inngest_client.send(inngest.Event(
        name="maintenance/completed",
        data={
            "cleanup_count": cleanup_count,
            "health_status": health_check,
            "completed_at": datetime.datetime.now().isoformat()
        }
    ))
    
    return {
        "status": "maintenance_completed",
        "files_cleaned": cleanup_count,
        "health_status": health_check,
        "completed_at": datetime.datetime.now().isoformat()
    }


# Inngest step functions for maintenance
async def _cleanup_old_files_step() -> int:
    """Clean up old log files and temporary data."""
    import os
    from pathlib import Path
    
    cleanup_count = 0
    
    # Clean up old logs (older than 30 days)
    logs_dir = Path("outputs/logs")
    if logs_dir.exists():
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
        
        for log_file in logs_dir.glob("*.log"):
            if log_file.is_file():
                file_time = datetime.datetime.fromtimestamp(os.path.getctime(log_file))
                if file_time < cutoff_date:
                    log_file.unlink()
                    cleanup_count += 1
    
    return cleanup_count


async def _system_health_check_step() -> str:
    """Perform basic system health checks."""
    from pathlib import Path
    
    # Check if required directories exist
    required_dirs = ["outputs/raw", "outputs/parsed", "outputs/metadata"]
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            return "unhealthy"
    
    # Could add more health checks here
    return "healthy" 