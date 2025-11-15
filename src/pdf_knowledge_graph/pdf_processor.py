"""PDF processing module with OCR fallback support.

This module handles extraction of text from PDF files, supporting both
direct text extraction and OCR for scanned documents.
"""

import io
from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

from .logger import setup_logger
from .models import PDFMetadata

logger = setup_logger(__name__)


class PDFProcessor:
    """Process PDF files to extract text content."""

    def __init__(self, min_text_threshold: int = 100) -> None:
        """Initialize PDF processor.

        Args:
            min_text_threshold: Minimum characters to consider PDF as text-based
        """
        self.min_text_threshold = min_text_threshold
        logger.info("PDFProcessor initialized")

    def extract_text(self, pdf_path: Path) -> Tuple[str, PDFMetadata]:
        """Extract text from PDF file with OCR fallback.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, metadata)

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF cannot be processed
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Processing PDF: {pdf_path.name}")

        # Try direct text extraction first
        text, num_pages = self._extract_text_direct(pdf_path)

        extraction_method = "direct"
        has_text = len(text.strip()) >= self.min_text_threshold

        # Fall back to OCR if not enough text found
        if not has_text:
            logger.info(
                f"Insufficient text extracted ({len(text)} chars), falling back to OCR"
            )
            text = self._extract_text_ocr(pdf_path)
            extraction_method = "ocr"
            has_text = len(text.strip()) > 0

        if not has_text:
            raise ValueError("No text could be extracted from PDF")

        metadata = PDFMetadata(
            filename=pdf_path.name,
            num_pages=num_pages,
            text_length=len(text),
            has_text=has_text,
            extraction_method=extraction_method,
        )

        logger.info(
            f"Extracted {len(text)} characters from {num_pages} pages "
            f"using {extraction_method} method"
        )

        return text, metadata

    def _extract_text_direct(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract text directly from PDF using PyMuPDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (text, number_of_pages)
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())

            doc.close()
            return "\n".join(text_parts), len(doc)

        except Exception as e:
            logger.error(f"Error extracting text directly: {e}")
            return "", 0

    def _extract_text_ocr(self, pdf_path: Path) -> str:
        """Extract text from PDF using OCR (Tesseract).

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            logger.info("Converting PDF to images for OCR")
            # Convert PDF to images
            images = convert_from_path(str(pdf_path))

            text_parts = []
            for i, image in enumerate(images):
                logger.debug(f"Processing page {i + 1}/{len(images)} with OCR")
                # Perform OCR on each page
                text = pytesseract.image_to_string(image)
                text_parts.append(text)

            ocr_text = "\n".join(text_parts)
            logger.info(f"OCR completed: extracted {len(ocr_text)} characters")
            return ocr_text

        except Exception as e:
            logger.error(f"Error during OCR processing: {e}")
            return ""

    def validate_pdf(self, pdf_path: Path) -> bool:
        """Validate that file is a readable PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if valid PDF, False otherwise
        """
        try:
            doc = fitz.open(pdf_path)
            is_valid = doc.page_count > 0
            doc.close()
            return is_valid
        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            return False


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, PDFMetadata]:
    """Convenience function to extract text from PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Tuple of (extracted_text, metadata)
    """
    processor = PDFProcessor()
    return processor.extract_text(pdf_path)
