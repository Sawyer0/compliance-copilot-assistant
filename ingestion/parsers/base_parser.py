"""Base parser class for document processing."""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from core.logging import get_logger
from models.document import DocumentContent, DocumentFormat

logger = get_logger(__name__)


class ParseResult(BaseModel):
    """Result of a parse operation."""
    success: bool
    content: Optional[DocumentContent] = None
    error_message: Optional[str] = None
    parse_time: float = 0.0
    quality_score: Optional[float] = None
    extraction_method: str = "unknown"
    metadata: Dict[str, any] = {}
    
    class Config:
        arbitrary_types_allowed = True


class BaseParser(ABC):
    """Base class for document parsers."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse document content."""
        pass
    
    @abstractmethod
    def can_parse(self, content_type: str, file_extension: str) -> bool:
        """Check if this parser can handle the given content type."""
        pass
    
    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Extract structured sections from text."""
        sections = []
        current_section = {"title": "", "content": ""}
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Simple heuristic for section headers
            if self._is_section_header(line):
                # Save previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                current_section = {
                    "title": line,
                    "content": ""
                }
            else:
                current_section["content"] += line + "\n"
        
        # Add the last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _is_section_header(self, line: str) -> bool:
        """Determine if a line is likely a section header."""
        if not line:
            return False
        
        # Common section header patterns
        header_patterns = [
            lambda l: l.isupper() and len(l) < 100,  # ALL CAPS short lines
            lambda l: l.startswith(tuple('123456789')) and '.' in l[:10],  # Numbered sections
            lambda l: l.startswith('#'),  # Markdown headers
            lambda l: len(l) < 100 and l.endswith(':'),  # Lines ending with colon
            lambda l: l.startswith(('Article', 'Section', 'Chapter', 'Part')),  # Legal sections
        ]
        
        return any(pattern(line) for pattern in header_patterns)
    
    def _extract_links(self, text: str) -> List[Dict[str, str]]:
        """Extract links from text."""
        import re
        
        links = []
        
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            links.append({
                "url": url,
                "text": url,
                "type": "url"
            })
        
        return links
    
    def _calculate_quality_score(
        self, 
        text: str, 
        extraction_method: str
    ) -> float:
        """Calculate a quality score for the extracted text."""
        if not text:
            return 0.0
        
        score = 1.0
        
        # Penalize very short texts
        if len(text) < 100:
            score *= 0.5
        
        # Reward structured content
        if len(text.split('\n')) > 10:
            score *= 1.1
        
        # Penalize excessive special characters (OCR artifacts)
        special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
        if special_char_ratio > 0.3:
            score *= 0.7
        
        # Adjust based on extraction method
        method_scores = {
            "direct_text": 1.0,
            "html_parsing": 0.9,
            "pdf_text": 0.8,
            "ocr": 0.6,
            "fallback": 0.4
        }
        
        score *= method_scores.get(extraction_method, 0.5)
        
        return min(score, 1.0)
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Reduce multiple newlines
        text = re.sub(r' +', ' ', text)  # Reduce multiple spaces
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\.,!?;:()\[\]{}"\'-]', '', text)
        
        return text.strip()
    
    async def validate_content(self, content: DocumentContent) -> bool:
        """Validate parsed content."""
        if not content.raw_text or len(content.raw_text.strip()) < 10:
            return False
        
        # Check for reasonable text-to-noise ratio
        text = content.raw_text
        word_count = len(text.split())
        
        if word_count < 5:
            return False
        
        return True 