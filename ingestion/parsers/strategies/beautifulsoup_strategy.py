"""BeautifulSoup HTML parsing strategy for detailed structure extraction."""

import time
from typing import Union, Optional, List, Dict

from bs4 import BeautifulSoup

from .base_html_strategy import BaseHTMLStrategy
from parsers.base_parser import ParseResult
from models.document import DocumentContent


class BeautifulSoupHTMLStrategy(BaseHTMLStrategy):
    """HTML parsing strategy using BeautifulSoup for detailed structure extraction."""
    
    def can_handle(self, content: Union[bytes, str], url: Optional[str] = None) -> bool:
        """BeautifulSoup can handle any HTML content."""
        return True
    
    def get_priority(self) -> int:
        """Lower priority - fallback when other methods fail."""
        return 50
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse HTML using BeautifulSoup."""
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
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
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            
            extraction_metadata = {
                "title": title.string if title else None,
                "description": meta_description.get('content') if meta_description else None,
                "author": meta_author.get('content') if meta_author else None,
                "keywords": meta_keywords.get('content') if meta_keywords else None,
                "total_tables": len(tables),
                "total_images": len(images),
                "total_links": len(links),
                "extraction_method": "beautifulsoup",
                "content_length": len(cleaned_text)
            }
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="beautifulsoup",
                metadata=extraction_metadata
            )
        
        except Exception as e:
            if self.logger:
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
            
            # Extract headers if present
            headers = []
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    headers.append(th.get_text(strip=True))
            
            # Extract all rows
            for row in table.find_all('tr'):
                cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if cells:  # Only add non-empty rows
                    rows.append(cells)
            
            if rows:
                table_data = {
                    "index": table_index,
                    "rows": len(rows),
                    "cols": max(len(row) for row in rows) if rows else 0,
                    "headers": headers if headers else None,
                    "data": rows[:10]  # First 10 rows only to avoid massive data
                }
                
                # Add table summary
                if len(rows) > 10:
                    table_data["summary"] = f"Table with {len(rows)} rows (showing first 10)"
                
                tables.append(table_data)
        
        return tables
    
    def _extract_links_from_soup(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract links from BeautifulSoup object."""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Skip empty links or javascript
            if not href or href.startswith('javascript:') or not text:
                continue
            
            link_type = "internal" if href.startswith('#') or href.startswith('/') else "external"
            
            links.append({
                "url": href,
                "text": text[:200],  # Limit text length
                "type": link_type,
                "title": link.get('title', ''),
                "target": link.get('target', '')
            })
        
        return links[:100]  # Limit to first 100 links
    
    def _extract_images_from_soup(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract images from BeautifulSoup object."""
        images = []
        
        for img_index, img in enumerate(soup.find_all('img')):
            src = img.get('src', '')
            
            # Skip empty src or data URIs (too long)
            if not src or src.startswith('data:'):
                continue
            
            images.append({
                "index": img_index,
                "src": src,
                "alt": img.get('alt', ''),
                "title": img.get('title', ''),
                "width": img.get('width'),
                "height": img.get('height'),
                "class": ' '.join(img.get('class', [])) if img.get('class') else ''
            })
        
        return images[:50]  # Limit to first 50 images 