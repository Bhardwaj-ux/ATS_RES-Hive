# FILEPATH: apps/jdimport/services/conversion.py
import io

import fitz  # PyMuPDF
import mammoth
from markdownify import markdownify as html_to_markdown


class ConversionError(Exception):
    pass


def _pdf_bytes_to_markdown(pdf_bytes):
    """
    PDF -> Markdown directly via PyMuPDF text extraction.
    (Avoids pdf2docx/opencv/numpy, which blow past Vercel's 225MB bundle limit.)
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ConversionError(f"Failed to open PDF: {exc}") from exc

    lines = []
    try:
        for page in doc:
            text = page.get_text("text")
            if text:
                lines.append(text)
    finally:
        doc.close()

    raw_text = "\n\n".join(lines).strip()
    if not raw_text:
        raise ConversionError("No readable text was found in this PDF.")

    return raw_text


def _docx_bytes_to_markdown(docx_bytes):
    """DOCX -> HTML (mammoth) -> Markdown (markdownify)."""
    try:
        result = mammoth.convert_to_html(io.BytesIO(docx_bytes))
    except Exception as exc:
        raise ConversionError(f"Failed to read DOCX content: {exc}") from exc

    html = result.value
    if not html or not html.strip():
        raise ConversionError("No readable text was found in this document.")

    markdown_text = html_to_markdown(
        html, heading_style="ATX", bullets="-", strong_em_symbol="*"
    )
    return markdown_text.strip()


def convert_pdf_to_markdown(pdf_file):
    """Public entrypoint kept for backward compatibility with views.py."""
    pdf_file.seek(0)
    pdf_bytes = pdf_file.read()
    if not pdf_bytes:
        raise ConversionError("Uploaded PDF file is empty.")
    return _pdf_bytes_to_markdown(pdf_bytes)


def convert_docx_to_markdown(docx_file):
    docx_file.seek(0)
    docx_bytes = docx_file.read()
    if not docx_bytes:
        raise ConversionError("Uploaded DOCX file is empty.")
    return _docx_bytes_to_markdown(docx_bytes)
