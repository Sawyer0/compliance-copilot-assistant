"""Inngest job functions for compliance document ingestion."""

from .job_orchestrator import process_ingestion_job, handle_job_completion
from .source_processor import process_source
from .schedulers import scheduled_ingestion, weekly_maintenance
from .client import inngest_client

# Collect all functions for FastAPI integration
inngest_functions = [
    process_ingestion_job,
    process_source,
    scheduled_ingestion,
    weekly_maintenance,
    handle_job_completion,
]

__all__ = [
    "inngest_client",
    "inngest_functions",
    "process_ingestion_job",
    "process_source", 
    "scheduled_ingestion",
    "weekly_maintenance",
    "handle_job_completion",
] 