"""Base fetcher class for document retrieval."""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import UUID

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.document import DocumentFormat, DocumentMetadata
from ..models.source import Source

logger = get_logger(__name__)


class FetchResult(BaseModel):
    """Result of a fetch operation."""
    success: bool
    content: Optional[Union[bytes, str]] = None
    content_type: Optional[str] = None
    file_extension: Optional[str] = None
    metadata: Optional[Dict[str, any]] = None
    error_message: Optional[str] = None
    fetch_time: float = 0.0
    file_size: Optional[int] = None
    
    class Config:
        arbitrary_types_allowed = True


class BaseFetcher(ABC):
    """Base class for document fetchers."""
    
    def __init__(self, source: Source):
        self.source = source
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=self.source.config.request_timeout,
            headers=self.source.config.headers,
            follow_redirects=True
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @abstractmethod
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch documents from the source."""
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _fetch_url(
        self, 
        url: str, 
        additional_headers: Optional[Dict[str, str]] = None
    ) -> FetchResult:
        """Fetch content from a URL with retry logic."""
        start_time = time.time()
        
        try:
            headers = self.source.config.headers.copy()
            if additional_headers:
                headers.update(additional_headers)
            
            logger.info(
                "Fetching URL",
                url=url,
                source_name=self.source.config.name
            )
            
            response = await self.client.get(
                url,
                headers=headers,
                params=self.source.config.query_params
            )
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            content = response.content
            
            # Determine file extension from content type
            file_extension = self._get_extension_from_content_type(content_type)
            
            fetch_time = time.time() - start_time
            
            logger.info(
                "Successfully fetched URL",
                url=url,
                content_type=content_type,
                file_size=len(content),
                fetch_time=fetch_time
            )
            
            return FetchResult(
                success=True,
                content=content,
                content_type=content_type,
                file_extension=file_extension,
                fetch_time=fetch_time,
                file_size=len(content),
                metadata={
                    'url': url,
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }
            )
        
        except Exception as e:
            fetch_time = time.time() - start_time
            error_msg = f"Failed to fetch {url}: {str(e)}"
            
            logger.error(
                "Failed to fetch URL",
                url=url,
                error=str(e),
                fetch_time=fetch_time
            )
            
            return FetchResult(
                success=False,
                error_message=error_msg,
                fetch_time=fetch_time
            )
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        content_type_map = {
            'application/pdf': 'pdf',
            'text/html': 'html',
            'text/plain': 'txt',
            'application/json': 'json',
            'application/xml': 'xml',
            'text/xml': 'xml',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        }
        
        for mime_type, extension in content_type_map.items():
            if mime_type in content_type:
                return extension
        
        return 'bin'  # Default for unknown types
    
    def _extract_metadata_from_response(
        self, 
        response_metadata: Dict,
        url: str
    ) -> DocumentMetadata:
        """Extract document metadata from HTTP response."""
        headers = response_metadata.get('headers', {})
        
        # Try to extract title from URL or headers
        title = None
        if 'content-disposition' in headers:
            # Extract filename from Content-Disposition header
            cd = headers['content-disposition']
            if 'filename=' in cd:
                title = cd.split('filename=')[1].strip('"\'')
        
        if not title:
            # Use URL basename as fallback
            title = Path(url).name or "Unknown Document"
        
        return DocumentMetadata(
            source_name=self.source.config.name,
            title=title,
            url=url,
            jurisdiction=self.source.config.jurisdiction,
            regulation_type=self.source.config.regulation_type,
            tags=self.source.config.tags.copy(),
            fetch_timestamp=datetime.utcnow(),
            last_modified=self._parse_last_modified(headers.get('last-modified')),
            custom_fields=response_metadata
        )
    
    def _parse_last_modified(self, last_modified_str: Optional[str]) -> Optional[datetime]:
        """Parse Last-Modified header to datetime."""
        if not last_modified_str:
            return None
        
        try:
            # Try common HTTP date formats
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(last_modified_str)
        except Exception:
            logger.warning(
                "Failed to parse Last-Modified header",
                last_modified=last_modified_str
            )
            return None
    
    async def health_check(self) -> bool:
        """Check if the source is accessible."""
        try:
            response = await self.client.head(str(self.source.config.base_url))
            return response.status_code < 400
        except Exception as e:
            logger.warning(
                "Health check failed",
                source_name=self.source.config.name,
                error=str(e)
            )
            return False 