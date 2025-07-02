"""Logging configuration for the ingestion engine."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory

from .config import get_settings


def setup_logging() -> None:
    """Setup structured logging configuration."""
    settings = get_settings()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Create file handler for persistent logs
    log_file = settings.logs_output_path / "ingestion.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    if settings.log_format == "json":
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    
    # Add file handler to root logger
    logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class DocumentLogger:
    """Specialized logger for document processing."""
    
    def __init__(self, document_id: str, source_name: str):
        self.logger = get_logger("document_processor")
        self.document_id = document_id
        self.source_name = source_name
        self.context = {
            "document_id": document_id,
            "source_name": source_name,
        }
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with document context."""
        self.logger.info(message, **self.context, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with document context."""
        self.logger.error(message, **self.context, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with document context."""
        self.logger.warning(message, **self.context, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with document context."""
        self.logger.debug(message, **self.context, **kwargs)


class JobLogger:
    """Specialized logger for job processing."""
    
    def __init__(self, job_id: str, job_type: str):
        self.logger = get_logger("job_processor")
        self.job_id = job_id
        self.job_type = job_type
        self.context = {
            "job_id": job_id,
            "job_type": job_type,
        }
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with job context."""
        self.logger.info(message, **self.context, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with job context."""
        self.logger.error(message, **self.context, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with job context."""
        self.logger.warning(message, **self.context, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with job context."""
        self.logger.debug(message, **self.context, **kwargs) 