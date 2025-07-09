"""Base site extractor interface."""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseSiteExtractor(ABC):
    """Abstract base class for site-specific content extractors."""
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get extractor priority (higher = more preferred)."""
        pass
    
    @abstractmethod
    async def extract_content(self, page) -> str:
        """Extract content from the page using site-specific logic."""
        pass
    
    def get_content_selectors(self) -> List[str]:
        """Get content selectors for this site."""
        return []
    
    def get_removal_selectors(self) -> List[str]:
        """Get selectors for elements to remove before extraction."""
        return [
            'nav', 'header', 'footer', '.nav', '.navigation', 
            '.menu', '.sidebar', '.social', '.share',
            '.breadcrumb', '.tag', '.category', '.author',
            'script', 'style', '[aria-hidden="true"]'
        ]
    
    async def _try_selectors(self, page, selectors: List[str], min_length: int = 500) -> Optional[str]:
        """Try a list of selectors and return content from the first successful one."""
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content) >= min_length:
                        return content
            except Exception:
                continue
        return None
    
    async def _remove_elements(self, page, selectors: List[str]):
        """Remove elements matching the given selectors."""
        if not selectors:
            return
        
        selector_list = "', '".join(selectors)
        await page.evaluate(f"""
            () => {{
                const selectors = ['{selector_list}'];
                selectors.forEach(selector => {{
                    document.querySelectorAll(selector).forEach(el => el.remove());
                }});
            }}
        """) 