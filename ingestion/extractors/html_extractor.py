"""HTML content extraction using site-specific extractors."""

import requests
import logging
from typing import List

from .site_extractors import (
    WhiteHouseExtractor,
    GenericExtractor
)

logger = logging.getLogger(__name__)


class HTMLExtractor:
    """Extracts content from HTML documents using site-specific strategies."""
    
    def __init__(self, timeout: int = 30, wait_time: int = 2000):
        self.timeout = timeout
        self.wait_time = wait_time
        
        # Initialize available site extractors
        self.extractors = [
            WhiteHouseExtractor(),
            GenericExtractor()  # Always keep as fallback
        ]
        
        # Sort by priority (highest first)
        self.extractors.sort(key=lambda e: e.get_priority(), reverse=True)
    
    async def extract_content(self, url: str, raw_file_path: str) -> str:
        """Extract content from HTML using site-specific strategies."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to the page
                await page.goto(url, wait_until='networkidle')
                await page.wait_for_timeout(self.wait_time)
                
                # Extract content using the best available extractor
                text_content = await self._extract_with_best_extractor(page, url)
                
                # Get the full page HTML for raw storage
                page_html = await page.content()
                await browser.close()
                
                # Save raw HTML
                with open(raw_file_path, 'w', encoding='utf-8') as f:
                    f.write(page_html)
                
                return text_content
                
        except Exception as e:
            logger.error(f"Playwright extraction failed for {url}: {e}")
            # Fallback to requests
            return await self._fallback_extraction(url, raw_file_path)
    
    async def _extract_with_best_extractor(self, page, url: str) -> str:
        """Use the best available extractor for the given URL."""
        for extractor in self.extractors:
            if extractor.can_handle(url):
                logger.info(f"Using {extractor.__class__.__name__} for {url}")
                
                try:
                    content = await extractor.extract_content(page)
                    if content and len(content) > 100:  # Minimum content length
                        return content
                except Exception as e:
                    logger.warning(f"Extractor {extractor.__class__.__name__} failed: {e}")
                    continue
        
        # If all extractors fail, return empty string
        logger.error(f"All extractors failed for {url}")
        return ""
    
    async def _fallback_extraction(self, url: str, raw_file_path: str) -> str:
        """Fallback to simple requests extraction."""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            with open(raw_file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return response.text
        except Exception as e:
            logger.error(f"Fallback extraction failed for {url}: {e}")
            return ""
    
    def add_extractor(self, extractor):
        """Add a new site extractor and re-sort by priority."""
        self.extractors.append(extractor)
        self.extractors.sort(key=lambda e: e.get_priority(), reverse=True)
    
    def get_available_extractors(self) -> List[str]:
        """Get list of available extractor class names."""
        return [extractor.__class__.__name__ for extractor in self.extractors] 