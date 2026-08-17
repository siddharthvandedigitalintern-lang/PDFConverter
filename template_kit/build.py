# -*- coding: utf-8 -*-
"""
Run this file to build the final PDF:
    python3 build.py

Strategy (wkhtmltopdf unpatched-Qt compatible):
  1. generate.py emits cover.html + content.html
  2. wkhtmltopdf builds cover.pdf  (no margins, no footer)
  3. wkhtmltopdf builds content.pdf (standard margins)
  4. reportlab stamps a footer bar on every content page
  5. pypdf merges cover.pdf + footered content.pdf -> final PDF
"""

import os
import io
import subprocess
import tempfile

from config import CONFIG
import generate

# ── Brand colours (kept in sync with generate.py) ──────────────────────────
DARK  = "#00875F"
MINT  = "#00D9A0"
MUTED = "#5B6260"

def hex_to_rgb01(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


def wkhtmltopdf(html_path, pdf_path, margin_top="16mm", margin_bottom="16mm",
                margin_left="18mm", margin_right="18mm"):
    """Run wkhtmltopdf on a single HTML file."""
    cmd = [
        "wkhtmltopdf",
        "--enable-local-file-access",
        "--page-size", "A4",
        "--margin-top",    margin_top,
        "--margin-bottom", margin_bottom,
        "--margin-left",   margin_left,
        "--margin-right",  margin_right,
        "--quiet",
        html_path,
        pdf_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("wkhtmltopdf stderr:", result.stderr)
        raise RuntimeError(f"wkhtmltopdf failed with code {result.returncode}")


def stamp_footer(content_pdf_path: str, out_pdf_path: str,
                 subject: str, start_page: int = 2):
    """
    Stamp a footer on every page of content_pdf_path using reportlab overlay.
    Pages are numbered starting from start_page (to account for cover page).
    """
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(content_pdf_path)
    n_pages = len(reader.pages)

    # A4 points
    PAGE_W, PAGE_H = A4   # ~595 x 842 pts
    MARGIN_BOTTOM_PT = 18 * 2.8346   # 18mm in points
    FOOTER_Y = MARGIN_BOTTOM_PT - 14  # position footer inside bottom margin

    dark_rgb  = hex_to_rgb01(DARK)
    muted_rgb = hex_to_rgb01(MUTED)
    mint_rgb  = hex_to_rgb01(MINT)

    overlay_buf = io.BytesIO()
    c = rl_canvas.Canvas(overlay_buf, pagesize=A4)

    for i in range(n_pages):
        page_num = start_page + i
        footer_text = f"Notes Ninja  \u2022  {subject}  \u2022  Page {page_num}"

        # Thin separator line above footer text
        c.setStrokeColorRGB(*hex_to_rgb01(MINT))
        c.setLineWidth(0.5)
        c.line(40, FOOTER_Y + 10, PAGE_W - 40, FOOTER_Y + 10)

        # Footer text
        c.setFont("Helvetica", 7.5)
        c.setFillColorRGB(*muted_rgb)
        c.drawCentredString(PAGE_W / 2, FOOTER_Y, footer_text)

        c.showPage()

    c.save()
    overlay_buf.seek(0)
    overlay_reader = PdfReader(overlay_buf)

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[i])
        writer.add_page(page)

    with open(out_pdf_path, "wb") as f:
        writer.write(f)


def merge_pdfs(pdf_paths: list, out_path: str):
    """Merge a list of PDF files into one."""
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    for path in pdf_paths:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    with open(out_path, "wb") as f:
        writer.write(f)


def main():
    # Step 1 — generate HTML files
    generate.build_html()
    print("HTML generated -> cover.html + content.html")

    # Resolve output name
    out_name = CONFIG["output_filename"].strip()
    if not out_name.lower().endswith(".pdf"):
        out_name += ".pdf"

    subject = CONFIG["footer_subject"]

    with tempfile.TemporaryDirectory() as tmp:
        cover_pdf   = os.path.join(tmp, "cover.pdf")
        content_raw = os.path.join(tmp, "content_raw.pdf")
        content_ok  = os.path.join(tmp, "content_footered.pdf")

        # Step 2 — cover page: zero margins so the full-bleed bars reach edges
        print("Building cover page …")
        wkhtmltopdf(
            os.path.abspath("cover.html"), cover_pdf,
            margin_top="0", margin_bottom="0",
            margin_left="0", margin_right="0",
        )

        # Step 3 — content pages: standard margins, extra bottom for footer
        print("Building content pages …")
        wkhtmltopdf(
            os.path.abspath("content.html"), content_raw,
            margin_top="16mm", margin_bottom="18mm",
            margin_left="18mm", margin_right="18mm",
        )

        # Step 4 — stamp footer on content pages (page numbering starts at 2)
        print("Stamping footers …")
        stamp_footer(content_raw, content_ok, subject, start_page=2)

        # Step 5 — merge cover + content
        print("Merging …")
        merge_pdfs([cover_pdf, content_ok], out_name)

    print(f"Done → {out_name}")


if __name__ == "__main__":
    main()
