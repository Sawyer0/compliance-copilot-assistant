"""Configuration management for the ingestion engine."""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Directory Configuration
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    raw_output_dir: Path = Field(default="outputs/raw", env="RAW_OUTPUT_DIR")
    parsed_output_dir: Path = Field(default="outputs/parsed", env="PARSED_OUTPUT_DIR")
    metadata_output_dir: Path = Field(default="outputs/metadata", env="METADATA_OUTPUT_DIR")
    logs_output_dir: Path = Field(default="outputs/logs", env="LOGS_OUTPUT_DIR")
    
    # OCR Configuration
    tesseract_cmd: str = Field(default="tesseract", env="TESSERACT_CMD")
    ocr_enabled: bool = Field(default=True, env="OCR_ENABLED")
    
    # HTTP Configuration
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="RETRY_DELAY")
    
    # Processing Configuration
    max_concurrent_jobs: int = Field(default=5, env="MAX_CONCURRENT_JOBS")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    
    # Storage Configuration
    enable_deduplication: bool = Field(default=True, env="ENABLE_DEDUPLICATION")
    enable_versioning: bool = Field(default=True, env="ENABLE_VERSIONING")
    
    # Inngest Configuration
    inngest_event_key: Optional[str] = Field(default=None, env="INNGEST_EVENT_KEY")
    inngest_signing_key: Optional[str] = Field(default=None, env="INNGEST_SIGNING_KEY")
    inngest_base_url: str = Field(default="https://api.inngest.com", env="INNGEST_BASE_URL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=False, env="API_RELOAD")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_directories()
    
    def _setup_directories(self) -> None:
        """Create output directories if they don't exist."""
        directories = [
            self.raw_output_dir,
            self.parsed_output_dir,
            self.metadata_output_dir,
            self.logs_output_dir,
        ]
        
        for directory in directories:
            if not directory.is_absolute():
                directory = self.base_dir / directory
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def raw_output_path(self) -> Path:
        """Get absolute path to raw output directory."""
        if self.raw_output_dir.is_absolute():
            return self.raw_output_dir
        return self.base_dir / self.raw_output_dir
    
    @property
    def parsed_output_path(self) -> Path:
        """Get absolute path to parsed output directory."""
        if self.parsed_output_dir.is_absolute():
            return self.parsed_output_dir
        return self.base_dir / self.parsed_output_dir
    
    @property
    def metadata_output_path(self) -> Path:
        """Get absolute path to metadata output directory."""
        if self.metadata_output_dir.is_absolute():
            return self.metadata_output_dir
        return self.base_dir / self.metadata_output_dir
    
    @property
    def logs_output_path(self) -> Path:
        """Get absolute path to logs output directory."""
        if self.logs_output_dir.is_absolute():
            return self.logs_output_dir
        return self.base_dir / self.logs_output_dir


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 