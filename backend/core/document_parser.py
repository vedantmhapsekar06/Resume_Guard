import os
import pdfplumber
import fitz  # PyMuPDF, used as a fallback for tricky PDFs
from docx import Document


def extract_text(file_path: str) -> str:
    """
    Extract raw text from a PDF or DOCX file.
    Raises ValueError for unsupported types and for files with no extractable text
    (e.g. scanned/image-only PDFs - OCR is not supported), so the LLM is never asked
    to 'analyze' an empty document.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        text = _extract_pdf_text(file_path)
    elif ext == ".docx":
        text = _extract_docx_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if len(text.strip()) < 30:
        raise ValueError(
            "No readable text found in this file (it may be a scanned/image-only document). "
            "Please upload a text-based PDF or DOCX."
        )
    return text


def _extract_pdf_text(file_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        text = ""

    # Fallback to PyMuPDF if pdfplumber got nothing (e.g. unusual PDF structure)
    if not text.strip():
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()

    return text.strip()


def _extract_docx_text(file_path: str) -> str:
    doc = Document(file_path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]

    # Many resume templates put content (skills, experience) inside tables;
    # doc.paragraphs does not include those.
    for table in doc.tables:
        for row in table.rows:
            seen = set()
            for cell in row.cells:
                if id(cell._tc) in seen:   # merged cells repeat
                    continue
                seen.add(id(cell._tc))
                for p in cell.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)

    return "\n".join(parts).strip()
