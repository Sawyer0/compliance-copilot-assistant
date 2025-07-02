"""Document models for compliance ingestion."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    FETCHING = "fetching"
    PARSING = "parsing"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    HTML = "html"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"


class DocumentMetadata(BaseModel):
    """Document metadata model."""
    doc_id: UUID = Field(default_factory=uuid4)
    source_name: str
    title: Optional[str] = None
    url: Optional[str] = None
    jurisdiction: Optional[str] = None
    regulation_type: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    language: str = "en"
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    # Processing metadata
    fetch_timestamp: Optional[datetime] = None
    parse_timestamp: Optional[datetime] = None
    parse_quality_score: Optional[float] = None
    extraction_method: Optional[str] = None
    
    class Config:
        use_enum_values = True


class DocumentContent(BaseModel):
    """Document content structure."""
    raw_text: str
    structured_sections: List[Dict[str, str]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    images: List[Dict[str, str]] = Field(default_factory=list)
    links: List[Dict[str, str]] = Field(default_factory=list)
    
    @validator('raw_text')
    def validate_raw_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Raw text cannot be empty")
        return v


class Document(BaseModel):
    """Complete document model."""
    metadata: DocumentMetadata
    content: Optional[DocumentContent] = None
    status: DocumentStatus = DocumentStatus.PENDING
    format: DocumentFormat
    
    # File paths
    raw_file_path: Optional[Path] = None
    parsed_file_path: Optional[Path] = None
    metadata_file_path: Optional[Path] = None
    
    # Processing info
    error_message: Optional[str] = None
    processing_logs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
    
    def add_log(self, message: str) -> None:
        """Add a processing log entry."""
        self.processing_logs.append(f"{datetime.utcnow().isoformat()}: {message}")
        self.updated_at = datetime.utcnow()
    
    def update_status(self, status: DocumentStatus, error: Optional[str] = None) -> None:
        """Update document status."""
        self.status = status
        self.error_message = error
        self.updated_at = datetime.utcnow()
        
        status_msg = f"Status changed to {status.value}"
        if error:
            status_msg += f" - Error: {error}"
        self.add_log(status_msg) 