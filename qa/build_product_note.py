"""Renders docs/01_PRODUCT_NOTE.md to docs/01_PRODUCT_NOTE.pdf (A4) and prints the page count.

Needs: pip install markdown pypdf playwright, plus Microsoft Edge or Google Chrome.
    python qa/build_product_note.py
"""

# ruff: noqa: E501  (the CSS below is long lines on purpose)
import re
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

DOCS = Path(__file__).resolve().parents[1] / "docs"
SOURCE = DOCS / "01_PRODUCT_NOTE.md"
PDF = DOCS / "01_PRODUCT_NOTE.pdf"

CSS = """
@page { size: A4; margin: 13mm 14mm; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 10.2pt; line-height: 1.38; color: #1F2937; }
h1 { font-size: 19pt; margin: 0 0 1mm 0; color: #312E81; }
h2 { break-after: avoid; page-break-after: avoid; font-size: 12pt; margin: 4.2mm 0 1.4mm 0; color: #4F46E5; border-bottom: 1px solid #C7D2FE; padding-bottom: 0.6mm; }
p { margin: 1.2mm 0; }
table { border-collapse: collapse; width: 100%; margin: 1.6mm 0; font-size: 9.2pt; page-break-inside: avoid; }
th { background: #EEF2FF; text-align: left; }
th, td { border: 1px solid #D1D5DB; padding: 0.9mm 1.6mm; vertical-align: top; }
img { max-width: 100%; }
p:has(> img) { break-before: avoid; }
p > img { display: block; margin: 1.5mm auto; width: 88%; }
.shots { display: flex; gap: 2mm; margin: 1.5mm 0; }
.shots img { width: 32.6%; height: auto; border: 1px solid #D1D5DB; border-radius: 2mm; }
strong { color: #111827; }
"""


def build() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables"])
    html = (
        f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    )
    html = re.sub(r'src="assets/', f'src="{(DOCS / "assets").as_uri()}/', html)
    page_file = DOCS / "_note_render.html"
    page_file.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="msedge", headless=True)
            except Exception:
                browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page()
            page.goto(page_file.as_uri())
            page.wait_for_timeout(800)
            page.pdf(path=str(PDF), format="A4", print_background=True, prefer_css_page_size=True)
            browser.close()
    finally:
        page_file.unlink(missing_ok=True)
    pages = len(PdfReader(str(PDF)).pages)
    print(f"{PDF.name}: {pages} pages")
    return pages


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
