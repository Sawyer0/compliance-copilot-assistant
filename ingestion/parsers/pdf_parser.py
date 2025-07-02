"""PDF parser implementation using PyMuPDF and pdfplumber."""

import time
from io import BytesIO
from typing import Dict, List, Union

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

from .base_parser import BaseParser, ParseResult
from ..models.document import DocumentContent


class PDFParser(BaseParser):
    """Parser for PDF documents."""
    
    def can_parse(self, content_type: str, file_extension: str) -> bool:
        """Check if this parser can handle PDF files."""
        return (
            'pdf' in content_type.lower() or 
            file_extension.lower() == 'pdf'
        )
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse PDF content using multiple methods."""
        start_time = time.time()
        
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        try:
            # Try PyMuPDF first (faster, better for text-based PDFs)
            result = await self._parse_with_pymupdf(content)
            
            if result.success and result.content:
                quality_score = self._calculate_quality_score(
                    result.content.raw_text, 
                    "pdf_text"
                )
                
                # If quality is low, try pdfplumber
                if quality_score < 0.5:
                    self.logger.info("Low quality text from PyMuPDF, trying pdfplumber")
                    pdfplumber_result = await self._parse_with_pdfplumber(content)
                    
                    if pdfplumber_result.success and pdfplumber_result.content:
                        pdfplumber_quality = self._calculate_quality_score(
                            pdfplumber_result.content.raw_text,
                            "pdf_text"
                        )
                        
                        if pdfplumber_quality > quality_score:
                            result = pdfplumber_result
                            quality_score = pdfplumber_quality
                
                result.quality_score = quality_score
                result.parse_time = time.time() - start_time
                
                return result
            
            # If PyMuPDF fails, try pdfplumber
            self.logger.info("PyMuPDF failed, trying pdfplumber")
            result = await self._parse_with_pdfplumber(content)
            
            if result.success:
                result.quality_score = self._calculate_quality_score(
                    result.content.raw_text if result.content else "",
                    "pdf_text"
                )
                result.parse_time = time.time() - start_time
                
                return result
        
        except Exception as e:
            self.logger.error("PDF parsing failed", error=str(e))
        
        # Return failure result
        return ParseResult(
            success=False,
            error_message="Failed to parse PDF with all methods",
            parse_time=time.time() - start_time,
            extraction_method="pdf_failed"
        )
    
    async def _parse_with_pymupdf(self, content: bytes) -> ParseResult:
        """Parse PDF using PyMuPDF."""
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            
            text_content = ""
            sections = []
            images = []
            tables = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text
                page_text = page.get_text()
                text_content += page_text + "\n"
                
                # Extract images (metadata only for now)
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    images.append({
                        "page": page_num + 1,
                        "index": img_index,
                        "width": img[2] if len(img) > 2 else None,
                        "height": img[3] if len(img) > 3 else None
                    })
                
                # Extract tables (basic detection)
                tables_on_page = page.find_tables()
                for table_index, table in enumerate(tables_on_page):
                    try:
                        table_data = table.extract()
                        tables.append({
                            "page": page_num + 1,
                            "index": table_index,
                            "rows": len(table_data) if table_data else 0,
                            "cols": len(table_data[0]) if table_data and table_data[0] else 0,
                            "data": table_data[:5] if table_data else []  # First 5 rows only
                        })
                    except Exception as e:
                        self.logger.warning(
                            "Failed to extract table",
                            page=page_num + 1,
                            table_index=table_index,
                            error=str(e)
                        )
            
            doc.close()
            
            # Clean and structure the text
            cleaned_text = self._clean_text(text_content)
            sections = self._extract_sections(cleaned_text)
            links = self._extract_links(cleaned_text)
            
            content_obj = DocumentContent(
                raw_text=cleaned_text,
                structured_sections=sections,
                tables=tables,
                images=images,
                links=links
            )
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="pymupdf",
                metadata={
                    "total_pages": len(doc) if 'doc' in locals() else 0,
                    "total_images": len(images),
                    "total_tables": len(tables)
                }
            )
        
        except Exception as e:
            self.logger.error("PyMuPDF parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"PyMuPDF parsing failed: {str(e)}",
                extraction_method="pymupdf"
            )
    
    async def _parse_with_pdfplumber(self, content: bytes) -> ParseResult:
        """Parse PDF using pdfplumber."""
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                text_content = ""
                tables = []
                images = []
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                    
                    # Extract tables
                    page_tables = page.extract_tables()
                    for table_index, table in enumerate(page_tables):
                        if table:
                            tables.append({
                                "page": page_num + 1,
                                "index": table_index,
                                "rows": len(table),
                                "cols": len(table[0]) if table else 0,
                                "data": table[:5]  # First 5 rows only
                            })
                    
                    # Images (basic metadata)
                    if hasattr(page, 'images'):
                        for img_index, img in enumerate(page.images):
                            images.append({
                                "page": page_num + 1,
                                "index": img_index,
                                "width": img.get('width'),
                                "height": img.get('height')
                            })
                
                # Clean and structure the text
                cleaned_text = self._clean_text(text_content)
                sections = self._extract_sections(cleaned_text)
                links = self._extract_links(cleaned_text)
                
                content_obj = DocumentContent(
                    raw_text=cleaned_text,
                    structured_sections=sections,
                    tables=tables,
                    images=images,
                    links=links
                )
                
                return ParseResult(
                    success=True,
                    content=content_obj,
                    extraction_method="pdfplumber",
                    metadata={
                        "total_pages": len(pdf.pages),
                        "total_images": len(images),
                        "total_tables": len(tables)
                    }
                )
        
        except Exception as e:
            self.logger.error("pdfplumber parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"pdfplumber parsing failed: {str(e)}",
                extraction_method="pdfplumber"
            )
