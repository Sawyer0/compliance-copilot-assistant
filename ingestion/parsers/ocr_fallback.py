"""OCR fallback parser using pytesseract."""

import time
from io import BytesIO
from typing import Dict, List, Union

import fitz  # PyMuPDF for PDF to image conversion
from PIL import Image
import pytesseract

from .base_parser import BaseParser, ParseResult
from core.config import get_settings
from models.document import DocumentContent


class OCRParser(BaseParser):
    """OCR fallback parser for scanned documents."""
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        
        # Configure tesseract if custom path is specified
        if self.settings.tesseract_cmd != "tesseract":
            pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd
    
    def can_parse(self, content_type: str, file_extension: str) -> bool:
        """Check if OCR is enabled and can handle the content."""
        if not self.settings.ocr_enabled:
            return False
        
        # OCR can handle images and PDFs
        return (
            'pdf' in content_type.lower() or
            'image' in content_type.lower() or
            file_extension.lower() in ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp']
        )
    
    async def parse(self, content: Union[bytes, str], **kwargs) -> ParseResult:
        """Parse content using OCR."""
        start_time = time.time()
        
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        try:
            content_type = kwargs.get('content_type', '')
            
            if 'pdf' in content_type.lower():
                return await self._parse_pdf_with_ocr(content)
            else:
                return await self._parse_image_with_ocr(content)
        
        except Exception as e:
            self.logger.error("OCR parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"OCR parsing failed: {str(e)}",
                parse_time=time.time() - start_time,
                extraction_method="ocr_failed"
            )
    
    async def _parse_pdf_with_ocr(self, content: bytes) -> ParseResult:
        """Parse PDF using OCR by converting pages to images."""
        start_time = time.time()
        
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            
            all_text = ""
            images_processed = 0
            
            for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages for performance
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                
                # OCR the image
                image = Image.open(BytesIO(img_data))
                page_text = pytesseract.image_to_string(image, config='--psm 6')
                
                all_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                images_processed += 1
                
                self.logger.debug(
                    "OCR processed PDF page",
                    page=page_num + 1,
                    text_length=len(page_text)
                )
            
            doc.close()
            
            # Clean and structure the text
            cleaned_text = self._clean_text(all_text)
            sections = self._extract_sections(cleaned_text)
            
            content_obj = DocumentContent(
                raw_text=cleaned_text,
                structured_sections=sections,
                tables=[],  # OCR doesn't preserve table structure
                images=[],
                links=[]
            )
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="ocr_pdf",
                parse_time=time.time() - start_time,
                metadata={
                    "pages_processed": images_processed,
                    "total_pages": len(doc) if 'doc' in locals() else 0,
                    "ocr_engine": "tesseract"
                }
            )
        
        except Exception as e:
            self.logger.error("PDF OCR parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"PDF OCR parsing failed: {str(e)}",
                parse_time=time.time() - start_time,
                extraction_method="ocr_pdf"
            )
    
    async def _parse_image_with_ocr(self, content: bytes) -> ParseResult:
        """Parse image using OCR."""
        start_time = time.time()
        
        try:
            # Open image
            image = Image.open(BytesIO(content))
            
            # Preprocess image for better OCR
            image = self._preprocess_image(image)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            # Get additional OCR data
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidence_scores = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # Clean and structure the text
            cleaned_text = self._clean_text(text)
            sections = self._extract_sections(cleaned_text)
            
            content_obj = DocumentContent(
                raw_text=cleaned_text,
                structured_sections=sections,
                tables=[],
                images=[],
                links=[]
            )
            
            return ParseResult(
                success=True,
                content=content_obj,
                extraction_method="ocr_image",
                parse_time=time.time() - start_time,
                metadata={
                    "image_size": image.size,
                    "average_confidence": avg_confidence,
                    "ocr_engine": "tesseract",
                    "total_words": len(confidence_scores)
                }
            )
        
        except Exception as e:
            self.logger.error("Image OCR parsing failed", error=str(e))
            return ParseResult(
                success=False,
                error_message=f"Image OCR parsing failed: {str(e)}",
                parse_time=time.time() - start_time,
                extraction_method="ocr_image"
            )
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Resize if too small (OCR works better on larger images)
        width, height = image.size
        if width < 1000:
            scale_factor = 1000 / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def check_ocr_availability(self) -> bool:
        """Check if OCR tools are available."""
        try:
            # Test pytesseract
            test_image = Image.new('RGB', (100, 100), color='white')
            pytesseract.image_to_string(test_image)
            return True
        except Exception as e:
            self.logger.warning("OCR not available", error=str(e))
            return False
