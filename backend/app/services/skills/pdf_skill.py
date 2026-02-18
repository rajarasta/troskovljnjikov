"""
PDF Processing Skill - Extract and analyze PDF documents.

Provides tools for:
- Extracting text from PDFs
- Extracting tables from PDFs
- Getting PDF metadata
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


def extract_pdf_text(file_path: str, page_range: Optional[tuple[int, int]] = None) -> dict:
    """
    Extract text from a PDF file.

    Args:
        file_path: Path to PDF file
        page_range: Optional (start_page, end_page) tuple (0-indexed)

    Returns:
        Dictionary with extracted text and metadata
    """
    if not HAS_PDFPLUMBER:
        return {"error": "pdfplumber not installed. Install with: pip install pdfplumber"}

    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            start = page_range[0] if page_range else 0
            end = page_range[1] if page_range else total_pages

            text_by_page = {}
            for i in range(start, min(end, total_pages)):
                page = pdf.pages[i]
                text_by_page[f"page_{i+1}"] = page.extract_text() or ""

            return {
                "file": str(path),
                "total_pages": total_pages,
                "extracted_pages": end - start,
                "text": text_by_page,
                "success": True,
            }
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return {"error": str(e), "success": False}


def extract_pdf_tables(file_path: str) -> dict:
    """
    Extract tables from a PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Dictionary with extracted tables
    """
    if not HAS_PDFPLUMBER:
        return {"error": "pdfplumber not installed"}

    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        with pdfplumber.open(path) as pdf:
            tables_by_page = {}
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    tables_by_page[f"page_{i+1}"] = tables

            return {
                "file": str(path),
                "pages_with_tables": len(tables_by_page),
                "tables": tables_by_page,
                "success": True,
            }
    except Exception as e:
        logger.error(f"Error extracting PDF tables: {e}")
        return {"error": str(e), "success": False}


def get_pdf_metadata(file_path: str) -> dict:
    """
    Get metadata from a PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Dictionary with PDF metadata
    """
    if not HAS_PYPDF:
        return {"error": "PyPDF2 not installed. Install with: pip install PyPDF2"}

    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        reader = PdfReader(path)
        metadata = reader.metadata

        return {
            "file": str(path),
            "num_pages": len(reader.pages),
            "title": metadata.get("/Title", ""),
            "author": metadata.get("/Author", ""),
            "subject": metadata.get("/Subject", ""),
            "creator": metadata.get("/Creator", ""),
            "producer": metadata.get("/Producer", ""),
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error getting PDF metadata: {e}")
        return {"error": str(e), "success": False}


# Skill registration info
SKILL_INFO = {
    "name": "pdf_extract",
    "description": "Extract text, tables, and metadata from PDF documents",
    "functions": [
        {
            "name": "extract_pdf_text",
            "description": "Extract text from PDF pages",
            "parameters": {
                "file_path": "Path to the PDF file",
                "page_range": "Optional (start_page, end_page) tuple",
            },
        },
        {
            "name": "extract_pdf_tables",
            "description": "Extract tables from PDF pages",
            "parameters": {
                "file_path": "Path to the PDF file",
            },
        },
        {
            "name": "get_pdf_metadata",
            "description": "Get metadata from PDF file",
            "parameters": {
                "file_path": "Path to the PDF file",
            },
        },
    ],
}
