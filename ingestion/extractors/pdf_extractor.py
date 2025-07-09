"""PDF content extraction using PyMuPDF."""

import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts content from PDF documents."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def extract_content(self, url: str, raw_file_path: str) -> str:
        """Extract text content from PDF files."""
        try:
            # Download PDF directly
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Save raw PDF
            with open(raw_file_path, 'wb') as f:
                f.write(response.content)
            
            # Extract text content using PyMuPDF
            import pymupdf as fitz
            doc = fitz.open(raw_file_path)
            text_content = ""
            for page in doc:
                text_content += page.get_text()
            doc.close()
            
            return text_content
            
        except Exception as e:
            logger.error(f"PDF extraction failed for {url}: {e}")
            return "" 