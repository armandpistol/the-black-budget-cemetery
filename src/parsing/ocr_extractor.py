"""
ocr_extractor.py
Converts scanned PDF pages to images and extracts text via Tesseract OCR.
"""

import os

import pytesseract
from pdf2image import convert_from_path


def extract_text_from_pdf(pdf_path: str, dpi: int = 300) -> dict:
    """
    Extract text from a scanned PDF using OCR.

    Args:
        pdf_path: Absolute or relative path to the PDF file.
        dpi: Resolution for page-to-image conversion. Higher = better OCR
             accuracy but slower. 300 is the standard for document scanning.

    Returns:
        A dict with:
          - 'source_file': source_filename of the PDF
          - 'page_count': number of pages processed
          - 'pages': list of dicts, one per page, each with 'page_num' and 'text'
          - 'full_text': all pages concatenated into one string
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.basename(pdf_path)
    print(f"Converting '{filename}' to images at {dpi} DPI...")

    # Convert each PDF page to a PIL Image object
    pages = convert_from_path(pdf_path, dpi=dpi)
    print(f"  {len(pages)} page(s) found. Running OCR...")

    page_results = []
    for i, page_image in enumerate(pages, start=1):
        print(f"  Processing page {i}/{len(pages)}...")
        text = pytesseract.image_to_string(page_image, lang="eng")
        page_results.append({
            "page_num": i,
            "text": text.strip()
        })

    full_text = "\n\n--- PAGE BREAK ---\n\n".join(
        p["text"] for p in page_results
    )

    return {
        "source_file": filename,
        "page_count": len(pages),
        "pages": page_results,
        "full_text": full_text
    }


if __name__ == "__main__":
    # Quick test — run this file directly to verify OCR works

    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "../../data/raw/blue_book_incident_17_kenneth_arnold.pdf"
    )

    result = extract_text_from_pdf(pdf_path)

    print(f"\n✓ Extracted {result['page_count']} pages from '{result['source_file']}'")
    print(f"\n--- FIRST PAGE PREVIEW ---\n")
    print(result["pages"][0]["text"][:1000])

    import json
    import pathlib

    output_dir = pathlib.Path(__file__).parents[2] / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "blue_book_incident_17_kenneth_arnold.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved to {output_path}")