"""Source configuration models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, validator


class SourceType(str, Enum):
    """Source type enumeration."""
    STATIC_PDF = "static_pdf"
    STATIC_HTML = "static_html"
    RSS_FEED = "rss_feed"
    API_ENDPOINT = "api_endpoint"
    WEB_SCRAPER = "web_scraper"
    DOCUMENT_LIBRARY = "document_library"


class FetchMethod(str, Enum):
    """Fetch method enumeration."""
    DIRECT_DOWNLOAD = "direct_download"
    WEB_SCRAPING = "web_scraping"
    API_CALL = "api_call"
    RSS_PARSING = "rss_parsing"


class SourceConfig(BaseModel):
    """Source configuration model."""
    source_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_type: SourceType
    fetch_method: FetchMethod
    
    # URL Configuration
    base_url: HttpUrl
    endpoints: List[str] = Field(default_factory=list)
    
    # Authentication
    auth_type: Optional[str] = None  # "bearer", "basic", "api_key", etc.
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Request Configuration
    headers: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, str] = Field(default_factory=dict)
    request_timeout: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    
    # Scheduling
    fetch_frequency: str = "weekly"  # "daily", "weekly", "monthly", "on_demand"
    schedule_cron: Optional[str] = None
    
    # Processing Configuration
    parser_config: Dict[str, Any] = Field(default_factory=dict)
    custom_selectors: Dict[str, str] = Field(default_factory=dict)
    
    # Metadata
    jurisdiction: Optional[str] = None
    regulation_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    
    # Status
    is_active: bool = True
    last_fetched: Optional[datetime] = None
    last_successful_fetch: Optional[datetime] = None
    consecutive_failures: int = 0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
    
    @validator('schedule_cron')
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.strip():
            return None
        # Basic cron validation would go here
        return v


class Source(BaseModel):
    """Complete source model with runtime state."""
    config: SourceConfig
    
    # Runtime state
    is_running: bool = False
    current_job_id: Optional[UUID] = None
    last_error: Optional[str] = None
    
    # Statistics
    total_documents_fetched: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    average_fetch_time: Optional[float] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
    
    def update_stats(self, success: bool, fetch_time: float) -> None:
        """Update fetch statistics."""
        self.config.last_fetched = datetime.utcnow()
        
        if success:
            self.successful_fetches += 1
            self.config.last_successful_fetch = datetime.utcnow()
            self.config.consecutive_failures = 0
        else:
            self.failed_fetches += 1
            self.config.consecutive_failures += 1
        
        self.total_documents_fetched += 1
        
        # Update average fetch time
        if self.average_fetch_time is None:
            self.average_fetch_time = fetch_time
        else:
            self.average_fetch_time = (
                (self.average_fetch_time * (self.total_documents_fetched - 1) + fetch_time)
                / self.total_documents_fetched
            )
        
        self.config.updated_at = datetime.utcnow() 