import os


# Prefer pymupdf4llm for rich extraction; fall back to PyMuPDF (fitz) if unavailable
try:
    import pymupdf4llm as pymupdf4llm
except Exception:
    pymupdf4llm = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

def extract_text_images_from_pdf(pdf_path):
    
    # Check if PDF file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # If pymupdf4llm is available, use it (gives chunked pages with images)
    if pymupdf4llm is not None:
        chunks_words = pymupdf4llm.to_markdown(
            doc=pdf_path,
            page_chunks=True,
            write_images=True,
            image_path="images",
            extract_words=True,
        )

        if chunks_words is None:
            raise ValueError(f"pymupdf4llm.to_markdown returned None for {pdf_path}")
        if not chunks_words:
            raise ValueError(f"No text chunks extracted from {pdf_path}")

        full_text = ""
        for page in chunks_words:
            full_text += page.get("text", "") + "\n"
        return full_text

    # Fallback: use PyMuPDF (fitz) to extract plain text per page
    if fitz is not None:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            try:
                text = page.get_text("text")
            except Exception:
                text = page.get_text()
            full_text += text + "\n"
        return full_text

    # Neither extractor is available
    raise RuntimeError(
        "No PDF extractor available: install 'pymupdf4llm' or 'PyMuPDF'.\n"
        "Install with: pip install pymupdf4llm  OR  pip install PyMuPDF"
    )




