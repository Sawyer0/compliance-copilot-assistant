"""Fetcher for Canadian Government AI governance documents."""

import aiohttp
from typing import List, Optional
from pathlib import Path

from ..base_fetcher import BaseFetcher, FetchResult
from ...models.source import Source
from ...models.document import DocumentFormat, DocumentMetadata
from ...core.logging import get_logger

logger = get_logger(__name__)


class CanadianGovernmentFetcher(BaseFetcher):
    """Fetcher for Canadian Government AI sources (ISED, AI Commissioner, etc.)."""
    
    def __init__(self, source: Source):
        super().__init__(source)
        self.session_timeout = aiohttp.ClientTimeout(total=60)
    
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch documents from Canadian Government sources."""
        results = []
        
        for endpoint in self.source.config.endpoints:
            try:
                logger.info(
                    "Fetching from Canadian Government source",
                    source=self.source.config.name,
                    endpoint=endpoint
                )
                
                result = await self._fetch_single_endpoint(endpoint)
                if result:
                    results.append(result)
                
            except Exception as e:
                logger.error(
                    "Failed to fetch from Canadian Government endpoint",
                    endpoint=endpoint,
                    error=str(e)
                )
                results.append(FetchResult(
                    success=False,
                    error_message=f"Failed to fetch {endpoint}: {str(e)}",
                    source_endpoint=endpoint
                ))
        
        return results
    
    async def _fetch_single_endpoint(self, endpoint: str) -> Optional[FetchResult]:
        """Fetch a single document from Canadian Government endpoint."""
        full_url = f"{self.source.config.base_url}{endpoint}"
        
        try:
            async with self.session.get(
                full_url,
                headers=self.source.config.headers,
                timeout=self.session_timeout
            ) as response:
                
                if response.status != 200:
                    logger.warning(
                        "Non-200 response from Canadian Government source",
                        url=full_url,
                        status=response.status
                    )
                    return FetchResult(
                        success=False,
                        error_message=f"HTTP {response.status}",
                        source_endpoint=endpoint
                    )
                
                content = await response.read()
                content_type = response.headers.get('content-type', '').lower()
                
                # Determine document format
                if 'pdf' in content_type or endpoint.endswith('.pdf'):
                    doc_format = DocumentFormat.PDF
                    file_extension = '.pdf'
                elif 'html' in content_type or 'text/html' in content_type:
                    doc_format = DocumentFormat.HTML
                    file_extension = '.html'
                else:
                    # Default to HTML for government pages
                    doc_format = DocumentFormat.HTML
                    file_extension = '.html'
                
                # Generate filename
                filename = self._generate_filename(endpoint, file_extension)
                
                # Create metadata
                metadata = DocumentMetadata(
                    source_id=self.source.config.source_id,
                    source_name=self.source.config.name,
                    original_url=full_url,
                    document_format=doc_format,
                    file_size=len(content),
                    content_type=content_type,
                    jurisdiction=self.source.config.jurisdiction,
                    regulation_type=self.source.config.regulation_type,
                    tags=self.source.config.tags,
                    custom_metadata={
                        'government_level': 'federal',
                        'country': 'Canada',
                        'agency': self._determine_agency(full_url),
                        'document_type': self._determine_document_type(endpoint),
                        'language': self._determine_language(endpoint)
                    }
                )
                
                return FetchResult(
                    success=True,
                    content=content,
                    metadata=metadata,
                    filename=filename,
                    source_endpoint=endpoint
                )
        
        except Exception as e:
            logger.error(
                "Error fetching from Canadian Government endpoint",
                url=full_url,
                error=str(e)
            )
            return FetchResult(
                success=False,
                error_message=str(e),
                source_endpoint=endpoint
            )
    
    def _generate_filename(self, endpoint: str, extension: str) -> str:
        """Generate appropriate filename for Canadian Government documents."""
        # Extract meaningful name from endpoint
        if 'ised-isde.canada.ca' in str(self.source.config.base_url):
            if 'artificial-intelligence' in endpoint:
                return f"canada_ai_governance_framework{extension}"
            elif 'data-commissioner' in endpoint:
                return f"canada_data_commissioner_ai{extension}"
        
        # Fallback: use sanitized endpoint
        safe_name = endpoint.replace('/', '_').replace('-', '_').strip('_')
        return f"canada_gov_{safe_name}{extension}"
    
    def _determine_agency(self, url: str) -> str:
        """Determine the Canadian government agency from URL."""
        if 'ised-isde.canada.ca' in url:
            return 'Innovation, Science and Economic Development Canada'
        elif 'priv.gc.ca' in url:
            return 'Office of the Privacy Commissioner of Canada'
        elif 'parl.gc.ca' in url:
            return 'Parliament of Canada'
        else:
            return 'Government of Canada'
    
    def _determine_document_type(self, endpoint: str) -> str:
        """Determine document type from endpoint."""
        if 'artificial-intelligence' in endpoint:
            return 'ai_governance_framework'
        elif 'data-commissioner' in endpoint:
            return 'data_protection_guidance'
        elif 'guidance' in endpoint:
            return 'government_guidance'
        else:
            return 'government_document'
    
    def _determine_language(self, endpoint: str) -> str:
        """Determine document language from endpoint."""
        if '/en/' in endpoint or endpoint.endswith('/en'):
            return 'English'
        elif '/fr/' in endpoint or endpoint.endswith('/fr'):
            return 'French'
        else:
            return 'English'  # Default assumption
    
    async def health_check(self) -> bool:
        """Check if Canadian Government sources are accessible."""
        try:
            # Test connection to base URL
            async with self.session.get(
                str(self.source.config.base_url),
                headers=self.source.config.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                # Government sites should return 200-299 or reasonable redirects
                if 200 <= response.status < 400:
                    logger.info(
                        "Canadian Government source health check passed",
                        source=self.source.config.name,
                        status=response.status
                    )
                    return True
                else:
                    logger.warning(
                        "Canadian Government source health check failed",
                        source=self.source.config.name,
                        status=response.status
                    )
                    return False
        
        except Exception as e:
            logger.error(
                "Canadian Government source health check error",
                source=self.source.config.name,
                error=str(e)
            )
            return False 