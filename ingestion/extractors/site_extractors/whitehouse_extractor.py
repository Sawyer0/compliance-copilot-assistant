"""White House site-specific content extractor."""

from typing import List
from .base_site_extractor import BaseSiteExtractor


class WhiteHouseExtractor(BaseSiteExtractor):
    """Extractor specifically designed for White House websites."""
    
    def can_handle(self, url: str) -> bool:
        """Check if this is a White House URL."""
        return "whitehouse" in url.lower()
    
    def get_priority(self) -> int:
        """High priority for White House sites."""
        return 90
    
    def get_content_selectors(self) -> List[str]:
        """Content selectors optimized for White House sites."""
        return [
            '.body-content',  # Main body content
            'section.body-content',
            'article .body-content', 
            '.post-content', 
            '.entry-content',
            '[role="main"] .container',
            '.main-content',
            'main section'
        ]
    
    def get_removal_selectors(self) -> List[str]:
        """Elements to remove specific to White House sites."""
        return super().get_removal_selectors() + [
            '.wh-breadcrumbs', '.mobile-overlay', '.overlay-header',
            '.hamburger-control', '.skip-link', '.alert-bar', 
            '.next-prev', '.screen-reader-text', '.mobile-nav-menus',
            '.social-simple'
        ]
    
    async def extract_content(self, page) -> str:
        """Extract content from White House pages."""
        # Remove White House-specific navigation elements
        await self._remove_elements(page, self.get_removal_selectors())
        
        # Try primary content selectors
        content = await self._try_selectors(page, self.get_content_selectors(), min_length=500)
        
        if content and len(content) > 1000:
            return content
        
        # If primary selectors don't work, try more targeted approach
        content = await page.evaluate("""
            () => {
                // Look for the actual article/document content
                const contentSelectors = [
                    'article', 
                    '.topper + section',  // Content after header
                    '.container .row p',  // Paragraphs in main container
                    'main .container'
                ];
                
                for (const selector of contentSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        const text = element.innerText;
                        // Only return if it looks like actual content
                        if (text.length > 1000 && 
                            !text.includes('Menu') && 
                            !text.includes('Navigation') &&
                            !text.includes('Skip to content')) {
                            return text;
                        }
                    }
                }
                
                // Last resort: get body but filter out navigation
                const body = document.body.cloneNode(true);
                const navSelectors = [
                    'nav', 'header', 'footer', '.menu', '.navigation',
                    '.social', '.share', '.breadcrumb', '.site-header'
                ];
                navSelectors.forEach(sel => {
                    body.querySelectorAll(sel).forEach(el => el.remove());
                });
                return body.innerText;
            }
        """)
        
        return content or "" 