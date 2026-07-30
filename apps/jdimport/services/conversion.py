# FILEPATH: apps/jdimport/services/conversion.py
import io
import tempfile
import os
import mammoth
from markdownify import markdownify as html_to_markdown


class ConversionError(Exception):
    pass


def _pdf_bytes_to_docx_bytes(pdf_file):
    """Step 1: PDF -> DOCX using pdf2docx (layout-aware conversion)."""
    try:
        from pdf2docx import Converter
    except ImportError as exc:
        raise ConversionError(
            "PDF-to-DOCX converter is not installed on the server."
        ) from exc

    pdf_file.seek(0)
    pdf_bytes = pdf_file.read()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name

    tmp_docx_path = tmp_pdf_path.replace(".pdf", ".docx")

    try:
        converter = Converter(tmp_pdf_path)
        converter.convert(tmp_docx_path)
        converter.close()

        if not os.path.exists(tmp_docx_path):
            raise ConversionError("PDF could not be converted to DOCX.")

        with open(tmp_docx_path, "rb") as f:
            docx_bytes = f.read()
    except Exception as exc:
        raise ConversionError(f"Failed to convert PDF to DOCX: {exc}") from exc
    finally:
        for path in (tmp_pdf_path, tmp_docx_path):
            try:
                os.remove(path)
            except OSError:
                pass

    if not docx_bytes:
        raise ConversionError("PDF-to-DOCX conversion produced an empty file.")

    return docx_bytes


def _docx_bytes_to_markdown(docx_bytes):
    """Step 2: DOCX -> HTML (mammoth) -> Markdown (markdownify)."""
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
    """
    Full pipeline for PDF uploads:
    PDF -> DOCX -> Markdown
    Kept as the public entrypoint name for backward compatibility with views.py.
    """
    docx_bytes = _pdf_bytes_to_docx_bytes(pdf_file)
    return _docx_bytes_to_markdown(docx_bytes)


def convert_docx_to_markdown(docx_file):
    """
    Pipeline for native DOCX uploads:
    DOCX -> Markdown (no PDF step needed)
    """
    docx_file.seek(0)
    docx_bytes = docx_file.read()
    if not docx_bytes:
        raise ConversionError("Uploaded DOCX file is empty.")
    return _docx_bytes_to_markdown(docx_bytes)
