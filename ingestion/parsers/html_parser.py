"""HTML parser implementation using strategy pattern."""

import time
from typing import Dict, List, Union

from .base_parser import BaseParser, ParseResult
from .strategies import (
    PlaywrightHTMLStrategy,
    TrafilaturaHTMLStrategy, 
    BeautifulSoupHTMLStrategy
)


class HTMLParser(BaseParser):
    """Parser for HTML documents using multiple strategies."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize all parsing strategies
        self.strategies = [
            PlaywrightHTMLStrategy(logger=self.logger),
            TrafilaturaHTMLStrategy(logger=self.logger),
            BeautifulSoupHTMLStrategy(logger=self.logger)
        ]
        
        # Sort strategies by priority (highest first)
        self.strategies.sort(key=lambda s: s.get_priority(), reverse=True)
    
    def can_parse(self, content_type: str, file_extension: str) -> bool:
        """Check if this parser can handle HTML files."""
        return (
            'html' in content_type.lower() or 
            file_extension.lower() in ['html', 'htm']
        )
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse HTML content using the best available strategy."""
        start_time = time.time()
        
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        
        url = kwargs.get('url')
        
        # Try each strategy in priority order
        for strategy in self.strategies:
            if strategy.can_handle(content, url):
                self.logger.info(f"Trying strategy: {strategy.__class__.__name__}")
                
                try:
                    result = await strategy.parse(content, **kwargs)
                    
                    if result.success and result.content:
                        # Calculate quality score for the result
                        quality_score = self._calculate_quality_score(
                            result.content.raw_text, 
                            "html_parsing"
                        )
                        
                        # If quality is acceptable or this is our last strategy, use it
                        if quality_score >= 0.6 or strategy == self.strategies[-1]:
                            result.quality_score = quality_score
                            result.parse_time = time.time() - start_time
                            
                            self.logger.info(
                                f"HTML parsing successful with {strategy.__class__.__name__}",
                                quality_score=quality_score,
                                content_length=len(result.content.raw_text)
                            )
                            
                            return result
                        else:
                            self.logger.info(
                                f"Quality too low ({quality_score:.2f}) with {strategy.__class__.__name__}, trying next strategy"
                            )
                            continue
                    
                except Exception as e:
                    self.logger.warning(
                        f"Strategy {strategy.__class__.__name__} failed: {str(e)}"
                    )
                    continue
        
        # If all strategies failed
        self.logger.error("All HTML parsing strategies failed")
        return ParseResult(
            success=False,
            error_message="Failed to parse HTML with all available strategies",
            parse_time=time.time() - start_time,
            extraction_method="html_failed"
        )
