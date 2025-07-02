"""Ingestion job models for orchestration."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(str, Enum):
    """Job type enumeration."""
    SINGLE_DOCUMENT = "single_document"
    SOURCE_BATCH = "source_batch"
    FULL_INGESTION = "full_ingestion"
    SCHEDULED_UPDATE = "scheduled_update"
    RETRY_FAILED = "retry_failed"


class IngestionJob(BaseModel):
    """Ingestion job model."""
    job_id: UUID = Field(default_factory=uuid4)
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    
    # Job configuration
    source_ids: List[UUID] = Field(default_factory=list)
    document_ids: List[UUID] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    
    # Execution configuration
    max_concurrent_tasks: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=3600, ge=60, le=86400)
    retry_count: int = Field(default=3, ge=0, le=10)
    
    # Metadata
    created_by: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    parent_job_id: Optional[UUID] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Results
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    
    # Error handling
    error_message: Optional[str] = None
    execution_logs: List[str] = Field(default_factory=list)
    
    # Inngest specific
    inngest_event_id: Optional[str] = None
    inngest_run_id: Optional[str] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
    
    def add_log(self, message: str) -> None:
        """Add execution log entry."""
        self.execution_logs.append(f"{datetime.utcnow().isoformat()}: {message}")
        self.updated_at = datetime.utcnow()
    
    def update_status(self, status: JobStatus, error: Optional[str] = None) -> None:
        """Update job status."""
        self.status = status
        self.error_message = error
        self.updated_at = datetime.utcnow()
        
        if status == JobStatus.RUNNING and self.started_at is None:
            self.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            self.completed_at = datetime.utcnow()
        
        status_msg = f"Job status changed to {status.value}"
        if error:
            status_msg += f" - Error: {error}"
        self.add_log(status_msg)
    
    def update_progress(self, completed: int, failed: int, skipped: int = 0) -> None:
        """Update job progress."""
        self.completed_tasks = completed
        self.failed_tasks = failed
        self.skipped_tasks = skipped
        self.updated_at = datetime.utcnow()
    
    @property
    def progress_percentage(self) -> float:
        """Calculate job progress percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks + self.failed_tasks + self.skipped_tasks) / self.total_tasks * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if job is complete."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]


class TaskResult(BaseModel):
    """Individual task result."""
    task_id: UUID = Field(default_factory=uuid4)
    document_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    status: JobStatus
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Results
    success: bool = False
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


class IngestionResult(BaseModel):
    """Complete ingestion result."""
    job: IngestionJob
    task_results: List[TaskResult] = Field(default_factory=list)
    
    # Summary statistics
    total_documents_processed: int = 0
    successful_documents: int = 0
    failed_documents: int = 0
    skipped_documents: int = 0
    
    # Performance metrics
    total_execution_time: Optional[float] = None
    average_task_time: Optional[float] = None
    documents_per_minute: Optional[float] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
    
    def calculate_metrics(self) -> None:
        """Calculate performance metrics."""
        if self.job.started_at and self.job.completed_at:
            self.total_execution_time = (
                self.job.completed_at - self.job.started_at
            ).total_seconds()
            
            if self.total_execution_time > 0:
                self.documents_per_minute = self.total_documents_processed / (self.total_execution_time / 60)
        
        task_times = [
            result.duration_seconds for result in self.task_results 
            if result.duration_seconds is not None
        ]
        
        if task_times:
            self.average_task_time = sum(task_times) / len(task_times) 