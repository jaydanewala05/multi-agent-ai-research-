import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text().strip()

            if page_text:
                text += f"\n\n[PAGE {page_num}]\n{page_text}"

    return text.strip()
