"""EU AI Act document fetcher implementation."""

from typing import List
from urllib.parse import urljoin

from ..base_fetcher import BaseFetcher, FetchResult


class EUAIActFetcher(BaseFetcher):
    """Fetcher for EU AI Act documents."""
    
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch EU AI Act documents."""
        results = []
        
        # EU AI Act documents and related materials
        eu_documents = [
            {
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32024R1689",
                "title": "EU AI Act - Regulation (EU) 2024/1689"
            },
            {
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689",
                "title": "EU AI Act - HTML Version"
            },
            {
                "url": "https://artificialintelligenceact.eu/the-act/",
                "title": "EU AI Act - Summary and Analysis"
            }
        ]
        
        # Add any endpoint URLs from source config
        for endpoint in self.source.config.endpoints:
            eu_documents.append({
                "url": urljoin(str(self.source.config.base_url), endpoint),
                "title": f"EU AI Act Document - {endpoint}"
            })
        
        for doc_info in eu_documents:
            result = await self._fetch_url(doc_info["url"])
            
            if result.success:
                # Add EU-specific metadata
                if result.metadata is None:
                    result.metadata = {}
                
                result.metadata.update({
                    "document_title": doc_info["title"],
                    "source_type": "eu_regulation",
                    "regulation_type": "ai_governance",
                    "jurisdiction": "European Union",
                    "legal_framework": "EU Regulation",
                    "celex_number": "32024R1689" if "CELEX" in doc_info["url"] else None
                })
                
                self.logger.info(
                    "Successfully fetched EU AI Act document",
                    title=doc_info["title"],
                    url=doc_info["url"]
                )
            else:
                self.logger.error(
                    "Failed to fetch EU AI Act document", 
                    title=doc_info["title"],
                    url=doc_info["url"],
                    error=result.error_message
                )
            
            results.append(result)
        
        return results
    
    async def fetch_supporting_documents(self) -> List[FetchResult]:
        """Fetch supporting EU AI Act documents and guidance."""
        results = []
        
        supporting_docs = [
            {
                "url": "https://digital-strategy.ec.europa.eu/en/policies/european-approach-artificial-intelligence",
                "title": "European Approach to Artificial Intelligence"
            },
            {
                "url": "https://ec.europa.eu/futurium/en/ai-alliance-consultation.html",
                "title": "AI Alliance Consultation"
            }
        ]
        
        for doc_info in supporting_docs:
            result = await self._fetch_url(doc_info["url"])
            
            if result.success and result.metadata:
                result.metadata.update({
                    "document_title": doc_info["title"],
                    "source_type": "eu_policy",
                    "document_category": "supporting_guidance"
                })
            
            results.append(result)
        
        return results
