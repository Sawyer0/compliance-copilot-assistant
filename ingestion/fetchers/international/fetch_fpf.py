"""Future of Privacy Forum (FPF) document fetcher implementation."""

from typing import List
from urllib.parse import urljoin, urlparse
import re

from bs4 import BeautifulSoup

from ..base_fetcher import BaseFetcher, FetchResult


class FPFFetcher(BaseFetcher):
    """Fetcher for Future of Privacy Forum documents."""
    
    async def fetch_documents(self) -> List[FetchResult]:
        """Fetch FPF documents."""
        results = []
        
        # Key FPF AI-related publications
        fpf_documents = [
            {
                "url": "https://fpf.org/blog/fpf-report-artificial-intelligence-and-privacy-fundamental-challenges-and-solutions/",
                "title": "AI and Privacy: Fundamental Challenges and Solutions"
            },
            {
                "url": "https://fpf.org/blog/algorithmic-auditing-and-assessments/",
                "title": "Algorithmic Auditing and Assessments"
            },
            {
                "url": "https://fpf.org/blog/privacy-and-ai-governance/",
                "title": "Privacy and AI Governance"
            }
        ]
        
        # Add any endpoint URLs from source config
        for endpoint in self.source.config.endpoints:
            fpf_documents.append({
                "url": urljoin(str(self.source.config.base_url), endpoint),
                "title": f"FPF Document - {endpoint}"
            })
        
        for doc_info in fpf_documents:
            result = await self._fetch_url(doc_info["url"])
            
            if result.success:
                # Add FPF-specific metadata
                if result.metadata is None:
                    result.metadata = {}
                
                result.metadata.update({
                    "document_title": doc_info["title"],
                    "source_type": "privacy_advocacy",
                    "organization": "Future of Privacy Forum",
                    "document_category": "research_report",
                    "focus_area": "privacy_ai_intersection"
                })
                
                self.logger.info(
                    "Successfully fetched FPF document",
                    title=doc_info["title"],
                    url=doc_info["url"]
                )
            else:
                self.logger.error(
                    "Failed to fetch FPF document", 
                    title=doc_info["title"],
                    url=doc_info["url"],
                    error=result.error_message
                )
            
            results.append(result)
        
        return results
    
    async def fetch_latest_publications(self) -> List[FetchResult]:
        """Fetch latest FPF publications from their blog/reports section."""
        results = []
        
        try:
            # Fetch the main publications page
            blog_result = await self._fetch_url("https://fpf.org/blog/")
            
            if not blog_result.success:
                self.logger.error("Failed to fetch FPF blog page")
                return results
            
            # Parse the HTML to find recent AI-related publications
            soup = BeautifulSoup(blog_result.content, 'html.parser')
            
            # Look for article links (this is site-specific and may need adjustment)
            article_links = []
            
            # Find links that might be AI/privacy related
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                # Filter for AI/algorithmic/privacy content
                ai_keywords = ['artificial intelligence', 'ai', 'algorithm', 'privacy', 'data protection']
                
                if any(keyword in text for keyword in ai_keywords) and href.startswith('/blog/'):
                    full_url = urljoin("https://fpf.org", href)
                    article_links.append({
                        "url": full_url,
                        "title": link.get_text(strip=True)
                    })
            
            # Limit to most recent 5 articles
            for doc_info in article_links[:5]:
                result = await self._fetch_url(doc_info["url"])
                
                if result.success and result.metadata:
                    result.metadata.update({
                        "document_title": doc_info["title"],
                        "source_type": "privacy_advocacy",
                        "document_category": "blog_post",
                        "discovered_via": "blog_scraping"
                    })
                
                results.append(result)
        
        except Exception as e:
            self.logger.error("Failed to scrape FPF latest publications", error=str(e))
        
        return results
