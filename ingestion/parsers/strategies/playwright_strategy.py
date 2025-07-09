"""Playwright HTML parsing strategy for dynamic content."""

import time
from typing import Union, Optional

from .base_html_strategy import BaseHTMLStrategy
from parsers.base_parser import ParseResult
from models.document import DocumentContent


class PlaywrightHTMLStrategy(BaseHTMLStrategy):
    """HTML parsing strategy using Playwright for dynamic content."""
    
    def __init__(self, logger=None):
        super().__init__(logger)
        self.site_extractors = {
            'whitehouse.gov': self._extract_whitehouse_content,
            'eur-lex.europa.eu': self._extract_eurlex_content,
            'edpb.europa.eu': self._extract_edpb_content,
            'fpf.org': self._extract_fpf_content,
        }
    
    def can_handle(self, content: Union[bytes, str], url: Optional[str] = None) -> bool:
        """Playwright is best for dynamic content when URL is available."""
        return url is not None
    
    def get_priority(self) -> int:
        """High priority for URLs with dynamic content."""
        return 90
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse HTML using Playwright for dynamic content extraction."""
        url = kwargs.get('url')
        if not url:
            return ParseResult(
                success=False,
                error_message="URL required for Playwright parsing",
                extraction_method="playwright"
            )
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to the page
                await page.goto(url, wait_until='networkidle')
                
                # Wait for dynamic content
                await page.wait_for_timeout(2000)
                
                # Extract content using site-specific logic
                text_content, metadata = await self._extract_content_by_site(page, url)
                
                await browser.close()
                
                if not text_content or len(text_content.strip()) < 100:
                    return ParseResult(
                        success=False,
                        error_message="No substantial content extracted by Playwright",
                        extraction_method="playwright"
                    )
                
                # Clean and structure the text
                cleaned_text = self._clean_text(text_content)
                sections = self._extract_sections(cleaned_text)
                
                content_obj = DocumentContent(
                    raw_text=cleaned_text,
                    structured_sections=sections,
                    tables=[],
                    images=[],
                    links=[]
                )
                
                extraction_metadata = {
                    **metadata,
                    "url": url,
                    "extraction_method": "playwright",
                    "content_length": len(cleaned_text)
                }
                
                return ParseResult(
                    success=True,
                    content=content_obj,
                    extraction_method="playwright",
                    metadata=extraction_metadata
                )
                
        except Exception as e:
            if self.logger:
                self.logger.error("Playwright parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"Playwright parsing failed: {str(e)}",
                extraction_method="playwright"
            )
    
    async def _extract_content_by_site(self, page, url: str) -> tuple[str, dict]:
        """Extract content using site-specific logic."""
        # Determine site and use appropriate extractor
        for domain, extractor in self.site_extractors.items():
            if domain in url.lower():
                return await extractor(page)
        
        # Default generic extraction
        return await self._extract_generic_content(page)
    
    async def _extract_whitehouse_content(self, page) -> tuple[str, dict]:
        """Extract content from White House sites."""
        # Remove navigation and non-content elements first
        await page.evaluate("""
            () => {
                const elementsToRemove = [
                    'nav', 'header', 'footer', '.nav', '.navigation', 
                    '.menu', '.sidebar', '.social', '.share', '.social-simple',
                    '.breadcrumb', '.tag', '.category', '.author',
                    '.site-header', '.mobile-menu', '.mobile-overlay',
                    '.overlay-header', '.hamburger-control', '.skip-link',
                    '.alert-bar', '.next-prev', '.wh-breadcrumbs'
                ];
                
                elementsToRemove.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => el.remove());
                });
            }
        """)
        
        # Try specific content selectors for White House
        content_selectors = [
            'section.body-content',
            '.body-content', 
            'article .content',
            '.post-content',
            '.entry-content', 
            '[role="main"]',
            '.main-content',
            'main'
        ]
        
        text_content = ""
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    # Check if this looks like actual policy content
                    if len(content) > 1000 and self._is_policy_content(content):
                        text_content = content
                        break
            except Exception:
                continue
        
        # If no good content found, try filtered body
        if not text_content:
            text_content = await page.inner_text('body')
        
        # Extract metadata
        title = await page.title()
        
        return text_content, {"title": title, "site": "whitehouse.gov"}
    
    async def _extract_eurlex_content(self, page) -> tuple[str, dict]:
        """Extract content from EU Lex documents."""
        content_selectors = [
            '#document',
            '.eli-document',
            '.DocumentContent',
            '#content',
            '.eli-main-content'
        ]
        
        text_content = ""
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content) > 1000:
                        text_content = content
                        break
            except Exception:
                continue
        
        title = await page.title()
        return text_content, {"title": title, "site": "eur-lex.europa.eu"}
    
    async def _extract_edpb_content(self, page) -> tuple[str, dict]:
        """Extract content from EDPB sites."""
        content_selectors = [
            '.field-name-body',
            '.content',
            'article',
            '.main-content',
            '.page-content'
        ]
        
        text_content = ""
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content) > 500:
                        text_content = content
                        break
            except Exception:
                continue
        
        title = await page.title()
        return text_content, {"title": title, "site": "edpb.europa.eu"}
    
    async def _extract_fpf_content(self, page) -> tuple[str, dict]:
        """Extract content from Future of Privacy Forum."""
        content_selectors = [
            '.entry-content',
            '.post-content',
            'article .content',
            '.main',
            '.main-content'
        ]
        
        text_content = ""
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content) > 300:
                        text_content = content
                        break
            except Exception:
                continue
        
        title = await page.title()
        return text_content, {"title": title, "site": "fpf.org"}
    
    async def _extract_generic_content(self, page) -> tuple[str, dict]:
        """Generic content extraction for unknown sites."""
        text_content = await page.evaluate('''() => {
            // Try to find main content areas
            const selectors = [
                'main',
                'article', 
                '[role="main"]',
                '.content',
                '.main-content',
                '#content',
                '.post-content',
                '.entry-content'
            ];
            
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element && element.innerText.length > 500) {
                    return element.innerText;
                }
            }
            
            // Fallback to body, but try to exclude navigation
            const nav = document.querySelector('nav');
            const header = document.querySelector('header');
            const footer = document.querySelector('footer');
            
            if (nav) nav.style.display = 'none';
            if (header) header.style.display = 'none';
            if (footer) footer.style.display = 'none';
            
            return document.body.innerText;
        }''')
        
        title = await page.title()
        return text_content, {"title": title, "site": "generic"}
    
    def _is_policy_content(self, content: str) -> bool:
        """Check if content looks like policy/compliance content."""
        policy_indicators = [
            'executive order', 'section', 'whereas', 'shall', 'authority vested',
            'hereby ordered', 'artificial intelligence', 'compliance', 'regulation',
            'pursuant to', 'administration', 'federal', 'policy', 'implementation'
        ]
        
        content_lower = content.lower()
        return sum(1 for indicator in policy_indicators if indicator in content_lower) >= 3 