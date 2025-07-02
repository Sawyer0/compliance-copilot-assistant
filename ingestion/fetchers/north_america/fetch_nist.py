"""NIST document fetcher implementation."""

from typing import List
from urllib.parse import urljoin

from ..base_fetcher import BaseFetcher, FetchResult


class NISTFetcher(BaseFetcher):
    """Fetcher for NIST documents."""
    
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch NIST documents."""
        results = []
        
        # Common NIST documents
        nist_documents = [
            {
                "url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
                "title": "NIST AI Risk Management Framework (AI RMF 1.0)"
            },
            {
                "url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf", 
                "title": "NIST AI Risk Management Framework: Generative AI Profile"
            },
            {
                "url": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.01162023.pdf",
                "title": "NIST Cybersecurity Framework 2.0"
            }
        ]
        
        # Add any endpoint URLs from source config
        for endpoint in self.source.config.endpoints:
            nist_documents.append({
                "url": urljoin(str(self.source.config.base_url), endpoint),
                "title": f"NIST Document - {endpoint}"
            })
        
        for doc_info in nist_documents:
            result = await self._fetch_url(doc_info["url"])
            
            if result.success:
                # Add NIST-specific metadata
                if result.metadata is None:
                    result.metadata = {}
                
                result.metadata.update({
                    "document_title": doc_info["title"],
                    "source_type": "nist_publication",
                    "publication_type": "technical_standard"
                })
                
                self.logger.info(
                    "Successfully fetched NIST document",
                    title=doc_info["title"],
                    url=doc_info["url"]
                )
            else:
                self.logger.error(
                    "Failed to fetch NIST document", 
                    title=doc_info["title"],
                    url=doc_info["url"],
                    error=result.error_message
                )
            
            results.append(result)
        
        return results
    
    async def fetch_latest_documents(self) -> List[FetchResult]:
        """Fetch the latest NIST AI documents."""
        # This could be enhanced to scrape the NIST publications page
        # for the most recent AI-related documents
        return await self.fetch_documents()
