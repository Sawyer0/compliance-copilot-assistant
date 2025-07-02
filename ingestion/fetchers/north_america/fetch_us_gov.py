"""Fetcher for US Government AI guidance and executive orders."""

import aiohttp
from typing import List, Optional
from pathlib import Path

from ..base_fetcher import BaseFetcher, FetchResult
from ...models.source import Source
from ...models.document import DocumentFormat, DocumentMetadata
from ...core.logging import get_logger

logger = get_logger(__name__)


class USGovernmentFetcher(BaseFetcher):
    """Fetcher for US Government AI sources (White House, FTC, etc.)."""
    
    def __init__(self, source: Source):
        super().__init__(source)
        self.session_timeout = aiohttp.ClientTimeout(total=60)  # Longer timeout for gov sites
    
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch documents from US Government sources."""
        results = []
        
        for endpoint in self.source.config.endpoints:
            try:
                logger.info(
                    "Fetching from US Government source",
                    source=self.source.config.name,
                    endpoint=endpoint
                )
                
                result = await self._fetch_single_endpoint(endpoint)
                if result:
                    results.append(result)
                
            except Exception as e:
                logger.error(
                    "Failed to fetch from US Government endpoint",
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
        """Fetch a single document from US Government endpoint."""
        full_url = f"{self.source.config.base_url}{endpoint}"
        
        try:
            async with self.session.get(
                full_url,
                headers=self.source.config.headers,
                timeout=self.session_timeout
            ) as response:
                
                if response.status != 200:
                    logger.warning(
                        "Non-200 response from US Government source",
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
                        'agency': self._determine_agency(full_url),
                        'document_type': self._determine_document_type(endpoint)
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
                "Error fetching from US Government endpoint",
                url=full_url,
                error=str(e)
            )
            return FetchResult(
                success=False,
                error_message=str(e),
                source_endpoint=endpoint
            )
    
    def _generate_filename(self, endpoint: str, extension: str) -> str:
        """Generate appropriate filename for US Government documents."""
        # Extract meaningful name from endpoint
        if 'whitehouse.gov' in str(self.source.config.base_url):
            if 'executive-order' in endpoint:
                return f"us_executive_order_ai{extension}"
            elif 'presidential-actions' in endpoint:
                return f"us_presidential_action_ai{extension}"
        elif 'ftc.gov' in str(self.source.config.base_url):
            if 'ai-claims' in endpoint:
                return f"ftc_ai_claims_guidance{extension}"
            elif 'aiming-truth' in endpoint:
                return f"ftc_ai_fairness_report{extension}"
        
        # Fallback: use sanitized endpoint
        safe_name = endpoint.replace('/', '_').replace('-', '_').strip('_')
        return f"us_gov_{safe_name}{extension}"
    
    def _determine_agency(self, url: str) -> str:
        """Determine the government agency from URL."""
        if 'whitehouse.gov' in url:
            return 'Executive Office of the President'
        elif 'ftc.gov' in url:
            return 'Federal Trade Commission'
        elif 'nist.gov' in url:
            return 'National Institute of Standards and Technology'
        else:
            return 'US Government'
    
    def _determine_document_type(self, endpoint: str) -> str:
        """Determine document type from endpoint."""
        if 'executive-order' in endpoint:
            return 'executive_order'
        elif 'presidential-actions' in endpoint:
            return 'presidential_action'
        elif 'business-guidance' in endpoint:
            return 'business_guidance'
        elif 'policy-reports' in endpoint:
            return 'policy_report'
        else:
            return 'government_document'
    
    async def health_check(self) -> bool:
        """Check if US Government sources are accessible."""
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
                        "US Government source health check passed",
                        source=self.source.config.name,
                        status=response.status
                    )
                    return True
                else:
                    logger.warning(
                        "US Government source health check failed",
                        source=self.source.config.name,
                        status=response.status
                    )
                    return False
        
        except Exception as e:
            logger.error(
                "US Government source health check error",
                source=self.source.config.name,
                error=str(e)
            )
            return False 