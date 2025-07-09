"""Trafilatura HTML parsing strategy for article extraction."""

import time
from typing import Union, Optional, List, Dict

import trafilatura

from .base_html_strategy import BaseHTMLStrategy
from parsers.base_parser import ParseResult
from models.document import DocumentContent


class TrafilaturaHTMLStrategy(BaseHTMLStrategy):
    """HTML parsing strategy using trafilatura for article extraction."""
    
    def can_handle(self, content: Union[bytes, str], url: Optional[str] = None) -> bool:
        """Trafilatura can handle any HTML content."""
        return True
    
    def get_priority(self) -> int:
        """Medium priority - good for static article content."""
        return 70
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse HTML using trafilatura."""
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        
        try:
            # Extract main text content
            extracted_text = trafilatura.extract(content)
            
            if not extracted_text:
                return ParseResult(
                    success=False,
                    error_message="No text content extracted by trafilatura",
                    extraction_method="trafilatura"
                )
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(content)
            
            # Extract with additional features
            extracted_with_features = trafilatura.extract(
                content,
                include_comments=False,
                include_links=True,
                include_images=True,
                include_tables=True
            )
            
            # Clean and structure the text
            cleaned_text = self._clean_text(extracted_text)
            sections = self._extract_sections(cleaned_text)
            links = self._extract_links_from_html(content)
            
            content_obj = DocumentContent(
                raw_text=cleaned_text,
                structured_sections=sections,
                tables=[],  # trafilatura doesn't extract detailed table structure
                images=self._extract_images_from_html(content),
                links=links
            )
            
            extraction_metadata = {}
            if metadata:
                extraction_metadata = {
                    "title": getattr(metadata, 'title', None),
                    "author": getattr(metadata, 'author', None),
                    "date": getattr(metadata, 'date', None),
                    "sitename": getattr(metadata, 'sitename', None),
                    "url": getattr(metadata, 'url', None),
                    "language": getattr(metadata, 'language', None),
                    "extraction_method": "trafilatura",
                    "content_length": len(cleaned_text)
                }
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="trafilatura",
                metadata=extraction_metadata
            )
        
        except Exception as e:
            if self.logger:
                self.logger.error("Trafilatura parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"Trafilatura parsing failed: {str(e)}",
                extraction_method="trafilatura"
            )
    
    def _extract_links_from_html(self, content: str) -> List[Dict[str, str]]:
        """Extract links using regex as fallback."""
        import re
        
        links = []
        
        # Extract href attributes
        href_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
        matches = re.findall(href_pattern, content, re.IGNORECASE)
        
        for url, text in matches:
            links.append({
                "url": url,
                "text": text.strip(),
                "type": "internal" if url.startswith('#') else "external"
            })
        
        return links[:50]  # Limit to first 50 links
    
    def _extract_images_from_html(self, content: str) -> List[Dict[str, str]]:
        """Extract images using regex as fallback."""
        import re
        
        images = []
        
        # Extract img tags with more attributes
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*>'
        matches = re.findall(img_pattern, content, re.IGNORECASE)
        
        for index, match in enumerate(matches):
            src = match[0] if isinstance(match, tuple) else match
            alt = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
            
            images.append({
                "index": index,
                "src": src,
                "alt": alt,
                "title": "",
                "width": None,
                "height": None
            })
        
        return images[:20]  # Limit to first 20 images 