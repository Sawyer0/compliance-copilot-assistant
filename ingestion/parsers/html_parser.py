"""HTML parser implementation using trafilatura and markdownify."""

import time
from typing import Dict, List, Union

import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

from .base_parser import BaseParser, ParseResult
from ..models.document import DocumentContent


class HTMLParser(BaseParser):
    """Parser for HTML documents."""
    
    def can_parse(self, content_type: str, file_extension: str) -> bool:
        """Check if this parser can handle HTML files."""
        return (
            'html' in content_type.lower() or 
            file_extension.lower() in ['html', 'htm']
        )
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse HTML content using multiple methods."""
        start_time = time.time()
        
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        
        try:
            # Try trafilatura first (best for article extraction)
            result = await self._parse_with_trafilatura(content)
            
            if result.success and result.content:
                quality_score = self._calculate_quality_score(
                    result.content.raw_text, 
                    "html_parsing"
                )
                
                # If quality is low, try BeautifulSoup
                if quality_score < 0.6:
                    self.logger.info("Low quality text from trafilatura, trying BeautifulSoup")
                    bs_result = await self._parse_with_beautifulsoup(content)
                    
                    if bs_result.success and bs_result.content:
                        bs_quality = self._calculate_quality_score(
                            bs_result.content.raw_text,
                            "html_parsing"
                        )
                        
                        if bs_quality > quality_score:
                            result = bs_result
                            quality_score = bs_quality
                
                result.quality_score = quality_score
                result.parse_time = time.time() - start_time
                
                return result
            
            # If trafilatura fails, try BeautifulSoup
            self.logger.info("Trafilatura failed, trying BeautifulSoup")
            result = await self._parse_with_beautifulsoup(content)
            
            if result.success:
                result.quality_score = self._calculate_quality_score(
                    result.content.raw_text if result.content else "",
                    "html_parsing"
                )
                result.parse_time = time.time() - start_time
                
                return result
        
        except Exception as e:
            self.logger.error("HTML parsing failed", error=str(e))
        
        # Return failure result
        return ParseResult(
            success=False,
            error_message="Failed to parse HTML with all methods",
            parse_time=time.time() - start_time,
            extraction_method="html_failed"
        )
    
    async def _parse_with_trafilatura(self, content: str) -> ParseResult:
        """Parse HTML using trafilatura."""
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
            
            # Extract with comments and links
            extracted_with_metadata = trafilatura.extract(
                content,
                include_comments=False,
                include_links=True,
                include_images=True
            )
            
            # Clean and structure the text
            cleaned_text = self._clean_text(extracted_text)
            sections = self._extract_sections(cleaned_text)
            links = self._extract_links_from_html(content)
            
            content_obj = DocumentContent(
                raw_text=cleaned_text,
                structured_sections=sections,
                tables=[],  # trafilatura doesn't extract table structure
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
                }
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="trafilatura",
                metadata=extraction_metadata
            )
        
        except Exception as e:
            self.logger.error("Trafilatura parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"Trafilatura parsing failed: {str(e)}",
                extraction_method="trafilatura"
            )
    
    async def _parse_with_beautifulsoup(self, content: str) -> ParseResult:
        """Parse HTML using BeautifulSoup."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Extract text
            text_content = soup.get_text()
            
            # Extract structured data
            tables = self._extract_tables_from_soup(soup)
            links = self._extract_links_from_soup(soup)
            images = self._extract_images_from_soup(soup)
            
            # Clean and structure the text
            cleaned_text = self._clean_text(text_content)
            sections = self._extract_sections(cleaned_text)
            
            content_obj = DocumentContent(
                raw_text=cleaned_text,
                structured_sections=sections,
                tables=tables,
                images=images,
                links=links
            )
            
            # Extract metadata from HTML
            title = soup.find('title')
            meta_description = soup.find('meta', attrs={'name': 'description'})
            meta_author = soup.find('meta', attrs={'name': 'author'})
            
            extraction_metadata = {
                "title": title.string if title else None,
                "description": meta_description.get('content') if meta_description else None,
                "author": meta_author.get('content') if meta_author else None,
                "total_tables": len(tables),
                "total_images": len(images),
                "total_links": len(links)
            }
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="beautifulsoup",
                metadata=extraction_metadata
            )
        
        except Exception as e:
            self.logger.error("BeautifulSoup parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"BeautifulSoup parsing failed: {str(e)}",
                extraction_method="beautifulsoup"
            )
    
    def _extract_tables_from_soup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract tables from BeautifulSoup object."""
        tables = []
        
        for table_index, table in enumerate(soup.find_all('table')):
            rows = []
            for row in table.find_all('tr'):
                cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if cells:  # Only add non-empty rows
                    rows.append(cells)
            
            if rows:
                tables.append({
                    "index": table_index,
                    "rows": len(rows),
                    "cols": max(len(row) for row in rows) if rows else 0,
                    "data": rows[:10]  # First 10 rows only
                })
        
        return tables
    
    def _extract_links_from_soup(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract links from BeautifulSoup object."""
        links = []
        
        for link in soup.find_all('a', href=True):
            links.append({
                "url": link['href'],
                "text": link.get_text(strip=True),
                "type": "internal" if link['href'].startswith('#') else "external"
            })
        
        return links
    
    def _extract_images_from_soup(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract images from BeautifulSoup object."""
        images = []
        
        for img_index, img in enumerate(soup.find_all('img')):
            images.append({
                "index": img_index,
                "src": img.get('src', ''),
                "alt": img.get('alt', ''),
                "title": img.get('title', ''),
                "width": img.get('width'),
                "height": img.get('height')
            })
        
        return images
    
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
        
        return links
    
    def _extract_images_from_html(self, content: str) -> List[Dict[str, str]]:
        """Extract images using regex as fallback."""
        import re
        
        images = []
        
        # Extract img tags
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, content, re.IGNORECASE)
        
        for index, src in enumerate(matches):
            images.append({
                "index": index,
                "src": src,
                "alt": "",
                "title": ""
            })
        
        return images
