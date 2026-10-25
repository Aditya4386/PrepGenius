"""
pdf_parser.py — Extract text from uploaded PDF bytes.

Responsibilities:
- Validate the file is actually a PDF (check magic bytes)
- Validate file size
- Extract and return plain text using PyMuPDF
- Detect scanned-only PDFs (no extractable text)

Does NOT save anything to disk. Works entirely with bytes in memory.
"""

import pymupdf as fitz

PDF_MAGIC_BYTES = b"%PDF"
MIN_MEANINGFUL_TEXT_LENGTH = 50


class PDFParseError(Exception):
    """Raised when the PDF cannot be parsed for a known reason."""
    pass


def validate_and_extract_text(file_bytes: bytes, max_size_bytes: int) -> str:
    """
    Validate the uploaded bytes and extract text.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        max_size_bytes: Maximum allowed file size (from settings).

    Returns:
        Extracted plain text from the PDF.

    Raises:
        PDFParseError: If the file is invalid, too large, empty, or scanned.
    """
    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise PDFParseError(f"File exceeds the {max_mb:.0f} MB size limit.")

    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        raise PDFParseError("The uploaded file is not a valid PDF.")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        raise PDFParseError("The PDF file is malformed and cannot be opened.")

    if doc.page_count == 0:
        doc.close()
        raise PDFParseError("The PDF has no pages.")

    all_text_parts = []
    for page in doc:
        page_text = page.get_text()
        if page_text:
            all_text_parts.append(page_text.strip())

    doc.close()

    full_text = "\n\n".join(all_text_parts).strip()

    if len(full_text) < MIN_MEANINGFUL_TEXT_LENGTH:
        raise PDFParseError(
            "No readable text could be extracted from this PDF. "
            "It may be a scanned document. OCR is not supported in this version."
        )

    return full_text