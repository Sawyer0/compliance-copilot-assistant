"""Generic site content extractor for unknown websites."""

from typing import List
from .base_site_extractor import BaseSiteExtractor


class GenericExtractor(BaseSiteExtractor):
    """Generic extractor for unknown websites."""
    
    def can_handle(self, url: str) -> bool:
        """Can handle any URL as fallback."""
        return True
    
    def get_priority(self) -> int:
        """Lowest priority - fallback only."""
        return 10
    
    def get_content_selectors(self) -> List[str]:
        """Generic content selectors."""
        return [
            'main',
            'article', 
            '[role="main"]',
            '.content',
            '.main-content',
            '#content',
            '.post-content',
            '.entry-content'
        ]
    
    async def extract_content(self, page) -> str:
        """Extract content using generic selectors."""
        # Try standard content selectors first
        content = await self._try_selectors(page, self.get_content_selectors(), min_length=500)
        
        if content:
            return content
        
        # Fallback to JavaScript-based extraction with cleanup
        content = await page.evaluate('''() => {
            const selectors = [
                'main', 'article', '[role="main"]', '.content',
                '.main-content', '#content', '.post-content', '.entry-content'
            ];
            
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element && element.innerText.length > 500) {
                    return element.innerText;
                }
            }
            
            // Last resort: clean body content
            const nav = document.querySelector('nav');
            const header = document.querySelector('header');
            const footer = document.querySelector('footer');
            
            if (nav) nav.style.display = 'none';
            if (header) header.style.display = 'none';
            if (footer) footer.style.display = 'none';
            
            return document.body.innerText;
        }''')
        
        return content or "" 