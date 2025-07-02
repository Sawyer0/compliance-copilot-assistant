"""Document parsers for different formats."""

from .base_parser import BaseParser, ParseResult
from .html_parser import HTMLParser
from .pdf_parser import PDFParser
from .ocr_fallback import OCRParser

__all__ = [
    "BaseParser",
    "ParseResult",
    "HTMLParser", 
    "PDFParser",
    "OCRParser",
] 