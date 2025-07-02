"""Fetcher for international regulatory bodies and standards organizations."""

import aiohttp
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..base_fetcher import BaseFetcher, FetchResult
from ...models.source import Source
from ...models.document import DocumentFormat, DocumentMetadata
from ...core.logging import get_logger

logger = get_logger(__name__)


class InternationalRegulatoryFetcher(BaseFetcher):
    """Fetcher for international regulatory bodies (Singapore, ISO, GDPR, etc.)."""
    
    def __init__(self, source: Source):
        super().__init__(source)
        self.session_timeout = aiohttp.ClientTimeout(total=90)  # Longer timeout for international sites
    
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch documents from international regulatory sources."""
        results = []
        
        for endpoint in self.source.config.endpoints:
            try:
                logger.info(
                    "Fetching from international regulatory source",
                    source=self.source.config.name,
                    endpoint=endpoint,
                    jurisdiction=self.source.config.jurisdiction
                )
                
                result = await self._fetch_single_endpoint(endpoint)
                if result:
                    results.append(result)
                
            except Exception as e:
                logger.error(
                    "Failed to fetch from international regulatory endpoint",
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
        """Fetch a single document from international regulatory endpoint."""
        full_url = f"{self.source.config.base_url}{endpoint}"
        
        try:
            # Some international sites may require special headers
            headers = dict(self.source.config.headers) if self.source.config.headers else {}
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Cache-Control': 'no-cache'
            })
            
            async with self.session.get(
                full_url,
                headers=headers,
                timeout=self.session_timeout
            ) as response:
                
                if response.status != 200:
                    logger.warning(
                        "Non-200 response from international regulatory source",
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
                    # Default to HTML for regulatory pages
                    doc_format = DocumentFormat.HTML
                    file_extension = '.html'
                
                # Generate filename
                filename = self._generate_filename(endpoint, file_extension)
                
                # Create metadata with enhanced international context
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
                    custom_metadata=self._build_custom_metadata(full_url, endpoint)
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
                "Error fetching from international regulatory endpoint",
                url=full_url,
                error=str(e)
            )
            return FetchResult(
                success=False,
                error_message=str(e),
                source_endpoint=endpoint
            )
    
    def _generate_filename(self, endpoint: str, extension: str) -> str:
        """Generate appropriate filename for international regulatory documents."""
        base_url = str(self.source.config.base_url).lower()
        
        # Singapore sources
        if 'pdpc.gov.sg' in base_url or 'smartnation.gov.sg' in base_url:
            if 'model-ai-governance' in endpoint:
                return f"singapore_ai_governance_model{extension}"
            elif 'artificial-intelligence' in endpoint:
                return f"singapore_ai_guidance{extension}"
        
        # ISO/IEC sources
        elif 'iso.org' in base_url or 'iec.ch' in base_url:
            if '23053' in endpoint:
                return f"iso_iec_23053_ai_framework{extension}"
            elif '23894' in endpoint:
                return f"iso_iec_23894_ai_risk_management{extension}"
            elif 'artificial-intelligence' in endpoint:
                return f"iso_iec_ai_standards{extension}"
        
        # GDPR/EDPB sources
        elif 'edpb.europa.eu' in base_url:
            if 'gdpr' in endpoint and 'ai' in endpoint:
                return f"edpb_gdpr_ai_guidance{extension}"
            elif 'artificial-intelligence' in endpoint:
                return f"edpb_ai_guidance{extension}"
        
        # Fallback: use sanitized endpoint with jurisdiction prefix
        jurisdiction_prefix = self.source.config.jurisdiction.lower().replace(' ', '_')
        safe_name = endpoint.replace('/', '_').replace('-', '_').strip('_')
        return f"{jurisdiction_prefix}_{safe_name}{extension}"
    
    def _build_custom_metadata(self, url: str, endpoint: str) -> Dict[str, Any]:
        """Build enhanced metadata for international regulatory documents."""
        metadata = {
            'organization_type': self._determine_organization_type(url),
            'document_type': self._determine_document_type(endpoint),
            'geographic_scope': self._determine_geographic_scope(url)
        }
        
        # Add specific metadata based on source
        if 'singapore' in self.source.config.jurisdiction.lower():
            metadata.update({
                'country': 'Singapore',
                'agency': self._determine_singapore_agency(url),
                'development_stage': self._determine_development_stage(endpoint)
            })
        elif 'iso' in url.lower() or 'iec' in url.lower():
            metadata.update({
                'standards_body': 'ISO/IEC',
                'standard_type': self._determine_standard_type(endpoint),
                'status': self._determine_standard_status(endpoint)
            })
        elif 'edpb' in url.lower() or 'gdpr' in endpoint.lower():
            metadata.update({
                'regulatory_body': 'European Data Protection Board',
                'legal_basis': 'GDPR',
                'binding_nature': self._determine_binding_nature(endpoint)
            })
        
        return metadata
    
    def _determine_organization_type(self, url: str) -> str:
        """Determine the type of organization."""
        if any(domain in url for domain in ['gov.sg', 'pdpc.gov.sg']):
            return 'government_agency'
        elif any(domain in url for domain in ['iso.org', 'iec.ch']):
            return 'standards_organization'
        elif 'edpb.europa.eu' in url:
            return 'regulatory_authority'
        else:
            return 'regulatory_body'
    
    def _determine_document_type(self, endpoint: str) -> str:
        """Determine document type from endpoint."""
        if 'model' in endpoint or 'framework' in endpoint:
            return 'governance_framework'
        elif 'guidance' in endpoint:
            return 'regulatory_guidance'
        elif 'standard' in endpoint:
            return 'technical_standard'
        elif 'consultation' in endpoint:
            return 'public_consultation'
        else:
            return 'regulatory_document'
    
    def _determine_geographic_scope(self, url: str) -> str:
        """Determine geographic scope."""
        if 'gov.sg' in url:
            return 'national_singapore'
        elif 'europa.eu' in url:
            return 'european_union'
        elif any(domain in url for domain in ['iso.org', 'iec.ch']):
            return 'international'
        else:
            return 'regional'
    
    def _determine_singapore_agency(self, url: str) -> str:
        """Determine Singapore government agency."""
        if 'pdpc.gov.sg' in url:
            return 'Personal Data Protection Commission'
        elif 'smartnation.gov.sg' in url:
            return 'Smart Nation and Digital Government Office'
        elif 'gov.sg' in url:
            return 'Government of Singapore'
        else:
            return 'Singapore Government'
    
    def _determine_development_stage(self, endpoint: str) -> str:
        """Determine development stage for Singapore documents."""
        if 'draft' in endpoint:
            return 'draft'
        elif 'consultation' in endpoint:
            return 'consultation'
        elif 'final' in endpoint:
            return 'final'
        else:
            return 'published'
    
    def _determine_standard_type(self, endpoint: str) -> str:
        """Determine ISO/IEC standard type."""
        if '23053' in endpoint:
            return 'framework_standard'
        elif '23894' in endpoint:
            return 'risk_management_standard'
        else:
            return 'technical_standard'
    
    def _determine_standard_status(self, endpoint: str) -> str:
        """Determine ISO/IEC standard status."""
        if 'draft' in endpoint:
            return 'draft'
        elif 'published' in endpoint:
            return 'published'
        else:
            return 'active'
    
    def _determine_binding_nature(self, endpoint: str) -> str:
        """Determine binding nature of GDPR guidance."""
        if 'guidance' in endpoint:
            return 'guidance'
        elif 'opinion' in endpoint:
            return 'advisory'
        elif 'decision' in endpoint:
            return 'binding'
        else:
            return 'interpretive'
    
    async def health_check(self) -> bool:
        """Check if international regulatory sources are accessible."""
        try:
            # Test connection to base URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(
                str(self.source.config.base_url),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                # International sites should return 200-299 or reasonable redirects
                if 200 <= response.status < 400:
                    logger.info(
                        "International regulatory source health check passed",
                        source=self.source.config.name,
                        status=response.status
                    )
                    return True
                else:
                    logger.warning(
                        "International regulatory source health check failed",
                        source=self.source.config.name,
                        status=response.status
                    )
                    return False
        
        except Exception as e:
            logger.error(
                "International regulatory source health check error",
                source=self.source.config.name,
                error=str(e)
            )
            return False 