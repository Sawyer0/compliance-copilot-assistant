"""Base HTML parsing strategy interface."""

from abc import ABC, abstractmethod
from typing import Dict, Union, Optional

from parsers.base_parser import ParseResult


class BaseHTMLStrategy(ABC):
    """Abstract base class for HTML parsing strategies."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    @abstractmethod
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse HTML content using this strategy."""
        pass
    
    @abstractmethod
    def can_handle(self, content: Union[bytes, str], url: Optional[str] = None) -> bool:
        """Check if this strategy can handle the given content/URL."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get strategy priority (higher number = higher priority)."""
        pass
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize line breaks
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:  # Skip empty lines
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract structured sections from text."""
        sections = {}
        
        if not text:
            return sections
        
        # Simple section detection based on common patterns
        lines = text.split('\n')
        current_section = "content"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line looks like a header
            if (len(line) < 100 and 
                (line.isupper() or 
                 line.startswith(('Section', 'Chapter', 'Part', 'Article')) or
                 any(marker in line.lower() for marker in ['executive order', 'whereas', 'section']))):
                
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = line.lower().replace(' ', '_')[:50]
                current_content = []
            else:
                current_content.append(line)
        
        # Save final section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections 